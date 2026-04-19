# Changelog

すべての注目すべき変更点はこのファイルに記録します。ルールは "Keep a Changelog" に準拠します。

なお、本CHANGELOGはコードベースの内容から推測して作成しています（自動生成された実装ドキュメントに基づくまとめ）。実際のリリースノートとして使用する際は、必要に応じて補正してください。

## [0.1.0] - 2026-04-19

Added
- 初回公開リリース。
- 実行/監視エントリポイント
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory により実運用/モックブローカを切り替え可能。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をデーモン Thread で実行。stop flag（data/stop_requested.flag）と PID ファイル（data/execution.pid）で制御。
    - duckdb を分析用に接続。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視データは単一の monitoring DB に記録）。
    - 停止フラグ（data/stop_requested.flag）検出で安全にループ終了。
    - duckdb を分析用に接続。

- 設定管理・初期化
  - config.py
    - Settings クラスを導入し、環境変数・.env/.env.local の自動読み込み（OS 環境変数を上書きしない保護付き）。
    - .env パーサは export 形式、クォート付きの値、インラインコメント等に対応。
    - 各種既定値とバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。
    - paper_trading 用の paper_sqlite_path や各種閾値、PID/kill flag パスなどの設定プロパティを提供。
  - config_setup.py
    - 対話式 .env 作成ウィザードを追加。既存 .env 読み込み、入力補完、シークレットマスク、保存機能を提供。
    - デフォルト項目群（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）を定義。
  - validate_config.py
    - 起動前に設定不備を検出する CLI（--strict オプションあり）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パス親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML があれば）パース検証、本番向けガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）によるファイル出力を設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装し、既存ハンドラをクリアして二重設定を防止。
    - ファイルハンドラはデフォルトで logs/<app_name>.log、30 日分バックアップ。
  - utils/process_priority.py
    - プラットフォーム（Windows / POSIX 系）を吸収したプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。psutil を利用し、権限不足や未対応 OS では警告を出力してフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）と配分重み計算（calc_equal_weights, calc_score_weights）を導入。スコアが全て 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（既存保有の時価ベースでセクターごとの露出を計算し、上限超過セクターの候補を除外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear 対応）を追加。
  - portfolio/position_sizing.py
    - 株数計算ロジック（risk_based / equal / score）を実装。単元（lot_size）で丸め、per-position および aggregate キャップ、cost_buffer（手数料・スリッページ見積り）を考慮したスケールダウンロジックを持つ。

- 分析・研究
  - research/factor_research.py
    - DuckDB（prices_daily / raw_financials）を利用したファクター計算モジュールの骨子を追加（モメンタム、MA200、ATR、出来高系等を計画）。calc_momentum 等の関数が実装開始（価格系列のスキャン範囲や窓長の定数を定義）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（環境変数）または --db オプションで DB 指定可能。
    - システム安定性（稼働率）、注文成功率/送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を集計し、閾値に対する PASS/FAIL 判定を行う。
    - P95 計算、日付範囲フィルタ、データ欠損時の N/A ハンドリングを実装。

- パッケージ基礎
  - __init__.py によるバージョン定義: __version__ = "0.1.0"。
  - パッケージ公開インターフェース（portfolio モジュールのエクスポート等）を整備。

Security
- 特になし（初期リリース）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Notes / 動作上の重要な挙動（利用者向け）
- .env の自動ロード
  - デフォルトでプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env / .env.local を読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください。
- Paper Trading と Live の DB 分離
  - 実行エンジンは paper_trading 環境時に PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番データと分離します。監視は環境に関係なく sqlite_path（デフォルト data/monitoring.db）を使用します。
- 停止制御
  - data/stop_requested.flag（プロジェクトルート配下）を配置することで監視ループ／実行エンジンを安全に停止できます。起動時に stop フラグが既に存在する場合、エンジンは起動しません。
- ログ管理
  - デフォルトは logs/<app_name>.log に日次ローテーションで出力（30 日分保持）。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- 権限・環境差異の取り扱い
  - process_priority / cpu_affinity は権限不足や未対応環境で失敗しても警告を出力して安全にフォールバックします。

参照
- 各 CLI:
  - python -m kabusys.config_setup   （.env ウィザード）
  - python -m kabusys.validate_config  （設定検証）
  - python -m kabusys.tools.paper_verification_report  （Paper Trading レポート）
  - python -m kabusys.run_execution  / python -m kabusys.run_monitoring  （サービス起動）

--- 

（必要に応じて、実際の変更履歴・貢献者・リリース日などの実データを反映してください。）