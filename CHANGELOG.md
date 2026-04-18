CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従っています。
このファイルはコードベースから推測して生成した初回リリースの変更履歴です。

Unreleased
----------

（なし）

0.1.0 - 2026-04-18
------------------

Added
- 基本アプリケーション情報
  - パッケージメタデータを追加（kabusys.__version__ = "0.1.0"）。
- 起動スクリプト
  - run_monitoring: システム監視ループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルート/data/stop_requested.flag ファイルの検出で行う。
    - monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化する。
    - DuckDB と SQLite の接続を確立し SystemMonitor.check_once() を定期実行。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory により実環境／Mock ブローカーの選択を行う（paper_trading では MockBrokerClient を想定）。
    - ExecutionEngine を別スレッドで実行し、停止フラグ（data/stop_requested.flag）でセーフシャットダウン。
    - 実行系用の PID ファイル管理（data/execution.pid を使用する設定）をサポート。
- 設定管理
  - Settings クラスを追加し環境変数から各種設定を取得。
    - DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、API トークン、LINE 通知設定、監視しきい値などをプロパティとして提供。
    - KABUSYS_ENV（development / paper_trading / live）の検証やログレベルの検証を実装。
    - PAPER_FILL_MODE の妥当性検証（"instant" / "partial" / "never" / "reject" を許容）。
  - 自動 .env ロード機能を実装（プロジェクトルートの .env / .env.local を読み込み）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パースの堅牢化:
    - export キーワード、クォート（シングル/ダブル）、エスケープ、インラインコメントの扱いに対応。
    - 上書きポリシーと protected（OS 環境変数保護）をサポート。
- 設定支援ツール
  - config_setup: .env 対話式ウィザードを追加。既存値の読み込み、秘匿入力、確認・保存までサポート。
  - validate_config: 起動前に .env と config/*.yaml の状態を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認を行う。
    - PyYAML がない場合は YAML 内容検証をスキップし警告を出す。
    - --strict オプションで警告を FAIL 扱いにできる。
    - 本番環境向けの安全策チェック（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険設定など）を実装。
- ロギングとプロセス制御ユーティリティ
  - logging_setup:
    - StreamHandler（stdout）＋ TimedRotatingFileHandler（日次・30世代）をルートロガーに設定。
    - 既存ハンドラのクリア、自動ログディレクトリ作成（失敗時はファイル出力をスキップ）を実装。
    - LOG_LEVEL / LOG_DIR 環境変数対応。
  - process_priority:
    - Windows / POSIX (Linux/Mac/FreeBSD) を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS を考慮して失敗時は警告を出してスキップする設計。
- ポートフォリオ構築
  - portfolio.portfolio_builder:
    - 候補選定（select_candidates） — スコア降順、同点は signal_rank 昇順でタイブレーク。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）を実装。全スコア 0 の場合は等配分にフォールバックし warning を出す。
  - portfolio.risk_adjustment:
    - セクター集中制限（apply_sector_cap） — 既存保有比率が閾値を超えるセクターの新規候補を除外（unknown セクターは除外対象外）。
    - レジームに応じた投下資金乗数（calc_regime_multiplier） — "bull":1.0, "neutral":0.7, "bear":0.3、未知レジームはフォールバックで 1.0（警告）。
  - portfolio.position_sizing:
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - リスクベース（risk_pct, stop_loss_pct）や per-position / aggregate 上限、単元株（lot_size）丸め、手数料/スリッページ見積り（cost_buffer）を考慮したスケールダウンロジックを実装。
    - aggregate cap 超過時のスケールダウンと端数処理（lot 単位での再配分）を実装。
- 解析／研究モジュール
  - research.factor_research（部分実装）:
    - Momentum 等のファクター計算設計を記述。DuckDB の prices_daily, raw_financials を利用してモメンタム（1M/3M/6M）や MA200 偏差、ATR、流動性指標等を計算する方針を提示（実装は続く）。
- ツール
  - tools.paper_verification_report:
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計し検証レポートを出力する CLI を追加。
    - システム稼働率、注文成功率（fill/send）、リスク却下数、レイテンシ（平均/最大/P95）などを集計。
    - 合格判定用の閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL を判定。
    - 日付フィルタ（--from/--to）と DB パス指定 (--db) をサポート。
- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / Implementation details
- デフォルトのデータファイル/ログパス:
  - DuckDB: data/kabusys.duckdb
  - 監視用 SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログ: logs/<app_name>.log（LOG_DIR で上書き可）
- 停止・強制停止用フラグ:
  - data/stop_requested.flag により監視/実行の停止を検知。
  - PID ファイル / kill flag の取り扱いは Settings 経由でパス指定可能。
- セキュリティ/運用上の注意:
  - .env は Git にコミットしないことを README 等で明示するようにウィザードに注記がある。
  - validate_config により本番環境（KABUSYS_ENV=live）向けのガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 設定）を行う。

将来の改善候補（コード中の TODO などから推測）
- position_sizing: 銘柄別の lot_size 対応（マスタ拡張）。
- price の欠損時のフォールバック価格（前日終値等）を導入して exposure の過少見積りを防止。
- research.factor_research の続き実装（Momentum / ATR / Value / Liquidity 等の詳細計算）。
- monitoring の監視項目やアラート出力（LINE 連携等）の強化。

ライセンス、貢献方法、その他の運用手順についてはプロジェクトの README を参照してください。