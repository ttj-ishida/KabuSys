# Changelog

すべての重要な変更点をここに記録します。本ファイルは Keep a Changelog の書式に準拠しています。

なお、本リリース情報はコードベース（src/ 以下）からの実装内容を基に推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
Initial release — 日本株自動売買 / データ基盤・研究・AI スコアリングの初期実装。

### Added
- パッケージ基盤
  - kabusys パッケージ初期版（__version__ = 0.1.0）。
  - パッケージ公開 API に data, strategy, execution, monitoring を含める設計（__all__）。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - .env 行パーサ（export プレフィックス、クォートやエスケープ、インラインコメントの扱い対応）。
  - 環境変数保護（既存 OS 環境変数を保護する protected ロジック）。
  - Settings クラス：JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / KABU_API_BASE_URL / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID / DUCKDB_PATH / SQLITE_PATH / KABUSYS_ENV / LOG_LEVEL 等のプロパティを提供。環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）やユーティリティプロパティ（is_live / is_paper / is_dev）を実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）の JSON mode でセンチメントを取得する score_news 実装。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を calc_news_window で提供。
  - バッチ処理（1 API コールで最大 20 銘柄）、1 銘柄あたりの記事数/文字数上限、チャンクごとの再試行（指数バックオフ、429/ネットワーク/5xx をリトライ対象）を実装。
  - レスポンスの堅牢なバリデーション（JSON 抽出、"results" 構造チェック、コードの正規化、スコア数値検証、±1 でクリップ）。
  - 書き込みは部分失敗に備え、取得できたコードのみ DELETE → INSERT の置換を行う（冪等性・既存データ保護）。
  - 単体テスト用に _call_openai_api をパッチ差し替え可能な設計。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定する score_regime 実装。
  - マクロキーワードによる raw_news 抽出、OpenAI 呼び出し（gpt-4o-mini）での macro_sentiment 評価、スコア合成・閾値判定（bull / neutral / bear）を実装。
  - API エラー時は macro_sentiment を 0.0 とするフェイルセーフ。DB への書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理。
  - lookahead バイアス対策（date 引数ベースで外部時間参照を行わない設計）。

- 研究用ファクター計算（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。
    - momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA の乖離、データ不足時は None）。
    - volatility: 20 日 ATR（avg true range）、atr_pct、avg_turnover、volume_ratio（データ不足時は None）。
    - value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0 / 欠損時は None）。
  - feature_exploration: calc_forward_returns（任意ホライズンの将来リターン）、calc_ic（スピアマン順位相関による IC）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
  - research パッケージの __all__ で主要関数を公開。zscore_normalize は data.stats から再利用。

- データ基盤（kabusys.data）
  - calendar_management: JPX マーケットカレンダー管理（market_calendar テーブルに基づく is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供）。
    - DB データがない/未登録日は曜日ベースのフォールバックを使用。
    - calendar_update_job により J-Quants API からの差分取得と保存（バックフィル、健全性チェックを含む）。
  - pipeline / ETL: ETLResult データクラス、ETL ヘルパー関数を含む pipeline モジュール。差分取得・保存・品質チェック（quality モジュール利用）を想定した設計。
  - data.etl から ETLResult を再エクスポート。

- 実装上の設計方針（ドキュメント化）
  - ルックアヘッドバイアス回避のため、datetime.today() / date.today() をスコア処理の内部で参照しない設計（外部から target_date を注入）。
  - OpenAI 呼び出しの失敗はスコアリング処理全体の致命エラーとせず、適切にフォールバック or スキップして継続（フェイルセーフ）。
  - DuckDB の互換性考慮（executemany に空リストを渡さない、日付の型変換ユーティリティ等）。
  - 単体テストしやすい設計（_call_openai_api を patch 可能など）。

### Fixed
- 初期実装として各種エラーハンドリングを追加：
  - OpenAI API 呼び出し時の各種例外（RateLimitError, APIConnectionError, APITimeoutError, APIError）に対して再試行ロジックとフェイルセーフフォールバックを実装。
  - JSON 解析失敗時に前後余計なテキストが混入した場合でも {} を抽出して解析を試みる復元処理を追加（news_nlp）。
  - DuckDB の挙動（executemany に空リスト不可）を考慮した分岐を追加して DB 書き込み時の例外を回避。

### Security
- 機密情報は環境変数経由で取得（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK_BOT_TOKEN, KABU_API_PASSWORD 等）。
- .env の自動ロード時に既存 OS 環境変数を保護する protected ロジックを実装（.env.local は override=True だが protected を尊重）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを明示的に無効化可能（テストや CI 向け）。

### Notes / Implementation details
- OpenAI モデルは gpt-4o-mini を想定（JSON mode を利用した厳格な出力フォーマット）。
- ニュース集約・スコアリングは「銘柄ごとに全記事を統合して 1 スコアを返す」方式を採用。トークン・文字数対策として1銘柄ごとに文字数上限を設定。
- 市場レジーム判定では ETF 1321 の MA200 乖離を主要信号とし、マクロセンチメントを補助（重み 0.7 / 0.3）。閾値により bull / neutral / bear を判定。
- 多くの処理で DuckDB をデータストアとして想定しており、SQL と Python の混合で高効率に集計・ウィンドウ関数を使用している。

---

初版（0.1.0）は上記機能群を含む初期実装です。今後のリリースではテストカバレッジの拡充、さらなる堅牢化（タイムアウト/再試行ポリシーの改善）、外部 API クライアント抽象化、ドキュメントの充実化を予定しています。