# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

（現時点では未リリースの差分はありません）

## [0.1.0] - 2026-04-16

初回公開リリース。本リリースでは自動売買システム「KabuSys」のコア機能群を収録しています。
主な追加点は以下の通りです。

### Added
- 基本パッケージ情報
  - パッケージメタ情報を `kabusys.__version__ = "0.1.0"` として追加。

- 設定管理（kabusys.config）
  - 環境変数／.env ファイルからの設定読み込みを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により CWD に依存しない .env 自動ロード機能を提供。
  - .env パーサーを強化:
    - `export KEY=val` 形式の対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメント処理（クォート無しの場合は '#' の前が空白ならコメント扱い）。
  - 自動ロードを無効化するための環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - 各種設定プロパティを提供（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, 各種閾値など）。
  - `PAPER_FILL_MODE` の検証（有効値: "instant"、"partial"、"never"、"reject"）。
  - 実行環境判定プロパティ（`is_live`, `is_paper`, `is_dev`）。

- 実行／監視エントリポイント
  - run_execution（kabusys.run_execution）
    - ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 用 DB を使用して本番 DB と完全分離（環境変数 `PAPER_TRADING_SQLITE_PATH` または Settings.paper_sqlite_path）。
    - BrokerClientFactory を介したブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグファイル（data/stop_requested.flag）検知で安全に停止。
    - 実行 PID を data/execution.pid に保存（設定により上書き）。
    - RiskManager のデフォルト構成（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）。
  - run_monitoring（kabusys.run_monitoring）
    - SystemMonitor をポーリングで起動する監視スクリプト。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視データを記録。
    - 停止フラグファイル（data/stop_requested.flag）検知でループを終了。
    - プロセス優先度を起動時に "high" に設定。

- プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定する `set_process_priority` を提供。
  - CPU コア数を固定する `set_cpu_affinity` を提供。
  - アクセス権限や未サポート環境に対しては警告ログを出して安全にスキップ。

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定・重み計算（portfolio_builder）
    - `select_candidates`: スコア降順＋同点時 signal_rank によるタイブレークで候補を選定。
    - `calc_equal_weights`, `calc_score_weights`: 等金額配分・スコア比例配分（全スコアが 0 の場合は等配分にフォールバック、警告ログ）。
  - セクター制約とレジーム乗数（risk_adjustment）
    - `apply_sector_cap`: 既存保有を基にセクター集中を抑制。sell 対象銘柄をエクスポージャー計算から除外可能。"unknown" セクターは上限適用対象外。
    - `calc_regime_multiplier`: market regime に応じた投下資金乗数（"bull":1.0、"neutral":0.7、"bear":0.3、未知は 1.0 で警告）。
  - 株数決定（position_sizing）
    - `calc_position_sizes`: risk_based / equal / score の各割当方式に対応。損失リスク・単元株（lot_size）・max_position_pct・max_utilization・cost_buffer を考慮した株数計算と aggregate cap によるスケーリング処理を実装。
    - スケールダウン時は端数処理・残差に基づく lot_size 単位の追加配分ロジックを備える。

- 研究（research）モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - `calc_momentum`: 1M/3M/6M リターン、200日移動平均乖離を計算。
    - `calc_volatility`: 20日 ATR、相対 ATR、平均売買代金、出来高比を計算。
    - `calc_value`: raw_financials を用いた PER / ROE の計算（target_date 以前の最新財務レコード取得）。
    - DuckDB を用いた SQL ベースの高速計算を想定。
  - 特徴量解析（kabusys.research.feature_exploration）
    - `calc_forward_returns`: 指定 horizon リストに基づく将来リターン計算（複数ホライズンを一度のクエリで取得）。
    - `calc_ic`, `rank`, `factor_summary`: IC（Spearman ρ）計算、ランク付け、ファクターの基本統計量計算を実装。
  - `zscore_normalize` を外部（kabusys.data.stats）から再エクスポート。

- Paper Trading 検証ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）からデータを集計して検証レポートを標準出力に出力する CLI ツールを追加。
  - 指標:
    - 稼働率（uptime）閾値 99.0%、
    - 注文成功率（fill rate）閾値 90.0%、
    - 送信率（send rate）閾値 95.0%、
    - P95 レイテンシ閾値 200 ms。
  - コマンドラインオプション: --from, --to, --db（DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可）。
  - DB が無い場合やテーブル欠損時には N/A を扱いフェイルセーフに動作。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメントスコアを算出して `ai_scores` テーブルへ書き込む処理を実装。
  - 実装上の特徴:
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を計算する `calc_news_window`。
    - 記事数・文字数のトリム（1銘柄あたり上限 10 記事、3000 文字）。
    - 最大バッチサイズ 20 銘柄で API 送信、429/ネットワーク/5xx を対象に指数バックオフでリトライ。
    - レスポンス検証、スコアを ±1.0 にクリップ。
    - 部分失敗時でも既存スコアを保護するため、更新対象コードを限定して DELETE→INSERT を実施。
  - API キーは引数または環境変数 `OPENAI_API_KEY` から解決。未設定時は ValueError を送出。

- データベース初期化ユーティリティ
  - 監視テーブルなどを初期化する `init_monitoring_db` 呼び出しを run scripts 内で行い、冪等に監視テーブルの存在を保証。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Migration
- デフォルトの DB パス:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
- 監視・実行の停止/制御ファイル:
  - 停止フラグ: data/stop_requested.flag（存在検知で停止）
  - 実行 PID: data/execution.pid（ExecutionEngine）
  - kill フラグパスは Settings.kill_flag_path で変更可能
- 環境変数による挙動変更:
  - MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト 60）
  - KABUSYS_ENV （development / paper_trading / live）
  - PAPER_FILL_MODE（paper_trading の挙動）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（自動 .env ロード抑止）
  - OPENAI_API_KEY（ニュース NLP 用）

### Security
- OpenAI API キー等の機密設定は環境変数で扱うよう設計されています。`.env` 自動ロード機能は OS 環境変数を保護する仕組み（override/protected）を備えていますが、本番環境では `.env` に機密情報を置かないかアクセス制御を厳格にしてください。

---

今後の予定（例）
- ExecutionEngine / SystemMonitor の詳細ログ強化、メトリクス出力の整備
- 細やかなエラーリトライと監視アラート連携（LINE API など）
- ニュース NLP のモデル選択とプロンプト最適化、テスト用モックの整備

（注）本 CHANGELOG はソースコードから実装された機能・挙動を要約したものであり、実際のリリースパッケージや配布物と差異がある場合があります。