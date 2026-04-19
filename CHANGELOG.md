CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

Unreleased
----------

- （現在の開発ブランチの未リリース変更はここに記載します）

0.1.0 - 2026-04-19
------------------

Added
- 初回リリース。KabuSys 自動売買フレームワークの基本コンポーネントを追加しました。
  - エントリポイント / 起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、本番 DB と完全分離して動作。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、別スレッドでのエンジン実行・停止フラグ監視を実装。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告出力してデフォルトにフォールバック。
      - 停止フラグファイル（data/stop_requested.flag）検知によるグレースフルシャットダウン。
  - 設定管理・検証・ウィザード
    - config.py
      - .env 自動読み込み機能（プロジェクトルート検出）と Settings クラスを提供。
      - 環境変数の厳密チェック（KABUSYS_ENV / LOG_LEVEL の妥当性検証）、paper_fill_mode の妥当性チェック、各種パス（duckdb/sqlite 等）・フラグ設定プロパティを実装。
      - .env のパースは export プレフィックス、クォート、エスケープ、インラインコメント等を考慮。
    - config_setup.py
      - 対話式ウィザードで .env を作成・更新するツールを追加。秘密値のマスク表示、選択肢・デフォルトサポート。
    - validate_config.py
      - 起動前の設定検証ツールを追加（必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在/パース等をチェック）。
      - --strict オプションで警告を FAIL 扱いにできる。
  - データベース / 分析基盤
    - DuckDB 統合: duckdb_path を Settings で取得し、各スクリプトで接続して分析処理に利用。
    - 監視用 SQLite（monitoring.db）初期化ユーティリティを利用する初期化処理を導入（init_monitoring_db の呼び出し）。
  - ポートフォリオ構築（pure functions）
    - portfolio.portfolio_builder
      - 候補選定（select_candidates）、等重み・スコア加重（calc_equal_weights / calc_score_weights）を追加。スコア全てが 0 の場合は等重みへフォールバック。
    - portfolio.risk_adjustment
      - セクター集中上限の適用（apply_sector_cap）、市場レジームに応じた乗数計算（calc_regime_multiplier）を実装。未知レジーム時はフォールバック動作。
    - portfolio.position_sizing
      - 発注株数計算（calc_position_sizes）を実装。
      - risk_based / equal / score の配分方式をサポート。単元株（lot_size）丸め、最大ポジション上限、全体の aggregate cap によるスケールダウン、コストバッファの考慮、残差分配ロジックを実装。
  - ツール
    - tools.paper_verification_report
      - Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（平均 / 最大 / P95）等を集計し PASS/FAIL 判定を行う。閾値は定数で定義（稼働率 99% など）。
  - ユーティリティ
    - utils.logging_setup
      - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を追加する設定関数を提供。LOG_DIR / LOG_LEVEL を尊重し、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
      - 出力は stdout を採用（cron 等のリダイレクト運用を考慮）。
    - utils.process_priority
      - クロスプラットフォームのプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。Windows / POSIX（Linux/Mac/FreeBSD）を透過的に扱い、権限不足時は警告でスキップ。
  - 研究用モジュール（partial）
    - research.factor_research
      - DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム、MA200 乖離、ATR、出来高系などを計画）。（ファイルは途中まで実装）

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Notes / 利用上の注意
- run_monitoring は KABUSYS_ENV にかかわらず監視用 DB のパスとして Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。実行時の環境に応じて MONITOR_POLL_INTERVAL 等の環境変数で挙動を調整してください。
- run_execution は paper_trading モード時に paper_sqlite_path を使用し、本番 DB とは分離して動作します。ペーパートレードの挙動は PAPER_FILL_MODE 環境変数で制御できます（instant/partial/never/reject）。
- .env の自動読み込みはデフォルトで有効です。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 実行スクリプトは停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を利用したグレースフルな停止・プロセス管理を想定しています。

Authors
- KabuSys 開発チーム

Acknowledgements
- 本リリースはプロジェクトルート検出や .env パース、DuckDB / SQLite の組み合わせ、運用監視・ペーパートレード分離など、実運用を想定した設計を反映しています。