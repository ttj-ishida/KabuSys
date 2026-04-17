CHANGELOG
=========

すべての注目すべき変更をここに記録します。フォーマットは "Keep a Changelog" に準拠します。

[0.1.0] - 2026-04-17
--------------------

Added
- 実行用エントリポイントを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）を監視して安全に終了する。監視用 DB は環境にかかわらず本番 sqlite_path を使用する。（src/kabusys/run_monitoring.py）
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時はペーパートレード用の専用 SQLite を使用して本番 DB と分離、BrokerClientFactory を経由したブローカークライアントの作成、OrderRepository/OrderManager/RiskManager/Reconciler を組み合わせてエンジンをスレッドで実行。停止フラグと PID ファイルを扱う。（src/kabusys/run_execution.py）

- 設定管理の追加・改善
  - .env 自動読み込みをプロジェクトルート（.git または pyproject.toml）から行う機能を追加。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。（src/kabusys/config.py）
  - .env のパースを堅牢化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント取り扱いなど）。（src/kabusys/config.py）
  - Settings クラスを導入し、アプリ設定へのアクセスをプロパティ化（J-Quants トークン、kabu API、DB パス、PID/kill flag パス、閾値設定、環境判定プロパティ等）。PAPER_FILL_MODE の検証も追加。（src/kabusys/config.py）
  - settings インスタンスをエクスポート。（src/kabusys/config.py）

- 設定検証・ウィザード CLI を追加
  - validate_config.py: .env と config/*.yaml を起動前に検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの存在確認、PyYAML があれば YAML のパース検証、KABUSYS_ENV=live 時の追加ガード、--strict オプションで警告も FAIL 扱いに可能。（src/kabusys/validate_config.py）
  - config_setup.py: 対話式ウィザードで .env を初期生成／更新する CLI を追加。値のマスク表示やデフォルトの提示、保存前の確認、.env の書き込みロジックを実装。（src/kabusys/config_setup.py）

- ポートフォリオ構築・ポジションサイズ計算モジュールを追加
  - portfolio_builder: 候補選定（スコア降順、タイブレークの signal_rank ）、等金額・スコア加重の重み計算を実装。（src/kabusys/portfolio/portfolio_builder.py）
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームや unknown セクターの扱いに関する挙動を明記。（src/kabusys/portfolio/risk_adjustment.py）
  - position_sizing: allocation_method（risk_based / equal / score）に基づく株数計算、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer による保守的見積りを実装。（src/kabusys/portfolio/position_sizing.py）
  - portfolio パッケージのエクスポート定義を追加。（src/kabusys/portfolio/__init__.py）

- 研究・分析モジュールを追加
  - research/factor_research: DuckDB を用いたファクター計算（モメンタム、ボラティリティ等）の骨組みを追加。prices_daily / raw_financials を参照してモメンタム（1M/3M/6M、MA200乖離）や ATR/流動性指標を算出する関数を実装。（src/kabusys/research/factor_research.py）

- 運用ユーティリティ・改善
  - process_priority ユーティリティを追加（set_process_priority / set_cpu_affinity）。Windows / POSIX を吸収し、権限不足などのケースは警告を出してフォールバックする。起動スクリプトでプロセス優先度を "high" に設定する利用を追加。（src/kabusys/utils/process_priority.py）

- 運用ツールを追加
  - tools/paper_verification_report.py: ペーパートレード DB を集計して検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、レイテンシ（P95 など）に基づく PASS/FAIL 判定を行う。CLI オプションで期間指定と DB パス指定が可能。（src/kabusys/tools/paper_verification_report.py）

- 監視 DB 初期化ユーティリティを追加（init_monitoring_db を各起動スクリプトで呼び idempotent にテーブルを確保）（src/kabusys/monitoring/... を参照）

Changed
- .env 自動読み込みの優先順位を明確化：OS 環境変数 > .env.local > .env。（src/kabusys/config.py）
- 環境変数の扱いに保護（protected）機構を導入し、OS 環境変数を .env による上書きから保護する仕組みを追加。（src/kabusys/config.py）
- run_execution: paper_trading モード時に使用する SQLite を本番と完全に分離（settings.paper_sqlite_path を使用）。またリスク管理用デフォルトパラメータをコード内に設定。（src/kabusys/run_execution.py）
- 各種 CLI（config_setup / validate_config / paper_verification_report）でのユーザーフィードバック（マスク表示、確認メッセージ、情報出力）を改善。

Fixed
- 環境変数 MONITOR_POLL_INTERVAL のパースで不正値が指定された場合に警告してデフォルトにフォールバックするようにし、time.sleep に不正な値が渡らないように対策。（src/kabusys/run_monitoring.py）

Notes / Behavior & Safety
- run_monitoring は監視用テーブル作成のために sqlite3 接続を開き、duckdb を分析用に使用する。監視は本番 sqlite_path を参照するため、運用時は注意が必要。（src/kabusys/run_monitoring.py）
- run_execution は起動前に停止フラグを確認し、既に停止要求がある場合は起動せずに終了する安全対策を備えている。（src/kabusys/run_execution.py）
- Settings は KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE などの妥当性検査を行い、不正値は ValueError を送出する（起動時に早期検出可能）。（src/kabusys/config.py）
- config_setup による .env ファイルはデフォルトで Git にコミットすべきでない旨を注釈付きで出力する（.env の扱いに関する運用注意）。（src/kabusys/config_setup.py）

Deprecated
- なし

Removed
- なし

Security
- 特になし（機密情報は .env に保存する想定。config_setup は .env を生成する際に注意を促している）

---
注: 本 CHANGELOG はコードベースの内容（docstring・実装・CLI メッセージ等）から推測して作成しています。実際のリリースノート作成時は、変更差分（Git のコミット / PR）を基に詳細を補足してください。