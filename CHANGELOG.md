# CHANGELOG

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。  
リリース日はコードベースから推測して付与しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-21
初回リリース（推測）。以下の主要機能・ユーティリティ群を含む。

### 追加 (Added)
- 全体
  - KabuSys パッケージの初期公開版。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 実行/監視
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを行う。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番データベースと分離。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler 等を組み立て ExecutionEngine を起動する。
    - 停止用フラグファイル (`data/stop_requested.flag`) を監視し、検出時に安全に停止する仕組みを備える。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に（環境に依らず）本番用の sqlite_path を利用して監視 DB を初期化。
    - 停止フラグファイルの検出でループを終了、例外はログ出力して次回ポーリングへ継続。

- 設定管理
  - config: 環境変数 / .env 読み込みと Settings クラスを追加。
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出し `.env` / `.env.local` をロード（OS 環境変数は保護）。
    - `.env` の自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env 行パーサーは `export KEY=val` やシングル/ダブルクォート値、エスケープ、インラインコメント処理に対応。
    - 各種設定プロパティを提供（J-Quants トークン, kabu API パスワード, DB パス, PAPER_FILL_MODE, KABUSYS_ENV 等）。
    - PAPER_FILL_MODE の妥当性チェック（"instant" | "partial" | "never" | "reject"）。
    - KABUSYS_ENV の妥当性チェック（"development", "paper_trading", "live"）とログレベル検証。
  - config_setup: 対話式 .env ウィザードを追加。
    - .env の初期作成・更新を補助する CLI（`python -m kabusys.config_setup`）。
    - シークレット項目はマスク表示、選択肢・デフォルト提示、確認後 .env を保存。
    - .env に関する注意（絶対に Git にコミットしない等）を出力。

- 設定検証
  - validate_config: 起動前の設定検証 CLI を追加（`python -m kabusys.validate_config`）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL/DB パス の妥当性チェック。
    - config/*.yaml ファイルの存在/パースチェック（PyYAML がなければ警告してパースはスキップ）。
    - `--strict` オプションで警告も失敗扱いにできる。

- ユーティリティ
  - utils/logging_setup: 統一ログ設定ユーティリティを追加。
    - stdout へ StreamHandler、日次ローテート（TimedRotatingFileHandler）でファイル出力を設定。
    - ログディレクトリは引数・環境変数 `LOG_DIR`・デフォルト `logs/` を考慮。
    - ログレベルは引数・環境変数 `LOG_LEVEL`・デフォルト `INFO` の順で解決。ファイルローテーションは 30 日分保持。
    - 標準出力は stdout を採用（cron などでの集約を考慮）。
  - utils/process_priority: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）で差分を吸収して優先度設定を試みる。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。失敗時は警告でスキップ。
  - tools/paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - SQLlite の paper_trading DB（環境変数 `PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db`）から集計。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL を判定する閾値を定義。
    - コマンドライン引数で期間指定可能（--from / --to / --db）。

- ポートフォリオ構築（Pure functions）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順、同点タイブレークに signal_rank）。
    - 等金額配分 calc_equal_weights と スコア加重配分 calc_score_weights（スコア全て 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存ポジションの時価ベースでセクター露出を算出し、上限超過セクターの新規候補を除外）。"unknown" セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジーム（"bull","neutral","bear"）に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた株数決定ロジック。
    - リスクベースでは stop_loss, risk_pct を考慮してポジションサイズを算出。
    - lot_size（単元）に基づく丸め、1 銘柄上限・アグリゲート上限（available_cash）を超えた場合のスケーリングと残差処理を実装。
    - cost_buffer により手数料/スリッページを保守的に見積もり。

- 研究用
  - research/factor_research.py（部分実装を含む）
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してモメンタム等のファクターを計算する設計（関数 calc_momentum 等の雛形・定数を導入）。
    - 長期 MA、ATR、出来高等のウィンドウ長定義を含む。

### 変更 (Changed)
- なし（初回公開想定のため既存からの変更点無し）

### 修正 (Fixed)
- なし（初回公開想定）

### セキュリティ (Security)
- なし特記

### 注意点 / マイグレーションノート
- .env の扱い
  - デフォルトでプロジェクトルート（.git または pyproject.toml）を起点に `.env` / `.env.local` を自動ロードします。外部で環境を管理する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを抑制してください。
  - .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup のヘッダにも注意喚起を記載）。
  - `.env.local` は `.env` より優先して上書きされ、既存の OS 環境変数は保護されます。
- 環境変数名と既定値
  - DB: DUCKDB_PATH（default: data/kabusys.duckdb）、SQLITE_PATH（default: data/monitoring.db）、PAPER_TRADING_SQLITE_PATH（default: data/paper_trading.db）
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれか。`live` 時は追加の注意（LINE 通知設定や Kill Switch の取り扱い）を必ず確認してください。
  - PAPER_FILL_MODE の有効値は "instant" / "partial" / "never" / "reject"。不正値は起動時に例外を投げます。
- ログ
  - ログは既定で stdout に出力され、ファイルは `logs/<app_name>.log` に日次ローテートで保存されます。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続します。
- プロセス優先度
  - run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとします。権限不足等で失敗した場合は警告を出力して続行します。
- Paper Trading と本番データの分離
  - `paper_trading` 環境では paper_trading 用 SQLite を使用し、本番の monitoring DB と物理的に分離される設計になっています。Paper 環境で実際のブローカに接続しないよう BrokerClientFactory が適切なモックを返すことが期待されます。

---

今後のリリース案内やバグ修正・機能追加要望があれば CHANGELOG を更新します。