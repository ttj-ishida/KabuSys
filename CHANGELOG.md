CHANGELOG
=========

すべての注目すべき変更履歴をここに記載します。フォーマットは "Keep a Changelog" に準拠しています。

[0.1.0] - 2026-04-12
-------------------

Added
- パッケージ初期リリース。基本的な自動売買・検証・監視機能を提供します。
- コマンド／エントリスクリプト
  - run_execution.py: ExecutionEngine を起動するエントリ。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite DB（data/paper_trading.db など）と MockBrokerClient を利用して本番 DB と分離して実行。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は実行環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。
  - tools.paper_verification_report: Paper Trading の検証レポートを生成する CLI（python -m kabusys.tools.paper_verification_report）。期間指定(--from/--to) と DB パス(--db) に対応。
- 設定管理（kabusys.config）
  - .env 自動読込機能: プロジェクトルート（.git または pyproject.toml で判定）を探索して .env / .env.local を自動読み込み（OS 環境変数が優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 高度な .env パーサ: export 付き行、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いをサポート。
  - Settings クラスで多数の設定をプロパティ化: DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）、PID/KILL フラグ、しきい値（CPU/MEM/DISK）、PAPER_FILL_MODE の検証など。
- 実行ツール／監視
  - monitoring_db 初期化呼び出し（冪等）を run_execution/run_monitoring で実施して監視用テーブルの存在を保証。
  - プロセス優先度設定ユーティリティ（kabusys.utils.process_priority）を導入。Windows と POSIX 系（Linux/Mac/FreeBSD）で差を吸収し、set_process_priority/set_cpu_affinity を提供。権限不足・未対応環境では警告を出してスキップする安全設計。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: シグナル選別（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights、全スコアが 0 の場合は等分にフォールバック）。
  - risk_adjustment: セクター上限適用（apply_sector_cap。unknown セクターは上限適用除外）、市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームは 1.0 でフォールバック）。
  - position_sizing: 株数計算（calc_position_sizes）。risk_based / equal / score の配分方式に対応し、lot_size（単元）丸め、1 銘柄上限・aggregate cap（available_cash によるスケールダウン）、cost_buffer を使った保守的コスト見積もり、残差処理による lot 単位の追加配分などを実装。
- リサーチ（kabusys.research）
  - factor_research: DuckDB を使ったファクター計算（calc_momentum, calc_volatility, calc_value）。価格・財務データ（prices_daily, raw_financials）を参照して各種指標を算出（MA200 乖離、ATR20、平均売買代金、PER/ROE など）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Spearman rank correlation）計算（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリ（factor_summary）。外部ライブラリに依存せず標準ライブラリのみで実装。
- AI ニューススコアリング（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコア生成機能を追加。raw_news と news_symbols を集約してバッチ（最大 20 銘柄/コール）で API に送信し、結果を ai_scores テーブルへ書き込む。スコアは ±1.0 にクリップ。
  - レートリミット・ネットワーク断・5xx 等に対して指数バックオフでリトライし、失敗時はフェイルセーフでスキップする設計。
  - タイムウィンドウ計算（JST に基づく前日 15:00 〜 当日 08:30）を明示的に実装。ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計。
- パッケージ初期メタデータ
  - __version__ = "0.1.0" を追加。

Changed
- （初期リリースにつき変更履歴はなし。実装上の設計・インターフェースは上記 Added を参照。）

Fixed
- .env 読み込みが失敗した場合に警告を出す（読み込み継続）。ファイル I/O エラーを抑制して堅牢化。
- run_monitoring のポーリング間隔環境変数 MONITOR_POLL_INTERVAL の不正値処理を追加。0 以下や非整数が渡った場合はデフォルト（60 秒）にフォールバックして警告を出力。
- tools.paper_verification_report: DB が存在しない場合のエラーメッセージを改善。SQLite の OperationalError（テーブル未存在 等）を個別にキャッチして安全にレポート生成を継続。

Security
- OpenAI API キーや各種外部トークンは環境変数経由で供給する設計。news_nlp.score_news は API キーが未設定の際 ValueError を送出して早期に失敗する。
- .env 自動ロードでは OS 環境変数を保護（.env.local の override でも OS 環境変数は上書きされないよう設計）。

Notes / Usage
- 環境変数の自動ロード機能はプロジェクトルートが .git または pyproject.toml で検出できなければスキップされます（配布後に CWD に依存しない動作を意図）。
- 主要な環境変数:
  - KABUSYS_ENV: development | paper_trading | live（無効値は ValueError）
  - SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH
  - PAPER_FILL_MODE: instant | partial | never | reject（無効値は ValueError）
  - OPENAI_API_KEY: news_nlp 用
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（整数、1 以上）
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、run_execution は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
  - paper_verification_report は paper_trading DB に対して稼働率 / 注文成功率 / レイテンシ等のレポートを生成します。
- 開発者向け:
  - process_priority.set_process_priority は権限や OS により失敗する可能性があるため、失敗時は警告を出して処理を継続します。
  - DuckDB 接続を受け取るリサーチ関数群は副作用を持たず、prices_daily / raw_financials テーブルのみ参照します（本番 API にはアクセスしない）。

Deprecated
- なし

Removed
- なし

Security
- なし（既知の脆弱性はありませんが、外部 API（OpenAI, ブローカ）を用いる箇所は適切に API キーや証憑を管理してください）

今後の予定（例）
- 監視アラート通知（LINE 連携等）
- 銘柄毎 lot_size マスタ対応（単元が銘柄毎に異なる環境への対応）
- ai_news_nlp の結果キャッシュ・再試行強化、部分失敗時のトランザクション改善

--- End of CHANGELOG ---