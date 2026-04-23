# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に従います。  
安定版のリリースや後続の変更時にこのファイルを更新してください。

## [Unreleased]

## [0.1.0] - 2026-04-23
初回リリース: KabuSys の基本機能（設定管理、監視・実行ランナー、発注エンジン、ブローカークライアント、注文状態管理など）を実装。

### Added
- 環境設定・読み込み
  - Settings クラスを実装し、環境変数から各種設定（J-Quants / kabu API / DB パス / LINE / ログレベル / Kill Switch 等）を取得可能に。
  - 自動 .env ロード機構を追加（プロジェクトルートを .git または pyproject.toml で検出し、.env → .env.local の順でロード）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env パーサーの強化: export 構文対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理などを実装。

- 環境設定ウィザード
  - python -m kabusys.config_setup による対話式ウィザードを追加。.env の初期作成・更新を支援する（項目定義、既存値の再利用、シークレット値のマスク表示、保存確認）。
  - .env 書き出しテンプレート（説明コメント含む）を実装。作成後に validate_config 実行の案内を表示。

- 設定検証 CLI
  - python -m kabusys.validate_config を追加し、起動前に環境変数や config/*.yaml の基本チェックが可能に。
  - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、PyYAML があれば YAML のパース検証を実行。
  - --strict オプションで警告も FAIL 扱いにできる。

- 実行系ランナー
  - ExecutionEngine 実装（シグナル取得→Gate 検査→発注→WebSocket push ドレイン）。セッション制御（発注開始/締切/終了時刻）をサポート。
  - run_execution スクリプト（python -m kabusys.run_execution）を追加。プロセス優先度設定、PID 書き出し、stop フラグ / kill.flag を用いた安全停止を実装。
  - run_monitoring スクリプト（python -m kabusys.run_monitoring）を追加。MONITOR_POLL_INTERVAL によるポーリング間隔調整と監視 DB 初期化を実装。
  - paper_trading 環境用に DB を分離（paper_trading 時は data/paper_trading.db を使用）。

- 注文管理と状態遷移
  - OrderRecord: 注文状態を表す状態機械（OrderState）と遷移ロジックを実装。不正遷移時は InvalidStateTransitionError を送出。
  - OrderManager: create/send/sync/cancel の外向き API を実装。
    - create_order で signal_id の重複検知（DB 側の部分ユニーク制約違反を DuplicateOrderError に変換）。
    - send_order は「OrderSent を永続化 → ブローカ呼び出し → broker_order_id 永続化（state は Sent のまま）→ OrderAccepted へ遷移」の 2 相永続化を行い、クラッシュ復旧に配慮（Reconciliation を想定）。
    - OrderSentPendingError の扱いを明確化（ブローカーが注文番号を返すが約定しないケース）。OrderRejectedError のハンドリング。
    - sync_order: broker 側ステータスを照合して状態を同期。部分約定の進行は差分更新で対応。
    - cancel_order: キャンセル不可能な状態（Closed/Cancelled/Rejected/Filled）は拒否し、broker_order_id がある場合はブローカー API を呼びキャンセル処理を行う。

- ブローカークライアント（kabu station）
  - KabuStationClient を実装（httpx 同期クライアント使用）。
  - トークン取得の遅延初期化と自動再取得（401 に対して再取得して 1 回リトライ）。
  - HTTP エラー・タイムアウト・ネットワークエラーを BrokerAPIError / RateLimitError 等に変換して扱う。
  - REST と WebSocket（push）を組み合わせた処理（stream_push がある場合は WebSocket スレッドを起動）。

- リスク管理・リコンシリエーション・監視連携（フック）
  - ExecutionEngine は RiskManager（Gate 1/2/3）、Reconciler、MonitoringDB を組み合わせて動作する設計。
  - 発注時の API レイテンシ計測や監視 DB へのトレードイベント記録フックを追加（監視 DB 書き込み失敗は発注フローを止めない）。

- DB / 分析
  - DuckDB を分析用に利用。ExecutionEngine は DuckDB 接続を受け取り、position_entries の書き込みやシグナル読み込みに利用。
  - 監視系は SQLite（monitoring.db）を使用。monitoring は設定に関わらず本番 sqlite_path を使用する点に注意。

- ユーティリティ
  - PID / stop flag / kill flag によるプロセス制御、KILL_FLAG_CLEAR_ON_START による起動時の kill.flag 自動クリア設定。
  - プロセス優先度設定（set_process_priority）とロギング初期化（setup_logging）をランナーで利用。

### Changed
- 初期リリースのため該当なし（今後のリリースで差分管理）。

### Fixed
- 初期リリースのため該当なし。

### Security
- .env ファイルを Git にコミットしない旨の注記をウィザードで出力。
- API トークン取り扱いは内部で管理し、HTTP レスポンスの検証およびエラー分類を行うことで誤動作時の情報露出を抑制。

### Notes / Implementation details
- Order 管理はデータベースへの永続化とブローカ呼び出しの間のクラッシュ耐性を考慮して設計されています（2 相永続化や sync/reconcile の想定）。
- .env の自動ロードはプロジェクトルートの検出に依存するため、配布後に動作させる場合は .git もしくは pyproject.toml が存在するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境を設定してください。
- config/*.yaml の検証は PyYAML がインストールされている場合に実行され、未インストール時は警告でスキップされます。
- ExecutionEngine の一部機能（RiskManager / Reconciler / BrokerClientFactory / MonitoringDB 等）は他モジュールに分割されており、本リリースではそれらを組み合わせるインターフェースを中心に実装しています。

---

今後のリリースでは以下を検討しています:
- より詳細な監視指標・アラート機構の強化
- 非同期（async）クライアントやバックグラウンドジョブの改良
- 単体テストと E2E テストの充実化
- config/*.yaml のスキーマ検証（JSON Schema 等）の導入

（以上）