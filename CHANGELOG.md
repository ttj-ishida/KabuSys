CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

注: 本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際の変更履歴が別にある場合はそちらを優先してください。

Unreleased
----------

- なし

[0.1.0] - 2026-04-25
--------------------

Added
- 初期リリース: KabuSys (バージョン 0.1.0) を追加。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。プロセス優先度を "high" に設定し、停止フラグファイル（data/stop_requested.flag）による停止制御をサポート。監視は環境にかかわらず本番 sqlite_path を使用する。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（data/paper_trading.db デフォルト）を使用し、本番 DB と分離。プロセス優先度設定、PID ファイル管理、停止フラグによる停止、スレッドでのエンジン実行管理を実装。
- 設定管理
  - config.py: 環境変数／.env 自動ロード機能を実装（.env/.env.local をプロジェクトルートから読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。.env パーサは export 形式、クォート文字列、インラインコメント等に対応。各種設定プロパティ（DB パス、API トークン、監視閾値、環境判定など）を提供する Settings クラスを追加。
  - config_setup.py: 対話式 .env 設定ウィザードを追加（.env の初期作成／更新を支援）。シークレット項目はマスク表示、保存時に .env を書き出し（.env を絶対にコミットしない注意書き）。
  - validate_config.py: 起動前設定検証 CLI を追加。.env の必須項目チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML が有れば）パース検証、本番環境向けガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START=1 の警告）を実装。--strict オプションで警告を FAIL 扱い可能。
- ロギング・運用ユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーへ設定。LOG_DIR/LOG_LEVEL の解決順を実装し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続するよう堅牢化。
  - utils/process_priority.py: プラットフォーム差分を吸収したプロセス優先度設定ユーティリティを追加（Windows の priority class / POSIX の nice を扱う）。CPU アフィニティ設定用 set_cpu_affinity も提供。アクセス権限や未対応環境でのフォールバックと警告を実装。
- モニタリング DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を起動時に呼び出し、監視用テーブルが存在することを保証（冪等）。
- Execution コンポーネントの組み立て
  - ExecutionEngine 起動時に BrokerClientFactory を通じてブローカークライアントを生成（paper_trading では MockBrokerClient が想定される）。OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンを起動する構成を追加。RiskManager 用の既定設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を用意。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 銘柄候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコアが全て 0 の場合は等金額配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap とレジームに応じた投下資金乗数 calc_regime_multiplier を追加。セクター不明 ("unknown") の取り扱いや未知レジームのフォールバック等を実装。
  - portfolio/position_sizing.py: ポジションサイズ算出 calc_position_sizes を追加。allocation_method（"risk_based","equal","score"）に対応し、単元株（lot_size）処理、1 銘柄上限、aggregate cap（利用可能現金でスケールダウン）や cost_buffer を考慮した保守的見積り、端数処理（lot 単位での再配分）を実装。
  - portfolio/__init__.py: 主要関数をエクスポート。
- Research / ファクター計算
  - research/factor_research.py: DuckDB 接続を受け取り momentum 等のファクターを計算する基盤を追加（calc_momentum 実装の骨子、定数や設計方針を含む）。prices_daily / raw_financials のみを参照する方針。
- 運用ツール
  - tools/paper_verification_report.py: ペーパートレード DB（PAPER_TRADING_SQLITE_PATH / --db）からレポートを生成する CLI を追加。稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）等を計算し、所定の閾値に基づいて PASS/FAIL を判定。P95 計算・期間フィルタ（--from/--to）に対応し、テーブル未存在時には安全にハンドリングする。
- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし（初回リリース）

Notes / 動作上の考慮点（実装からの推測）
- .env 自動読み込みはプロジェクトルート検出に .git または pyproject.toml を使用するため、配布後もカレントワーキングディレクトリに依存せず動作する想定。
- ログディレクトリ作成やファイルハンドラの初期化に失敗した場合は、stdout ログのみで継続する設計になっており、運用環境での堅牢性を高めている。
- 設定検証では PyYAML 非依存で動作し、インストールされていない場合は YAML 検証をスキップして警告を出す。
- 多くの箇所で外部依存（psutil, duckdb, sqlite3, PyYAML）が使用されているため、本番導入前に依存パッケージの確認・インストールが必要。
- run_execution/run_monitoring は停止フラグファイル（data/stop_requested.flag 等）で外部から安全に停止できる設計。

作者注記
- この CHANGELOG は提供されたソースコードの内容から機能追加・設計意図を推測して作成しています。実際のコミットレベルの履歴やマイナーチェンジ（バグ修正等）は反映されていない可能性があります。必要であれば、個別ファイルや関数ごとにより詳細な変更点（例: 仕様決定理由、未実装 TODO 等）を追記します。