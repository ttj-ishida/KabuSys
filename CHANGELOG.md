# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

## [0.1.0] - 2026-03-29

初回リリース。日本株のデータ基盤・研究・AI支援・運用補助機能を含む自動売買サブシステムのコア実装を追加しました。主な追加内容は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期化（バージョン __version__ = 0.1.0）。公開サブパッケージ: data, strategy, execution, monitoring。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定値を自動読み込みする機能を実装。
  - 自動ロード制御: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - プロジェクトルートの検出ロジック: .git または pyproject.toml を起点に探索（CWD に依存しない実装）。
  - .env 解析機能: `export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理（クォート有無での扱いの違い）を実装。
  - OS 環境変数を保護する protected 上書き制御（.env と .env.local の読み込み順を考慮）。
  - Settings クラス: J-Quants / kabu ステーション / Slack / DB パス等のプロパティを提供。既定値やバリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。
  - デフォルト値例: KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）を厳密に定義する calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/チャンク）、記事数・文字数上限（記事数=10、文字数=3000）によるトークン制御。
    - リトライ戦略（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）とフェイルセーフ（失敗時はスキップして継続）。
    - レスポンス検証（JSON 抽出、results リスト・各要素の code/score 検証、数値の有限性チェック）とスコアクリッピング（±1.0）。
    - スコアの ai_scores テーブルへの冪等書き込み（DELETE → INSERT）実装。部分失敗時に既存スコアを保護。
    - テスト容易性: OpenAI 呼び出し（_call_openai_api）をモック差し替え可能に設計。
    - パブリック API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出のキーワード集合（日本・米国・グローバルの主要用語）を実装。
    - OpenAI 呼び出し（gpt-4o-mini, JSON Mode）、リトライ、API エラーの扱い（不安定時は macro_sentiment=0.0 で継続）を実装。
    - レジームスコア計算、閾値によるラベリング（閾値 0.2）、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト容易性: news_nlp とモジュール結合しない形で OpenAI 呼び出しを独立実装。
    - パブリック API: score_regime(conn, target_date, api_key=None) → 1 を返す（成功時）。

- データ基盤 (src/kabusys/data)
  - カレンダー管理 (calendar_management.py)
    - JPX カレンダーの管理機能（market_calendar テーブル使用）を実装。
    - 営業日判定と探索ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータが無い場合は曜日（平日）でフォールバックする堅牢性。
    - 夜間バッチ更新 job: calendar_update_job(conn, lookahead_days=90) で J-Quants から差分取得し保存。バックフィル、健全性チェック（未来日付の異常検出）を実装。
  - ETL パイプライン (pipeline.py / etl.py)
    - ETLResult データクラスを追加（取得件数、保存件数、品質問題、エラー等を集約）。
    - 差分更新や最大日付取得のユーティリティ（_get_max_date 等）を実装。
    - ETLResult.to_dict() による品質問題の辞書化など監査用変換を提供。
    - etl モジュールで ETLResult を再エクスポート。
  - jquants_client との連携（fetch/save 呼び出しを想定する設計）。

- リサーチ／ファクター計算 (src/kabusys/research)
  - factor_research.py
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）。
    - Volatility/Liquidity: 20日 ATR・相対ATR、20日平均売買代金、出来高比率。
    - Value: PER, ROE（raw_financials から直近の財務データを取得して計算）。PBR/配当利回りは未実装として明記。
    - DuckDB 上の SQL ウィンドウ関数を利用した実装（lookahead 回避のため target_date 未満／以前のデータのみ参照）。
    - すべての関数は prices_daily / raw_financials のみ参照し、本番発注 API にはアクセスしない設計。
  - feature_exploration.py
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=[1,5,21])（任意ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（Spearman ランク相関、有効レコード数 3 未満で None）。
    - ランク変換: rank(values)（同順位は平均ランク、浮動小数丸めで ties を安定化）。
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median を計算）。
  - research パッケージの __all__ で主要関数を公開。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意事項 / 既知の設計上の振る舞い
- .env パーサーは細かなケース（クォート内エスケープ、インラインコメントの扱い等）に対応していますが、極端な非標準フォーマットでは想定外の挙動となる可能性があります。
- OpenAI API の JSON Mode を利用していますが、稀に前後に余計なテキストが混ざる場合を考慮して JSON 抽出ロジックを入れています。それでも全ての生成物を完全に保証するものではありません。
- API 呼び出し失敗時はフェイルセーフで「中立」や「スキップ」を選ぶ設計です（例: macro_sentiment=0.0、スコア未取得コードは書き込み対象外）。上位でのアラート運用を想定しています。
- raw_financials に PBR/配当利回り等は現時点で未実装である旨を明記。
- DuckDB の executemany に関する互換性考慮（空リスト禁止）に対応済み。
- テスト容易性のため、OpenAI 呼び出し箇所（両モジュールとも _call_openai_api）を unittest.mock で差し替え可能に実装しています。

### 将来的に検討すべき事項（提案）
- PBR・配当利回りといった追加バリューファクターの実装。
- AI モデル切替やプロンプト最適化のための設定外部化。
- ETL のジョブスケジューリングや監視機構（現状は関数提供のみ）。
- 詳細なログ集約・メトリクス収集（Prometheus/Datadog 等）との連携。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時には、コミット履歴や PR の説明を参照して差分を精査してください。