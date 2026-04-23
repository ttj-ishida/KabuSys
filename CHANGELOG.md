# CHANGELOG

すべての注目すべき変更点を記録します。これは Keep a Changelog のガイドラインに準拠しています。  

（注: 以下は提供されたソースコードから推測して作成した初回リリース向けの変更履歴です。実際のコミット履歴やリリースノートと差異がある可能性があります。）

## [Unreleased]

## [0.1.0] - 2026-04-23

### Added
- 初期リリース。KabuSys 日本株自動売買システムの基本コンポーネントを追加。
- 環境/設定管理
  - Settings クラス（src/kabusys/config.py）で環境変数から設定を取得する統一インタフェースを提供。
  - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。読み込み順序は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - .env ファイルパーサ（export 形式対応、クォート内のエスケープ処理、インラインコメント処理等）を実装。
  - Settings は各種設定プロパティ（J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV、LOG_LEVEL、paper_trading 設定など）を提供。無効値は ValueError を発生させる検証を行う。
- 環境設定ウィザード CLI
  - python -m kabusys.config_setup により対話式ウィザードで .env を作成／更新する機能を追加。
  - シークレット項目は表示をマスク、選択肢・デフォルト値・説明つきで入力支援。保存前に確認表示。
- 設定検証 CLI
  - python -m kabusys.validate_config により起動前に .env と config/*.yaml を検証する CLI を追加。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パス親ディレクトリ存在確認、config/*.yaml の存在と PyYAML によるパース検証（PyYAML 未インストール時は警告）。
  - --strict オプションで警告を FAIL（exit(1)）として扱う機能を追加。
- 実行系エントリポイント
  - run_execution（python -m kabusys.run_execution）: ExecutionEngine を起動するスクリプトを追加。paper_trading モード時は専用の paper DB を使用する挙動を実装。
  - run_monitoring（python -m kabusys.run_monitoring）: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用。
- Execution/発注エンジン
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）を実装。シグナル処理（デイリーループ）、WebSocket push のドレイン、PID ファイル管理、kill.flag の扱い、再コンシリエーション起動等を含むセッション管理を行う。
  - EngineConfig により target_date, 発注・締切・マーケット終了時刻を設定可能。
  - シグナル処理における Gate1（シグナルレベル検査）、Gate2（エグゼキューションレベル検査、レート制限・サーキットブレーカ）、Gate3（ドローダウン監視→kill_switch）を実装。
  - kill_switch により全 active 注文をキャンセルしてループ停止する機能を実装。
  - WebSocket スレッドによる kabu push 受信と _push_queue への投入、push からの同期処理（sync_order）を実装。
  - 発注後の position_entries への記録処理（次営業日を fill_date として扱う）を実装（DuckDB への書き込み）。
  - 発注時に発生するレイテンシ計測と監視DBへのログ記録（MonitoringDB が提供されている場合）。
- 注文管理・状態機械
  - OrderRecord（src/kabusys/execution/order_record.py）: 注文状態（OrderCreated, OrderSent, OrderAccepted, PartialFill, Filled, Closed, Cancelled, Rejected）を列挙した状態遷移ロジックを実装。InvalidStateTransitionError を定義。
  - OrderManager（src/kabusys/execution/order_manager.py）: signal_id ベースの重複検出（DuplicateOrderError）、create/send/sync/cancel の外向き API を実装。
    - send_order ではクラッシュ安全性を考慮した永続化シーケンス（OrderSent を先に永続化 → ブローカー呼び出し → broker_order_id を保存 → OrderAccepted に遷移 など）を実装。
    - OrderSentPendingError（ブローカーが注文番号だけ返すが約定しないケース）を扱う挙動を実装。
    - sync_order により broker 側ステータスを DB と同期し、部分約定の進行に応じた更新も行う。
    - cancel_order はキャンセル不可能な状態を判定して適切にエラーを返却。
- ブローカー API 抽象化
  - BrokerAPIProtocol（参照されるがソース一部）に基づく設計。BrokerClientFactory によるクライアント生成を想定。
  - KabuStationClient（src/kabusys/execution/kabu_client.py）:
    - kabu station REST API クライアント実装（同期 httpx.Client を使用）。
    - トークン取得の遅延初期化と 401 時の自動再取得（1回リトライ）を実装。
    - ステータスコード 429 を RateLimitError、5xx を BrokerAPIError に変換する取り扱い。
    - kabu 注文状態コード → 内部ステータスへのマッピングを実装。
    - websocket による push 受信（stream_push）をサポートする想定。
- データベース / モニタリング
  - duckdb を分析用に使用、sqlite（monitoring DB）を監視・注文履歴用に使用。
  - init_monitoring_db による監視用テーブルの初期化フロー（冪等）。
- ユーティリティ
  - process priority 設定ユーティリティを用いて起動時にプロセス優先度を "high" に設定する呼び出しを追加（run_execution/run_monitoring）。
  - logging 設定ユーティリティ（setup_logging）を利用する起動シーケンスを導入。
- パッケージ情報
  - パッケージルートに __version__ = "0.1.0" を追加。

### Changed
- N/A（初回リリースのため変更履歴はなし）

### Fixed
- N/A（初回リリースのため修正履歴はなし）

### Deprecated
- N/A

### Removed
- N/A

### Security
- N/A

### Notes / 動作上の注意
- validate_config は PyYAML が未インストールだと YAML 内容検証をスキップして警告する設計。config/*.yaml の構文チェックを行うには PyYAML をインストールしてください。
- KabuStationClient は httpx と websocket（websocket-client 等）の依存を想定しています。実行環境に必要な依存をインストールしてください。
- データベースファイルのデフォルトパスは data/ 以下。親ディレクトリが存在しない場合は警告を出しますが、起動時に自動作成されるケースがあります。
- .env の扱い:
  - 読み込み順序は OS 環境 > .env.local > .env（.env.local は .env の上書き）。
  - .env 読み込み時、OS 環境変数は保護（上書きされない）。.env.local は override=True（ただし OS からのキーは保護）で読み込まれます。
  - .env 解析は export 形式、クォート内エスケープ、インラインコメントなどを考慮した実装です。
- ExecutionEngine のセッション制御:
  - 起動時に kill.flag が存在すると、KILL_FLAG_CLEAR_ON_START=1 の場合は自動でクリアして起動、そうでない場合は起動を拒否して SystemExit(1) になります。
  - PID ファイルの作成・削除を行います。PID ファイルのパスは設定で上書き可能。
- paper_trading モードでは broker に MockBrokerClient を使用し、paper_trading 用 SQLite DB（PAPER_TRADING_SQLITE_PATH）へ記録して本番データと分離する設計になっています。
- OrderManager・OrderRecord の状態遷移は厳密に定義されています。不正な遷移は InvalidStateTransitionError を発生させます。
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で調整可能。不正値（0 以下や非整数）を指定した場合はデフォルト（60 秒）にフォールバックします。
- validate_config の --strict を利用すると警告も失敗扱い（exit code 1）になるため CI などで厳格にチェックできます。

---

もしさらにリリースノートを分割したい（例: Unreleased に次バージョンの作業内容を記録する、あるいは各コミットに基づく詳細を追加する）場合は、ソース管理のコミットログや実際の変更履歴を提供してください。