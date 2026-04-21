CHANGELOG.md
=============

このリポジトリの変更履歴は「Keep a Changelog」形式に準拠しています。  
以下は、提示されたコードベースの内容から推測して作成した変更履歴です（コードの実装・コメントに基づく要約）。実際のコミット履歴ではない点にご注意ください。

Unreleased
----------
### Added
- ログ出力を統一的に設定するユーティリティを追加
  - kabusys.utils.logging_setup: stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定し、ログディレクトリ作成失敗時はファイル出力をスキップする実装を導入。
- プロセス優先度・CPU affinity 設定ユーティリティを追加
  - kabusys.utils.process_priority: Windows/Linux（POSIX）差分を吸収し、優先度設定（high/normal/low）と CPU affinity 固定の関数を提供。アクセス権限不足時は安全にスキップ。
- 環境設定ウィザード CLI を追加
  - kabusys.config_setup: 対話式で .env を生成・更新するウィザードを追加（シークレットマスク、既存値再利用、保存前確認付き）。
- 設定検証 CLI を追加
  - kabusys.validate_config: .env や config/*.yaml の有無・基本整合性をチェックするツールを追加。--strict による警告の FAIL 扱い対応。
- Paper Trading 検証レポート生成ツールを追加
  - kabusys.tools.paper_verification_report: ペーパートレード用 SQLite を解析し、稼働率・注文成功率・レイテンシ等の指標を算出して PASS/FAIL を判定するレポートを出力。
- ポートフォリオ構築関連の純粋関数群を追加
  - kabusys.portfolio:
    - portfolio_builder: 候補選定（スコア降順）・等重/スコア重み算出。
    - position_sizing: 株数算出ロジック（risk_based / equal / score）、単元株丸め、aggregate cap スケーリング、コストバッファ考慮。
    - risk_adjustment: セクター上限除外ロジック（既存保有に基づく）と市場レジーム乗数（bull/neutral/bear）。
- 実行系・監視系の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を立ち上げるエントリ。paper_trading 時に専用 DB を使う分離、BrokerFactory 経由でブローカークライアントを選択、停止フラグ（data/stop_requested.flag）による安全停止、PID ファイル管理。
  - run_monitoring.py: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数で間隔上書き、監視 DB 初期化や duckdb 連携、停止フラグ検知でループ終了。
- 設定読み込みの堅牢化
  - kabusys.config: .env 自動ロード（.env, .env.local）機能を追加。export 前置、クォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。OS 環境変数の保護（上書き回避）機構を実装。
- 設定アクセスラッパーを追加
  - Settings クラスを提供し、各種環境変数（JQUANTS, KABU, DB パス, PAPER_FILL_MODE 等）をプロパティとして検証付きで取得可能に。
- DuckDB と SQLite の両方を想定したデータアクセス基盤を導入
  - 多くのモジュールが sqlite3 および duckdb 接続を受け取る設計に。

### Changed
- ログ出力の既定を stdout に統一
  - cron/task scheduler からの起動を想定し stderr ではなく stdout を StreamHandler に設定。
- .env の読み込み優先順位
  - OS 環境 > .env.local > .env の順で読み込む。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能。
- Paper Trading と本番 DB の明確な分離
  - run_execution では settings.is_paper に応じて paper_sqlite_path を使用。

### Fixed
- .env パーサの不整合対応
  - export キーワード、シングル/ダブルクォート内でのエスケープ、インラインコメントの扱いなどに対する堅牢化を実施。
- ウィザードの既存値表示・マスク処理
  - secret 項目は表示時にマスクし、Enter で既存値を再利用可能に修正。

0.1.0 - 2026-04-21
------------------
初回リリース（コードベースの主要機能をまとめたリリース：以下は実装から推測される主要項目）

### Added
- コア機能
  - 自動売買システムの基盤モジュール群を実装:
    - 実行エンジン（ExecutionEngine）起動スクリプト（run_execution.py）
    - 監視コンポーネント（SystemMonitor）起動スクリプト（run_monitoring.py）
    - 監視用 SQLite DB 初期化ロジック
    - ブローカークライアントの抽象化（BrokerClientFactory）とモック／本番切替（paper_trading サポート）
- ポートフォリオ構築
  - 候補選定、重み計算、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算（単元株丸め、リスクベース配分、スケーリング）を提供。
- 設定関連ツール
  - 対話式 .env ウィザード（config_setup.py）
  - 起動前検証ツール（validate_config.py）
- 運用ツール
  - Paper Trading 検証レポート（tools/paper_verification_report.py）: 稼働率、注文成功率、API レイテンシ等を算出し PASS/FAIL を判定。
- ユーティリティ
  - ロギング設定（utils/logging_setup.py）
  - プロセス優先度・CPU affinity 設定（utils/process_priority.py）
  - 環境変数の安全な読み込みと Settings API（config.py）
- 研究用モジュール（research/factor_research.py）
  - DuckDB を用いたファクター計算インターフェース（モメンタム・ATR 等）を開始実装（prices_daily/raw_financials ベース）。

### Changed
- 設定とデータベースの既定値を明確化
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH のデフォルトを data/ 配下に設定。
- ログのローテーション・保持機能を導入（30日分）。
- 起動スクリプトでのプロセス優先度設定を起動直後に行い、エンジンの安定性を向上。

### Fixed / Safety
- 実行時の停止フラグ（data/stop_requested.flag）による安全停止を両スクリプトで実装。
- ペーパートレード時に本番 DB を汚染しないよう専用 DB を使用する分離を実装。
- 設定検証で本番環境（KABUSYS_ENV=live）の危険箇所（LINE 未設定、KILL_FLAG_CLEAR_ON_START 等）を警告。

Notes / その他
- 一部モジュール（research/factor_research.py）は計算ロジックの実装が継続中のため、今後の拡張でより多くのファクターや最適化が追加される見込みです。
- .env の自動ロードはプロジェクトルートの検出に依存するため、配布後やパッケージ化後は自動ロードを無効化するオプション（KABUSYS_DISABLE_AUTO_ENV_LOAD）を利用してください。

参考: 主なソースファイル
- run_execution.py, run_monitoring.py
- config.py, config_setup.py, validate_config.py
- utils/logging_setup.py, utils/process_priority.py
- portfolio/*（portfolio_builder, position_sizing, risk_adjustment）
- tools/paper_verification_report.py
- research/factor_research.py

（この CHANGELOG は提示されたコードベースの構成・ドキュメント文字列から推測して作成しています。実際の変更履歴はコミットログをご確認ください。）