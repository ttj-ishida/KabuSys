CHANGELOG
=========

このファイルは Keep a Changelog 準拠で記載しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（今後の変更をここに記載）

[0.1.0] - 2026-04-18
-------------------

Added
- 初期リリース: 基本的な自動売買システムのコア機能を追加。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。
- 起動スクリプト
  - run_execution: 実運用用 ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアントを BrokerClientFactory で構築、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) の扱いを実装。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ (data/stop_requested.flag) により安全にループを終了。
- 設定管理 / ユーティリティ
  - config: .env の自動読み込み、環境変数取得ユーティリティを実装（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順と保護（OS 環境変数の上書き防止）。
    - 各種設定プロパティ（DB パス、PID/kill flag、paper trading 設定、監視閾値など）を提供。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）を実装。
  - config_setup: 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - 入力支援、既存 .env の読み込み・編集、保存機能。
    - 実行例: python -m kabusys.config_setup
  - validate_config: 起動前に .env と config/*.yaml を検証する CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス・YAML ファイルの存在/パース確認、本番環境向けガードを実装。
    - --strict オプションで警告を失敗扱いにできる。
    - 実行例: python -m kabusys.validate_config
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（P95 等）を集計し PASS/FAIL を判定。
    - コマンド例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- ポートフォリオ構築（純粋関数群、DB 不要）
  - portfolio.portfolio_builder: 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクター上限適用・レジーム乗数（apply_sector_cap, calc_regime_multiplier）。
  - portfolio.position_sizing: 発注株数決定・リスク制限・単元丸め（calc_position_sizes）。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - aggregate cap スケールダウン、lot_size 単位での再配分ロジックを実装。
- ログ／プロセス管理ユーティリティ
  - utils.logging_setup: stdout ストリームハンドラと日次ローテーションファイルハンドラ（TimdRotatingFileHandler）をルートロガーに設定するユーティリティを追加（ログディレクトリ自動作成、LOG_LEVEL/LOG_DIR の解決ルール、30 日保持）。
  - utils.process_priority: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加（psutil ベース、Windows / POSIX 対応）。
    - 起動スクリプトでは最初に set_process_priority("high") を呼び出すように統一。
- 監視 DB 初期化
  - monitoring_db.init_monitoring_db を利用して監視用テーブルの冪等な初期化を行う呼び出しを run_execution/run_monitoring に追加。
- DuckDB 統合
  - 各種モジュール（実行エンジン、分析ツール等）で DuckDB 接続パス（デフォルト data/kabusys.duckdb）を使用する設計を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- 環境変数の自動読み込み時に OS 環境変数を保護する仕組みを導入（.env/.env.local の上書き制御）。

Notes / 運用上のポイント
- MONITOR_POLL_INTERVAL:
  - 監視ループのポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能。デフォルト 60 秒。不正値（0 以下や非整数）は警告してデフォルトにフォールバックします。
- Paper Trading と本番 DB の分離:
  - KABUSYS_ENV=paper_trading の場合、run_execution は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用します。監視（run_monitoring）は環境にかかわらず settings.sqlite_path を使用する設計になっています（意図的な挙動）。
- ログ:
  - デフォルトで logs/<app_name>.log に日次ローテーション（30 日保持）で出力。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
  - ログレベル解決順: 関数引数 > 環境変数 LOG_LEVEL > "INFO"
- プロセス優先度:
  - 起動スクリプトは開始時に set_process_priority("high") を呼び出します。psutil の権限不足等で設定できない場合は警告を出してスキップします。
- .env 自動読み込み:
  - デフォルトでプロジェクトルートの .env と .env.local を自動読み込みします。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- CLI:
  - 実行例:
    - 設定ウィザード: python -m kabusys.config_setup
    - 設定検証: python -m kabusys.validate_config [--strict]
    - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

既知の制限 / TODO
- position_sizing.calc_position_sizes:
  - 将来的に銘柄ごとの lot_size（単元）を stocks マスタで管理する設計への拡張予定（現状は全銘柄共通的に lot_size=100 を想定）。
- apply_sector_cap:
  - price_map に欠損（0.0）がある場合にエクスポージャーが過少見積りされてしまう点を注記。前日終値などのフォールバック価格を導入する余地あり。
- research.factor_research:
  - ファイル先頭に Momentum ファクターの計算関数があり（一部実装済み）。他ファクターや完全な実装は今後追加予定。

互換性 / 移行メモ
- 初回リリースのため後方互換の懸念はありませんが、.env のキー名や挙動（monitoring が本番 sqlite を使う等）を変更する際は運用手順の見直しが必要です。

作者 / コントリビューション
- 本リリースは初期機能群の実装です。機能追加・バグ修正は CHANGELOG の Unreleased に記録してください。