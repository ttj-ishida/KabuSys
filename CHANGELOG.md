# Changelog

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠しています。  
リリースは安定化した機能群を反映しており、以降の変更はここに追記してください。

全般:
- バージョンはパッケージの __version__ に合わせて 0.1.0 として公開。

## [0.1.0] - 初期リリース（初版）
公開日: 未設定

### 追加 (Added)
- アプリケーション基本構成
  - パッケージ初期化・バージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - Settings クラス（src/kabusys/config.py）を実装。.env 自動ロード、.env/.env.local の優先度や保護（既存 OS 環境変数を上書きしない）に対応。
  - .env パーサーを実装（コメント・クォート・export 形式対応、無効行スキップ）。
  - 環境変数による挙動制御：
    - KABUSYS_DISABLE_AUTO_ENV_LOAD：自動 .env ロード無効化
    - KABUSYS_ENV（development / paper_trading / live）
    - PAPER_TRADING_SQLITE_PATH（Paper Trading 専用 DB）
    - OPENAI_API_KEY（AI スコアリング用）
    - MONITOR_POLL_INTERVAL（監視ポーリング間隔）
    - その他多数（PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値など。Settings ドキュメント参照）

- 実行エントリ / デーモン類
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント作成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、ExecutionEngine を起動するフローを実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を参照して初期化（init_monitoring_db 実行）。
    - Process priority を最初に設定。監視ループでは SystemMonitor.check_once() を定期実行し例外保護を実施。

- モニタリング / ユーティリティ
  - process_priority ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows と POSIX（Linux / macOS / FreeBSD）を吸収して優先度（high/normal/low）を設定。
    - CPU affinity 設定機能（set_cpu_affinity）を実装。
    - 権限不足や未対応プラットフォーム時は WARN ログでスキップ。

- ポートフォリオ構築（純粋関数群、DB非依存）
  - portfolio_builder（select_candidates, calc_equal_weights, calc_score_weights）
    - BUY シグナルのスコア降順ソート、同点時の tiebreaker。
    - スコアが全て 0 の場合に等配分へフォールバック（警告ログ）。
  - risk_adjustment（apply_sector_cap, calc_regime_multiplier）
    - セクター集中上限チェック（sell_codes を除外可能、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数（bull/neutral/bear に対応、未知レジームはフォールバック）。
  - position_sizing（calc_position_sizes）
    - allocation_method: "risk_based", "equal", "score" をサポート。
    - 単元（lot_size）丸め、per-stock 上限・aggregate cap、cost_buffer による保守的見積もり。
    - 利用可能現金を超えた場合のスケールダウンと残差配分（fractional remainder を考慮して lot 単位で追加配分）。

- リサーチ / ファクター計算（DuckDB ベース）
  - factor_research（calc_momentum, calc_volatility, calc_value）
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）。
    - Volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - Value: raw_financials から EPS/ROE を取得し PER を計算（データ不足は None）。
    - DuckDB を用いた高速 SQL ウィンドウ関数実装。ターゲット日を引数に取る設計。
  - feature_exploration（calc_forward_returns, calc_ic, factor_summary, rank）
    - 将来リターンの一括取得（複数ホライズン対応、horizons のバリデーション）。
    - Spearman ランク相関（IC）計算。欠損やレコード不足時に None を返す安全設計。
    - ファクター列の基本統計量（count/mean/std/min/max/median）を計算。

- AI ニュース NLP スコアリング（OpenAI 統合）
  - ai/news_nlp.py
    - raw_news と news_symbols から銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）へバッチ（最大 20 コード/コール）で送信。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を UTC に変換して対象記事を抽出。
    - 最大記事数・最大文字数でトリム（1 銘柄あたり最大 10 記事、最大 3000 文字）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ実装（上限あり）。
    - レスポンス厳格検証（JSON 形式、results キー、コードと数値スコア）とスコアクリッピング（±1.0）。
    - 成功した銘柄のみ ai_scores テーブルで置換（DELETE + INSERT）して部分失敗時の既存データ保護を実現。
    - OpenAI API キー未設定時は ValueError。

- ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading DB（デフォルト data/paper_trading.db）を参照して期間集計レポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - PASS/FAIL 判定基準を定義（デフォルト閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - コマンドライン引数 --from / --to / --db をサポート。

### 変更 (Changed)
- n/a（初期リリースのため既存機能の変更はなし）

### 修正 (Fixed)
- n/a（初期リリースのためバグ修正はなし）

### 注意点 / 既知の制限 (Known issues / Notes)
- Settings._find_project_root は .git または pyproject.toml を基準にルートを特定する。配布パッケージや特殊な配置では自動 .env ロードがスキップされる可能性がある。
- process_priority / set_cpu_affinity は権限不足や未対応プラットフォームではスキップされ、警告ログを出す設計（安全第一）。
- position_sizing の price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性あり（将来的に価格フォールバックを検討）。
- ai/news_nlp の処理は OpenAI の利用上限・コスト・レスポンス変動に依存するため、運用時は API キーおよびコスト管理に注意。

### 環境変数一覧（主なもの）
- KABUSYS_ENV: development | paper_trading | live（必須ではないが値検証あり）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 各種 API 認証情報（Settings で必須チェック）
- OPENAI_API_KEY: AI スコアリング用
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, LOG_LEVEL など

---

今後のバージョンでは、テスト追加、ドキュメント整備、AI スコアリングの耐障害性向上、価格フォールバックの導入、銘柄別 lot_size 対応（TODO に記載）などを想定しています。必要な項目やフォーマット変更があればお知らせください。