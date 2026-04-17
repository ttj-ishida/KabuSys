Keep a Changelog 準拠 — 変更履歴 (日本語)

すべての変更は可能な限りコードベースから推測して記載しています。初回リリース相当のまとめとして記載しています。

## [0.1.0] - 2026-04-17

### 追加
- 基本パッケージとバージョン情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。

- 実行 / 監視用エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper SQLite DB を使用（data/paper_trading.db をデフォルト）して本番 DB と完全分離。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository、OrderManager、RiskManager、Reconciler を組み立て ExecutionEngine をバックグラウンドスレッドで実行。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御: project/data/stop_requested.flag を監視し停止。execution.pid を PID ファイルとして扱う。
    - RiskManager に対するデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、等）を指定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を変更可能（デフォルト 60 秒）。不正値はログ警告のうえデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - プロセス優先度を "high" に設定し、stop フラグの検知で優雅に終了。

- 設定管理（環境変数読み込み）
  - config.py: 強化された .env 自動読み込み機能を追加。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env 解析器は quoted 値（シングル/ダブルクォート）、エスケープ（バックスラッシュ）、`export KEY=val` 形式、インラインコメントの取り扱い等に対応。
    - OS 環境変数を保護するための protected 上書き制御（.env.local は override=True だが既存 OS 環境変数は上書きしない）。
  - Settings クラスを追加し、アプリケーションで利用する設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE 等）。
    - `PAPER_FILL_MODE` に対する入力検証（許容値: "instant" | "partial" | "never" | "reject"）。
    - `KABUSYS_ENV` の検証（許容値: "development", "paper_trading", "live"）。
    - 各種閾値設定プロパティを追加（CPU/MEMORY/DISK の閾値や PID / kill flag のパス等）。
    - settings インスタンスをデフォルトでエクスポート。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - 信号の候補選定 select_candidates（score 降順、score 同値時は signal_rank 昇順のタイブレーク）。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超える場合に当該セクターの新規候補を除外するロジックを実装。
    - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数を実装（未知のレジームは警告して 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 等価・スコア・リスクベースの割当方式に対応した株数決定ロジックを実装。
    - 単元株（lot_size）丸め、銘柄別上限（max_position_pct）、総投下上限（available_cash による aggregate cap）を考慮したスケーリングロジック、端数調整アルゴリズムを実装。
    - risk_based 方式では risk_pct・stop_loss_pct を用いた理想株数算出を実装。
    - いくつかの場面でログ出力や入力検証あり（価格欠損時のスキップ等）。

- 研究（Research）モジュール
  - research.factor_research
    - モメンタム（1M/3M/6M リターン、MA200 乖離率）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均出来高等）、バリュー（PER/ROE）を DuckDB の prices_daily / raw_financials テーブルから計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - SQL ウィンドウ関数を用いた実装でデータ不足時の None ハンドリングあり。
  - research.feature_exploration
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、入力検証あり）。
    - IC（Spearman の ρ）計算 calc_ic（ランク変換を内部に実装）。
    - 統計サマリー factor_summary （count/mean/std/min/max/median）。
    - rank 関数（同順位は平均ランク）。

- ユーティリティ
  - utils.process_priority
    - プロセス優先度設定 set_process_priority（Windows / POSIX の差分を吸収）。
    - CPU アフィニティ設定 set_cpu_affinity（指定コア数でプロセスを固定するユーティリティ）。
    - 権限不足や未対応 OS の場合は警告ログを出して安全にスキップする実装。
  - utils.__init__ を追加。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI を追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数等を集計して PASS/FAIL 判定を出力。
    - デフォルト DB: data/paper_trading.db。コマンドライン引数 --from / --to / --db をサポート。
    - 判定基準（閾値）: 稼働率 99.0%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms（ソース内定義）。

- モジュール統合
  - research パッケージの __init__ に zscore_normalize（kabusys.data.stats から）や factor 関数をエクスポートする設定を追加。
  - portfolio パッケージの __init__ で主要関数をまとめてエクスポート。

- AI / ニュース NLP（部分実装）
  - ai.news_nlp モジュールを追加（OpenAI API を用いたニュースセンチメントスコアリングの設計と複数ユーティリティ関数を実装）。
    - gpt-4o-mini を想定、JSON Mode 出力のバリデーション、チャンク処理、リトライ（429/ネットワーク/5xx に対する指数バックオフ）方針などを明記。
    - calc_news_window 関数（JST ベースの収集ウィンドウを UTC に変換）を実装。
    - score_news の骨格（API キー解決、ウィンドウ計算、記事集約フェーズなど）を実装。ただしソースは途中で途切れている（後述の既知の問題参照）。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 既知の問題 / 注意点
- ai.news_nlp モジュールの実装が途中で途切れている（ソースが途中で終わっている断片あり）。score_news の記事集約フェーズ以降の処理が未完のため、本番利用前に実装完了と動作確認が必要。
- portfolio.position_sizing と risk_adjustment 内に今後の改善や TODO コメントが存在:
  - price が欠損（0.0）の場合のフォールバック価格処理は未実装（apply_sector_cap 内の TODO）。
  - 単元株（lot_size）を銘柄別に扱う拡張（lot_map）については将来的に対応予定。
- utils.process_priority / set_cpu_affinity は権限不足や未対応 OS で失敗する可能性があるためその場合は警告ログを出して処理をスキップする設計。
- run_monitoring は「監視は本番 sqlite_path を使用する」という仕様が運用上の注意点（開発環境で監視を分離したい場合は設定に注意）。

### 環境変数（主要）
- KABUSYS_ENV: 環境種別（development | paper_trading | live） — Settings でバリデーションあり
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env の自動読み込みを無効化
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper trading の MockBroker 動作モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite DB（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- OPENAI_API_KEY: ai.news_nlp で使用（score_news 実行時に必須）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT 等（Settings にプロパティあり）

### セキュリティ
- 環境変数未設定時に必須値を要求する _require() を導入（例: JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD）。運用時は .env の配置とアクセス制御に注意してください。

---

上記はコードから推測して作成した変更履歴です。差分や追加情報があれば、バージョンや各項目を更新して反映します。