CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」準拠の形式で記載しています。  
セマンティックバージョニングを意識して変更を記録しています。コード内容から推測して作成しています。

Unreleased
----------
- 監視ループおよび実行エンジンの堅牢性向上
  - run_monitoring/run_execution 起動スクリプトのログ・例外処理を改善（check_once 例外捕捉、停止フラグ検出のログ化など）。
  - MONITOR_POLL_INTERVAL 環境変数値のバリデーションを追加し、不正な値はデフォルトにフォールバックするように変更。
  - 停止・PID 管理ファイル（data/stop_requested.flag、data/execution.pid 等）を利用した安全停止処理を明確化。

- ロギングの改善
  - setup_logging で既存ハンドラを一度クリアして二重登録を防止。
  - コンソール出力は stdout に統一し、ログディレクトリ作成失敗時はファイル出力をスキップして警告を出力するように改善。
  - 日次ローテート（TimedRotatingFileHandler）を導入し最大バックアップ日数を設定。

- 設定管理の改善
  - .env 自動読み込みの順序（OS 環境 > .env.local > .env）を明確化し、OS 環境変数を上書きしない保護機構を追加。
  - .env のパーサを改善（export プレフィックス対応、クォート付き値のバックスラッシュエスケープ処理、インラインコメント処理など）。
  - PAPER_FILL_MODE 等の列挙値検証を追加し、不正値は例外で通知。

- Paper Trading / 分離
  - paper_trading 環境向けに専用 SQLite DB を使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
  - KABUSYS_ENV=paper_trading 時は MockBroker を用いる設計に対応（実際のブローカーとデータは完全に分離）。

- DuckDB 統合
  - 分析用に DuckDB を導入（duckdb_path 設定）。起動スクリプトから接続確立。

- ポートフォリオ構築・サイズ決定ロジック（純粋関数）
  - portfolio モジュールを導入:
    - portfolio_builder: 候補選定（スコアソート）、等重/スコア加重の重み計算。
    - risk_adjustment: セクターキャップ適用、レジーム乗数（bull/neutral/bear）。
    - position_sizing: risk_based / equal / score の割当方式、単元株（lot_size）丸め、aggregate cap スケーリングロジック、コストバッファ対応。
  - 入力不備時に適切にログ出力してフォールバックする設計。

- 監視・検証ツール
  - validate_config CLI を追加し、.env と config/*.yaml の事前検証（必須環境変数チェック、パス存在チェック、YAML パースチェック、本番向けガード）を行えるようにした。
  - config_setup 対話ウィザードを追加し、.env の初期作成・更新を支援。
  - tools/paper_verification_report スクリプトを追加し、Paper Trading の稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL 判定を行う。

- プロセス優先度・CPU 固定ユーティリティ
  - set_process_priority/set_cpu_affinity を提供し、Windows/Linux/Mac の差分を吸収して設定を試みる。権限不足等は警告ログでスキップ。

- 起動・停止の安全策
  - 起動時にプロセス優先度を高めに設定するフローを標準化（まず set_process_priority を呼び出す）。
  - 起動時に停止フラグが既に立っている場合は起動を回避するチェックを導入。

- その他
  - パッケージ初期バージョン管理情報を __version__ に含める（"0.1.0"）。
  - モジュール間の責務分離（DB 初期化は init_monitoring_db、ロギング設定は utils.logging_setup、プロセス管理は utils.process_priority など）を明確化。

0.1.0 — 2026-04-24
------------------
初回公開（コードベースから推測される主要機能をまとめたリリース）:

Added
- 実行系・監視系起動スクリプト
  - run_execution.py: ExecutionEngine の起動、ブローカーファクトリ利用、OrderManager / OrderRepository / RiskManager / Reconciler の組み立て、スレッドでのセッション実行と停止フラグ監視を実装。
  - run_monitoring.py: SystemMonitor のポーリングループを実装。監視 DB（SQLite）と分析 DB（DuckDB）への接続を確立。

- 設定・検証・ウィザード
  - Settings クラスで環境変数をラップし、各種設定値（DB パス、API トークン、ログレベル、しきい値など）をプロパティで提供。
  - config_setup.py: 対話式ウィザードで .env を生成/更新。
  - validate_config.py: 起動前検証 CLI を追加（--strict オプションにより警告を失敗扱いにできる）。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: stdout ストリームハンドラと日次ローテートファイルハンドラを設定するユーティリティを実装。
  - utils/process_priority.py: クロスプラットフォームでの優先度設定・CPU affinity 設定関数を実装。

- ポートフォリオ・リスク系
  - portfolio モジュールを追加（候補選定、重み付け、リスク調整、ポジションサイズ決定）。
  - リスク制約（max_position_pct、max_utilization、cost_buffer 等）や lot_size 丸めロジックを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 DB から期間集計し、稼働率・成立率・送信率・レイテンシを計算して PASS/FAIL 判定するスクリプトを追加。

Changed
- .env 自動読み込みを実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
- 環境変数の優先順位と保護（OS環境変数を上書きしない）を明確化。

Fixed
- .env のパースで export プレフィックスやクォート付き値、バックスラッシュエスケープを正しく扱うように改良。
- ログディレクトリ作成失敗時にアプリがクラッシュしないようハンドリングを追加。

Acknowledgements / Notes
- DuckDB を分析用に使う設計だが、起動スクリプトでは DuckDB 接続を確立するのみ。分析関数（research モジュールなど）から利用する想定。
- 実際の ExecutionEngine / BrokerClient 実装の振る舞い（注文 API 呼び出し等）はこのコードベースからは部分的にしか推測できないため、実運用時は各モック/本番クライアントの動作確認を推奨。

（以上はソースコードの内容から推測して作成した変更履歴です。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。）