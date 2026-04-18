Keep a Changelog 準拠 — 変更履歴
================================

すべての重要な変更はこのファイルに記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

### Added
- 設定ロード/管理を強化
  - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
  - .env パーサを改善（export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理）。
  - Settings クラスに多数のプロパティを追加／整備（J-Quants / kabu API / DuckDB/SQLite パス / paper_trading 用 DB パス / PID/KillFlag 関連 / 各種監視閾値など）。
  - PAPER_FILL_MODE の入力検証を追加（有効値チェック）。

- 起動スクリプト・デーモン関連
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ（data/stop_requested.flag）検出で安全にシャットダウン。
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB と MockBroker を使用する挙動を実装。停止フラグ／PID ファイル管理、スレッド実行による安全停止処理を実装。

- 開発支援 CLI
  - config_setup.py：対話式 .env 作成・更新ウィザードを追加。既存値の読み込み、シークレットマスク表示、保存確認を提供。
  - validate_config.py：環境変数・config/*.yaml の起動前検証ツールを追加。必須項目チェック、DB パスチェック、YAML パーシングチェック（PyYAML が無ければスキップ）、--strict オプションで警告も失敗扱いにできる。

- ロギング／プロセス管理ユーティリティ
  - utils/logging_setup.py：全アプリケーションで共通利用できるログ設定ユーティリティを追加。stdout 出力（StreamHandler）と日次ローテートファイル（TimedRotatingFileHandler）を統一的に設定。ログディレクトリ作成失敗時はファイル出力をスキップして警告出力。
  - utils/process_priority.py：クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。Windows/Linux/macOS を考慮し、権限や未対応環境では警告を出して安全にスキップ。

- ポートフォリオ構築 / サイズ計算
  - portfolio/portfolio_builder.py：候補選定（スコア順、タイブレーク）と等金額・スコア重み計算を実装。スコアが全て 0 の場合は等金額配分へフォールバック。
  - portfolio/risk_adjustment.py：セクター集中上限を適用する関数と市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームはフォールバックと警告出力。
  - portfolio/position_sizing.py：複数の配分方式（risk_based / equal / score）に対応した株数計算ロジックを実装。単元株（lot_size）丸め、銘柄別上限、aggregate キャップによるスケールダウン、残差分の再配分ロジックを実装。

- 解析ツール
  - tools/paper_verification_report.py：ペーパートレード用検証レポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を行う。
    - P95 計算ユーティリティ、日付フィルタ、DB パス解決（引数/環境変数/デフォルト）を実装。
    - 閾値は定数化（稼働率99%、成功率90% など）。

- 研究用ファクター計算（作業中）
  - research/factor_research.py にモメンタム系ファクター計算の骨格を追加（DuckDB 接続を受け、prices_daily / raw_financials を参照する設計）。モジュールは部分実装（メモ：calc_momentum など）。

### Changed
- DB 初期化の扱いを統一
  - monitoring テーブル類の初期化を呼び出し（init_monitoring_db を起動時に実行）して冪等にテーブル存在を保証。
- run_monitoring.py の挙動
  - Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を利用する旨を明記（意図的な設計）。
- run_execution.py の DB 選択
  - paper_trading 環境時に専用 paper SQLlite DB を使用して本番データと完全分離する実装。
- ロギングの挙動
  - stdout を利用するように仕様を明確化（cron/task scheduler でのリダイレクト取り扱いを考慮）。

### Fixed
- 環境変数パースの堅牢化
  - _get_poll_interval() で 0 以下や非数の値を検知した際にログを出してデフォルトにフォールバックする実装を追加（time.sleep に渡す負の値回避）。
- 権限や未対応プラットフォームに対するフォールトトレラントな振る舞いを追加
  - process_priority.set_process_priority / set_cpu_affinity は権限エラーや未実装 API を捕捉し、ログ警告を出してスキップするようにした。
- ログディレクトリ作成失敗時の取り扱いを改善
  - ログディレクトリ作成に失敗した場合に例外で落とさず、ストリームのみで継続するフォールバックを実装。

0.1.0 — 2026-04-11
-------------------
（初回公開相当のリリース。コードベースの主要機能をまとめてリリース）

### Added
- 基本パッケージ構成
  - kabusys パッケージ初期化（__version__ = 0.1.0）
  - サブパッケージ: portfolio, execution, monitoring, tools, research, utils などの雛形／実装。
- 実行系
  - ExecutionEngine の起動スクリプト（run_execution.py）、外部ブローカークライアント抽象化（BrokerClientFactory）、OrderManager / OrderRepository / RiskManager / Reconciler の組立てロジックを実装。
- 監視系
  - SystemMonitor の起動スクリプト（run_monitoring.py）および監視 DB 初期化ユーティリティ（init_monitoring_db）を実装。
- 設定管理
  - Settings クラスと自動 .env ロード（.env / .env.local の読み込み順、OS 環境優先）を実装。
- 開発ツール
  - 対話式設定ウィザード（config_setup.py）と設定検証 CLI（validate_config.py）を実装。
- ロギング・プロセス
  - 共通ロギング設定ユーティリティ（utils/logging_setup.py）とプロセス優先度管理（utils/process_priority.py）を実装。
- ポートフォリオ構築
  - 候補選定、重み計算、セクター制限、レジーム乗数、ポジションサイズ計算のコア関数群を実装（純粋関数で DB 非依存）。
- 検証レポート
  - Paper Trading 用の検証レポート生成ツール（tools/paper_verification_report.py）を実装。

### Changed
- 主要コンポーネントはなるべく副作用を抑えた純粋関数とユーティリティ化を目指して実装。
- デフォルト設定・ファイルパスは data/ ディレクトリ配下に集約。

### Fixed
- 起動時の環境変数読み込み・パースに関する既知の曖昧さを修正し、より堅牢なパーサを導入。

Deprecated
----------
- なし

Removed
-------
- なし

Security
--------
- なし

注記 / 今後の作業予定
- research/factor_research.py はモメンタム等のファクター計算の骨組みを持つが、完全実装は継続作業中。DuckDB のクエリ最適化や edge case の追加検証が必要。
- position_sizing の lot_size を銘柄別に対応する拡張や、price 欠損時のフォールバックロジック（前日終値や取得原価）を検討中。
- 本番運用前に validate_config.py で設定を検証し、KABUSYS_ENV=live 時のガード（LINE 通知設定、KILL_FLAG の扱い等）を十分に確認すること。