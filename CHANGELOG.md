CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは Keep a Changelog に準拠しています。  

バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に合わせています。

## [0.1.0] - 2026-04-23

### Added
- 初期リリース: KabuSys 日本株自動売買システムの基本コンポーネントを実装。
- 環境設定・読み込み
  - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で検出）。OS 環境変数を保護しつつ .env / .env.local を読み込む仕組みを提供（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプション）。
  - .env パース機能の強化: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント判定（クォートなしでは '#' の前がスペース/タブの場合のみコメント扱い）。
- 設定管理 API
  - Settings クラスを実装。環境変数から各種設定（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン、各種閾値、KABUSYS_ENV/LOG_LEVEL 等）を取得するプロパティを提供。
  - 各種プロパティで入力値検証を実施し、無効値は ValueError を送出（例: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の検証）。
- 対話式設定ウィザード
  - python -m kabusys.config_setup で .env の初期作成・更新を支援する CLI を追加。選択肢表示・シークレットマスク・確認プロンプト・保存処理を備える。
  - .env を生成する際にテンプレートヘッダ（Git にコミットしない旨の注意）を埋め込む。
- 設定検証 CLI
  - python -m kabusys.validate_config による起動前チェックを追加。
  - 必須環境変数の未設定チェック、プレースホルダ値検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML がインストールされている場合の）パース検証、KABUSYS_ENV=live 時の追加ガード（LINE 通知・Kill Flag 等）。
  - --strict オプションを追加（警告も FAIL 扱いで exit(1)）。
- 実行スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加。paper_trading 環境時は paper_trading 用 SQLite を使用して本番 DB と分離。プロセス優先度設定、停止フラグ／PID 管理を実装。
  - run_monitoring: SystemMonitor をポーリングする監視プロセス起動スクリプトを追加。MONITOR_POLL_INTERVAL によるポーリング間隔の上書き、監視用 DB 接続処理を実装。
- 実行エンジンと発注フロー
  - ExecutionEngine を実装。シグナルフェーズ（8:50–9:10）と push ドレインフェーズ（9:10–15:30）を持つセッション制御、WebSocket push 受信スレッド、kill.switch 処理、PID ファイル管理、Reconciliation 実行フックを実装。
  - シグナル処理時に Gate 1（シグナルレベル）、Gate 2（エグゼキューションレベル／レート制限）、Gate 3（ドローダウン監視）を順に評価し、NG 時は適切にスキップまたは kill_switch を発動する。
  - 発注成功時に position_entries へ約定予定日を書き込む処理（buy / sell の分岐）を追加。duckdb を用いたシグナル読み出し処理を実装。
  - 監視 DB（MonitoringDB）へ発注イベントのログを記録するフックを追加（latency_ms、約定数等）。
- ブローカー API クライアント
  - KabuStationClient を実装（同期 httpx クライアント）。トークン取得（遅延初期化）、認証付きリクエスト、401 時のトークン再取得とリトライ、429（RateLimitError）/ >=500 エラーの区別などを実装。WebSocket push を想定した stream_push フックも利用可能な設計。
- 注文状態と管理
  - OrderRecord: 注文状態を表すステートマシン（OrderCreated, OrderSent, OrderAccepted, PartialFill, Filled, Closed, Cancelled, Rejected）と遷移検証を実装。InvalidStateTransitionError を定義。
  - OrderManager: create/send/sync/cancel の高レベル API を実装。DB（OrderRepository, SQLite）との調停、クラッシュ耐性を考慮した二相的永続化（OrderSent 前後／broker_order_id 先コミット等）、OrderSentPendingError の扱い、DuplicateOrderError の導入、sync での部分約定更新ロジック、キャンセルの不許可状態チェックを実装。

### Changed
- なし（初回リリース）  

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- .env の読み込み順序は OS 環境 > .env.local > .env（.env.local は override=True）。OS 環境変数は protected として上書きされない。
- validate_config の YAML 検証は PyYAML 未インストール時にスキップし、警告を出力する。
- ExecutionEngine / run_* スクリプトは duckdb と sqlite を併用。Monitoring は常に本番 sqlite_path を利用する（paper_trading であっても）。
- kill.flag の自動クリア動作は KILL_FLAG_CLEAR_ON_START により制御（本番環境で 1 にすることは警告）。

今後の予定（例）
- async 対応のための httpx.AsyncClient 置換、WebSocket の非同期化
- BrokerClient のモック実装とテストカバレッジ拡充
- より詳細な監視メトリクスおよびアラートルールの追加

---
（この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴・リリースノートはコミットログやリリース管理に合わせて更新してください。）