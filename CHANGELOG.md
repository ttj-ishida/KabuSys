# Changelog

すべての非公開で重大な変更は明記します。本ドキュメントは Keep a Changelog の形式に準拠しています。
リリース日はプロジェクト内のバージョンおよび現時点の最終更新日（2026-04-17）に合わせています。

全体方針:
- セマンティックバージョニングを採用（本初期リリースは 0.1.0）。
- .env の自動ロード / ウィザード / 検証ツールや、監視・実行プロセス、ポートフォリオ構築ロジック、ユーティリティ、リサーチ用ファクター計算等を含む一通りの機能を提供します。

Unreleased
----------
（現在なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 初期リリース。
- 基本アプリケーション情報
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" と定義。

- 環境設定・管理
  - Settings クラス（src/kabusys/config.py）を追加し、環境変数経由で構成値を取得する共通インタフェースを提供。
    - J-Quants / kabuAPI / LINE / DB パス / 監視・システム設定等のプロパティを提供。
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証を行う。
    - PAPER_FILL_MODE の有効値チェック（instant / partial / never / reject）を実装。
    - 環境変数の自動ロード機能を追加（プロジェクトルートに .env / .env.local があれば自動で読み込む、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env 読み込みロジックはクォート・エスケープ・コメント対応、OS 環境変数を保護する override 動作を実装。

  - 対話式環境設定ウィザード（src/kabusys/config_setup.py）を追加。
    - .env ファイルの初期作成・更新をサポート。シークレット値はマスク表示。
    - 実行例: python -m kabusys.config_setup

  - 設定検証 CLI（src/kabusys/validate_config.py）を追加。
    - 必須環境変数や KABUSYS_ENV の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML が利用可能な場合の）パース検証を行う。
    - --strict オプションで警告を FAIL として扱う機能を追加。
    - 実行例: python -m kabusys.validate_config

- 監視（Monitoring）
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - SystemMonitor を使ったポーリングループを実行。既定のポーリング間隔は 60 秒で、環境変数 MONITOR_POLL_INTERVAL による上書きが可能（不正値はデフォルトにフォールバック）。
    - 停止制御はプロジェクト直下の data/stop_requested.flag ファイルで行う。
    - 監視用の SQLite DB は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計（監視は分離されない点に注意）。
    - プロセス優先度を「high」に設定する処理を起動時に行う。

  - 監視 DB の初期化ユーティリティ（monitoring_db への初期化呼び出し）を呼び出す処理を含む。

- 実行エンジン（Execution）
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading の場合、Broker の Mock 実装を利用し、paper_trading 用に分離した SQLite（デフォルト data/paper_trading.db）を使用する設計。
    - 実行中の PID 管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）による制御を実装。
    - BrokerClientFactory を通じて BrokerClient を生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動するワークフローを実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、initial_portfolio_value に broker.get_available_cash() を利用。

- ポートフォリオ構築（Portfolio）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順＋タイブレークルールで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコアが 0 の場合は等分にフォールバック）を実装。

  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合にそのセクターの新規候補を除外（unknown セクターは無視）。
    - calc_regime_multiplier: market_regime に応じた乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームはフォールバックで 1.0。

  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した発注株数計算を実装。
    - lot_size（単元株）、cost_buffer（スリッページ・手数料見積り）を考慮した aggregate cap のスケーリングロジックを実装。
    - risk_based ではリスク許容率（risk_pct）と損切り率（stop_loss_pct）から基準株数を算出。
    - 価格が取得できない銘柄をスキップし、単元株丸めと上限チェックを行う。

  - portfolio パッケージのエクスポートを整備（src/kabusys/portfolio/__init__.py）。

- リサーチ / ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）を追加。
    - DuckDB の prices_daily テーブルを使い、Momentum（1M/3M/6M、MA200乖離）や Volatility（ATR20 等）、流動性指標を計算する関数を実装。
    - データ不足時の扱いやウィンドウ要件（例: MA200 は 200 行以上必要）を明記。

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで指定）からデータを集計し、稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等を算出して PASS/FAIL 判定を行う。
    - デフォルトの閾値: 稼働率 99.0%、成立率 90.0%、送信率 95.0%、P95 レイテンシ 200ms。
    - 実行例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）を追加。
    - set_process_priority(level): Windows / POSIX 系を抽象化して nice / priority を設定。失敗時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスを固定する機能（未実行時は全コア）。
    - psutil に依存するため、権限やプラットフォームにより一部機能は無効になる可能性がある旨を考慮。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 実運用上の注意
- .env ファイルは決してリポジトリにコミットしないこと（config_setup にもその旨を明記）。
- 監視（run_monitoring）は環境にかかわらず監視用 sqlite_path を使用するため、監視 DB の取り扱いに注意すること。
- ペーパートレード用 DB は paper_trading 環境では本番 DB と分離される（PAPER_TRADING_SQLITE_PATH を利用可能）。
- MONITOR_POLL_INTERVAL、PAPER_FILL_MODE、KILL_FLAG_CLEAR_ON_START 等の環境変数で挙動を制御可能。設定値の妥当性チェックは Settings にて行われ、validate_config でも検出可能。
- process_priority や CPU affinity の設定はプラットフォーム依存で失敗する場合があり、その場合は警告を出力して継続します。
- Paper Verification レポートはデータが無い場合やテーブルが存在しない場合に安全にフォールバックして "N/A" を表示するよう実装されています。

Security
- 初期リリース時点で特筆すべきセキュリティ修正はありません。環境変数にシークレットを保持するため、適切なアクセス管理を推奨します。

Contact / Contributing
- バグ報告・改善提案は issue を通じてお願いします。次期リリースではテストの充実、エラーハンドリング強化、さらなる設定の柔軟化を予定しています。