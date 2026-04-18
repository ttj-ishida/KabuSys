Keep a Changelog に準拠した CHANGELOG.md（日本語）

全般的な方針:
- 重要な変更点をカテゴリ別に列挙（Added / Changed / Fixed / Removed / Security）
- 各項目は該当するモジュール／スクリプト名や環境変数名を明記
- 日付は本リリース日（2026-04-18）

注意: 以下はソースコード内容から推測して作成した変更履歴です。実際のコミット履歴とは差異があります。

Changelog
=========

Unreleased
----------
（なし）

0.1.0 - 2026-04-18
-----------------

Added
- 初回リリース: KabuSys 自動売買フレームワークの基盤機能を追加
- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。環境変数 KABUSYS_ENV により paper_trading 時は専用の MockBrokerClient を使用し、Paper Trading 用 DB（data/paper_trading.db、PAPER_TRADING_SQLITE_PATH で上書き可）を利用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する設計。
- 設定関連
  - config.py: Settings クラスを実装し、環境変数の読み取り・検証ロジックを提供。自動 .env ロード機構（.env/.env.local）と保護付き上書きロジックを実装。PAPER_FILL_MODE 等の値検証、SQLITE/DUCKDB パスなどのプロパティを提供。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。多くの設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等）をサポート。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パース検証（PyYAML があれば内容も検証）、本番環境向けのガードチェックを実装。--strict オプションで警告を失敗扱いにできる。
- 監視・モニタリング
  - monitoring.monitoring_db: 監視用 DB 初期化ユーティリティ（init_monitoring_db）を実装（起動スクリプトから呼び出し、冪等に監視テーブルを確保）。
  - run_monitoring.py に停止フラグ（data/stop_requested.flag）検知と安全な終了処理を実装。
- Execution（実行エンジン）周り
  - 実行エンジンの組み立て（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の初期化フロー）を実装。
  - Paper Trading 時に本番 DB と完全分離する挙動を実装（settings.is_paper による sqlite_path 切替）。
  - ExecutionEngine はデーモンスレッドで run_session を実行し、停止フラグで engine.stop() を呼び出して安全停止する。
- ポートフォリオ構築（portfolio パッケージ）
  - portfolio_builder.py: 候補選定 select_candidates、等分配 calc_equal_weights、スコア重み calc_score_weights を追加（同点タイブレーク、スコアが全て 0 の場合のフォールバックロジック等）。
  - risk_adjustment.py: セクター集中上限を適用する apply_sector_cap、マーケットレジームに基づく投下資金乗数 calc_regime_multiplier を追加（regime に応じたデフォルトマッピングと未知レジーム時のフォールバック）。
  - position_sizing.py: allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算 calc_position_sizes を実装。単元株（lot_size）丸め、銘柄毎・合計の上限・cost_buffer に基づくスケーリング、残差の分配ロジックを実装。
- 分析・研究
  - research.factor_research.py: DuckDB を使ったファクター計算基盤を追加（モメンタム、MA200、ATR、ボリューム指標等を計算するための方針とユーティリティを実装）。（注: ファイル途中までの実装で、関数 calc_momentum の実装継続が想定される）
- ツール
  - tools.paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。期間指定 (--from / --to)、DB 指定 (--db) をサポート。稼働率・注文成功率・送信率・P95 レイテンシなどを集計し PASS/FAIL 判定（閾値はファイル内定数で管理）。
- ユーティリティ
  - utils.logging_setup.py: 統一ログ設定ユーティリティを実装。コンソール出力（stdout）と日次ローテートするファイルハンドラ（TimedRotatingFileHandler）をルートロガーへ設定。ログディレクトリ作成失敗時はファイル出力をスキップ、既存ハンドラの二重登録を防止するため一旦クリアする。
  - utils.process_priority.py: Windows / POSIX 差分を吸収したプロセス優先度設定と CPU affinity 設定を実装。set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。権限不足時は警告を出してスキップ。
- パッケージ情報
  - __init__.py: __version__ = "0.1.0" を設定。

Changed
- 環境変数取り扱いの強化（config.py）
  - .env ファイルのパースで export プレフィックス、クォート文字列、エスケープ、インラインコメント処理をサポート。OS 環境変数を保護する protected 上書きロジックを導入。
  - 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索し、見つからないときはスキップする挙動に変更（配布後の動作を安定化）。
- ログ設定の調整
  - StreamHandler を stdout に向ける設計（cron/task scheduler のリダイレクトを考慮）。
  - ローテーションとバックアップ日数（30 日）をデフォルトで設定。
- 実行・監視の挙動
  - run_execution/run_monitoring 起動時に最初にプロセス優先度を high に設定する処理を追加（set_process_priority の呼び出し）。
  - run_monitoring は MONITOR_POLL_INTERVAL の値検証を追加し、不正値時はデフォルト（60 秒）へフォールバックする。

Fixed
- 環境読み込みでの安全性向上
  - .env 読み込み失敗時に warnings.warn を行い起動を継続するように変更（IO エラー耐性）。
- ログディレクトリ作成失敗時の挙動明確化
  - ディレクトリ作成が失敗してもコンソールログは有効のまま続行するように変更し、問題を stderr に出力する。
- 設定検証の頑健性向上
  - validate_config.py で PyYAML 未インストール時に YAML 検証をスキップし、わかりやすい警告を出力するようにした。

Removed
- なし

Security
- なし（ただし .env は絶対に Git にコミットしない旨を config_setup の生成ファイルヘッダに明記）

Notes / その他の設計注記
- Paper Trading と本番 DB の完全分離:
  - settings.is_paper が True の場合、Execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用するため、本番監視 DB と分離される。
- Kill / Stop フラグ:
  - run_execution.py/run_monitoring.py といった長時間プロセスはプロジェクト内 data/stop_requested.flag を監視して安全に停止する設計。
  - PID ファイルパスや kill フラグ関連設定は Settings 経由で管理できる（PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START）。
- 一部実装が継続中:
  - research.factor_research.calc_momentum の実装がファイル末尾で途中になっている（今後の実装で DuckDB を用いた各種ファクター計算が完成予定）。

以上

（この CHANGELOG はコードの内容から推測して作成しています。実際のコミットログに合わせて適宜修正してください。）