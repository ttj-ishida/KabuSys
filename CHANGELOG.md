# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このファイルはコードベースの内容から推測して作成した初期の変更履歴です。

フォーマット:
- 変更はセクション（Added, Changed, Fixed, Security, Breaking Changes 等）に分類しています。
- 日付はリリース日（推定）です。

## [Unreleased]
- 次回リリースに向けての作業項目や既知の改善点（特に明示がないため現状は空）。

## [0.1.0] - 2026-04-04
初期リリース（推定）。日本株自動売買システムの基盤的コンポーネントを実装。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン 0.1.0, __all__ に data, strategy, execution, monitoring を公開）。
- 環境設定
  - 環境変数/設定管理モジュール（kabusys.config）を実装。
    - プロジェクトルート自動検出ロジック（.git または pyproject.toml を探索）。
    - .env/.env.local の自動読み込み（OS 環境変数を保護する protected 機構）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化をサポート。
    - export KEY=val 形式やクォート／エスケープ、インラインコメント処理に対応した .env パーサ。
    - 必須環境変数取得のユーティリティ（_require）。
    - 設定クラス Settings を提供し、J-Quants、kabuステーション、LINE API、DBパス、監視閾値、実行モード（development/paper_trading/live）等のプロパティを公開。
    - 不正な KABUSYS_ENV / LOG_LEVEL 値の検証とエラーメッセージ。
- AI ニュース解析
  - kabusys.ai.news_nlp: ニュースを OpenAI（gpt-4o-mini）でバッチ評価して ai_scores テーブルへ登録する機能を実装。
    - タイムウィンドウ計算（JST基準 -> UTC変換）。
    - ニュースを銘柄毎に集約し、1銘柄当たり最大記事数・最大文字数でトリム。
    - 最大バッチ 20 銘柄での API 呼び出し。JSON Mode を期待したレスポンスをパース。
    - リトライ（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフ、失敗はフェイルセーフでスキップ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results フィールド、既知コードのみ採用、数値チェック、スコアのクリップ）。
    - DuckDB への冪等的書き込み（DELETE -> INSERT）、部分失敗でも既存スコアを保護する設計。
  - kabusys.ai.regime_detector: ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存する機能を実装。
    - ma200 乖離の計算（ルックアヘッド防止のため target_date 未満のデータのみ利用）。
    - マクロニュース抽出（キーワードフィルタ、最大記事数制限）。
    - OpenAI 呼び出しを用いたマクロセンチメント評価（再試行/バックオフ、失敗時は macro_sentiment=0.0 にフォールバック）。
    - スコア合成ルール（重み付け: MA 70% / マクロ 30%、スケーリングとクリップ）と閾値判定。
    - DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時に ROLLBACK）。
    - API キー注入をサポート（引数または OPENAI_API_KEY 環境変数）。
- Data / ETL
  - kabusys.data.pipeline: ETLResult データクラスと ETL 実行結果管理を実装。
    - ETLResult に品質問題（quality.QualityIssue）やエラーリストを保持、辞書変換ユーティリティを提供。
  - kabusys.data.etl: pipeline.ETLResult を再エクスポート。
  - kabusys.data.calendar_management: JPX カレンダー管理と営業日判定ロジックを実装。
    - market_calendar を基に is_trading_day/is_sq_day/next_trading_day/prev_trading_day/get_trading_days を提供。
    - DB に登録がない場合は曜日ベース（週末を休日）でのフォールバック。
    - calendar_update_job による J-Quants からの差分取得および冪等保存の実装（バックフィル・健全性チェック対応）。
    - DuckDB 互換性を考慮した日付変換ユーティリティなど。
- Research（リサーチ用ユーティリティ）
  - kabusys.research モジュール群を実装（ファクター計算・特徴量探索）。
  - calc_momentum / calc_volatility / calc_value:
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER/ROE）を DuckDB の prices_daily/raw_financials から計算。
    - 欠損・データ不足時の None 戻り、結果は (date, code) キーの dict リストで返却。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）計算、ホライズン検証（1..252）、単一クエリで効率的取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算、十分なレコードがない場合は None。
    - rank: 同順位は平均ランクとなるランク変換ユーティリティ（丸めによる ties 対応）。
    - factor_summary: 各ファクター列の統計サマリー（count/mean/std/min/max/median）。
- ロギングと診断
  - モジュール全体で適切な logger 呼び出しを配置し、異常時に警告/情報ログを出力する実装。

### Changed
- （初版のため履歴なし）

### Fixed
- （初版のため履歴なし）

### Security
- OpenAI API キーは引数から注入可能で、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は明示的に ValueError を返す設計で、API キー未設定による不透明な動作を避けるようになっている。

### Breaking Changes
- （初版のため該当なし）

### Notes / 設計上の重要ポイント（ドキュメント的補足）
- ルックアヘッドバイアス対策:
  - AI モジュールおよびリサーチ関数は datetime.today() / date.today() を内部で参照せず、常に caller が与える target_date に基づいてデータを取得・計算する設計です。
- データベース操作:
  - DuckDB を前提としており、executemany の空リストに対する扱いなど DuckDB のバージョン差分を考慮した実装が含まれています。
  - DB への書き込みは可能な限り冪等に実施（DELETE → INSERT、ON CONFLICT 等の利用を想定）。
- フェイルセーフ:
  - LLM/API の失敗はスコア 0.0 やスキップでフォールバックし、ETL の途中失敗が全体を停止させないように設計されています（呼び出し元での監視・対処を想定）。
- 環境変数ロード:
  - .env 自動読み込みはプロジェクトルートの検出に依存し、配布後の実行でも CWD に依存せず動作するように設計されています。
  - OS 環境変数は保護され、.env.local による上書きが可能（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。

---

上記はコードファイルの実装内容から推測した CHANGELOG です。追加のモジュール（strategy、execution、monitoring、jquants_client、quality モジュール等）は参照されていますが今回のコードベースに含まれていないため、外部連携や将来の変更は次回以降に反映してください。必要であれば日付や文言を実際のリリース日に合わせて更新します。