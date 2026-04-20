CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。
セマンティックバージョニングを採用します。  

0.1.0 - 2026-04-20
------------------

Added
- 初回公開リリース。
- 実行スクリプトを追加:
  - run_execution.py: ExecutionEngine を起動するメインスクリプト。KABUSYS_ENV により paper_trading 時は MockBrokerClient を用い、paper_trading 用の専用 SQLite（data/paper_trading.db, 環境変数で上書き可）を使用する。停止フラグ（data/stop_requested.flag）と PID ファイル管理に対応。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する。
- 環境設定・検証ツールを追加:
  - config_setup.py: .env の初期作成・更新を対話式に支援するウィザード。主要な設定項目とデフォルトを提示して保存可能。
  - validate_config.py: .env と config/*.yaml の整合性検証 CLI。--strict で警告を失敗扱いにできる。
- 環境変数・設定管理:
  - config.py: .env 自動ロード（.env → .env.local の順、OS 環境変数優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。各種設定値をプロパティとして提供（DBパス、ログレベル、監視閾値、PAPER_FILL_MODE 等の検証を含む）。
  - .env パーサーを実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理。
- ロギングユーティリティ:
  - utils/logging_setup.py: 統一的なログ設定関数 setup_logging を提供。コンソール出力（stdout）と日次ローテーションファイル出力（logs/<app>.log、30日保持）をルートロガーに設定。LOG_DIR / LOG_LEVEL 環境変数に対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- プロセス管理ユーティリティ:
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（high/normal/low）を提供。CPU affinity 設定ユーティリティも追加。psutil の権限不足等を安全にハンドリング。
- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、signal_rank でタイブレーク）、等重み・スコア重みの計算関数を追加。スコア全てが 0 の場合は等重みへフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap と、市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear マップ）を追加。未知レジームはフォールバックして 1.0 を返す。
  - portfolio/position_sizing.py: position sizing 実装。allocation_method（risk_based / equal / score）をサポートし、単元（lot_size）丸め、単銘柄上限、aggregate cap によるスケーリング、cost_buffer を用いた保守的なコスト見積り等を実装。
  - portfolio/__init__.py に上記関数群をエクスポート。
- Research / データ処理:
  - research/factor_research.py: DuckDB 接続を受け取り、prices_daily / raw_financials を用いてモメンタム等のファクターを計算するための基盤を追加（モジュール開始、定数定義）。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py: Paper Trading の SQLite DB（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し、閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency 200ms）に基づく PASS/FAIL レポートを生成する CLI を実装。
- 監視 DB 初期化:
  - monitoring.monitoring_db.init_monitoring_db を呼ぶことで監視用テーブルの存在を保証（冪等）。
- パッケージメタ:
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- ロギングの挙動: コンソール出力は標準エラーではなく標準出力（stdout）を使用するように統一（cron / スケジューラからのリダイレクト想定）。
- 設定ファイル読み込み順: OS 環境変数 > .env.local > .env（.env.local は .env を上書き）。既存 OS 環境変数は保護され、意図せぬ上書きを防止。
- 実行・監視の DB 接続ポリシー:
  - run_execution: paper_trading 環境時は paper_sqlite_path を使用して本番 DB と分離。
  - run_monitoring: 監視は環境にかかわらず Settings.sqlite_path（本番の監視 DB）を使用する方針を明示。

Fixed / Improved
- .env のパース機能を堅牢化: export プレフィックス、クォート内のエスケープ、インラインコメント処理などに対応（より現実的な .env 形式に対応）。
- 環境変数検証ツール（validate_config）を充実:
  - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、LOG_LEVEL の検証、DB パス親ディレクトリ存在チェック、config/*.yaml の存在および PyYAML が利用可能な場合のパース検証、KABUSYS_ENV=live 時の本番向け警告など。
  - --strict オプションで警告を失敗（exit code 1）扱いにできる。
- process_priority と CPU affinity の実装は権限エラーや未対応 OS を安全にハンドリングするよう改善。

Security
- .env を生成する config_setup はファイル先頭に「.env は絶対に Git にコミットしないこと」と明記（運用上の注意喚起）。

Notes / Known behaviours
- MONITOR_POLL_INTERVAL の値が整数でない、または 0 以下の場合は警告を出してデフォルト（60 秒）にフォールバックする実装。time.sleep に不正値を渡さないための安全策を採用。
- PAPER_FILL_MODE は "instant" / "partial" / "never" / "reject" のいずれかでなければ ValueError を投げる（誤設定検出）。
- apply_sector_cap において price が欠損（0.0）の場合はエクスポージャーが過少見積りとなる可能性があり、将来の改善ポイントとしてフォールバック価格（前日終値等）の導入をコメントで明記。
- position_sizing の将来的拡張候補として銘柄ごとの lot_size をデータで持つ設計への言及あり。

Assets / Files
- デフォルト DB / ファイルパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID/flag 等: data/execution.pid, data/stop_requested.flag, data/kill.flag
  - ログ: logs/<app>.log

Deprecated
- なし（初回リリース）。

Removed
- なし（初回リリース）。

Security
- なし（現状のコードから重大なセキュリティ修正は推測不可）。

開発者向けメモ
- 今後の改善案（コード内にも TODO コメントあり）:
  - position_sizing での銘柄別 lot_size サポート（stocks マスタの導入）。
  - apply_sector_cap の価格欠損時のフォールバックロジック。
  - research/factor_research モジュールのファクター計算ロジックの完全実装とテスト追加。
  - 実行コンポーネント（ExecutionEngine / BrokerClient 等）の詳細実装とユニットテスト強化。

---  
（この CHANGELOG は、リポジトリ内のコード構造・コメントから推測して作成しています。細かな動作や追加の変更点は実際のコミット履歴や開発ノートをご参照ください。）