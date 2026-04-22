# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-04-22

### 追加 (Added)
- パッケージの初期リリース。
- 設定管理
  - Settings クラスを導入。環境変数からアプリケーション設定を取得する一元インターフェースを提供（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン、ログレベル等）。
  - 環境自動ロード機能を追加（プロジェクトルートの .env / .env.local を自動読み込み）。OS 環境変数保護、.env の上書き挙動（.env と .env.local の優先度）、自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。
  - .env パース機能を強化：export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いを考慮。

- 環境設定ウィザード CLI
  - python -m kabusys.config_setup による対話式ウィザードを追加。一般的な環境項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、ログレベル、KILL_FLAG の振る舞い等）を対話で作成・更新し、.env を出力する機能。
  - 既存 .env 読み込みと既存値の再利用、シークレット欄のマスク表示、保存前の確認を実装。
  - .env 作成時に書き込まれるテンプレートヘッダに「.env は絶対に Git にコミットしないこと」を明記。

- 設定検証 CLI
  - python -m kabusys.validate_config で起動前に設定不備を検出するツールを追加。
  - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と PyYAML によるパース検証（PyYAML 未インストール時は検証をスキップして警告）を実装。
  - --strict オプションで警告も失敗（exit code 1）として扱うモードを追加。

- 実行スクリプト
  - run_execution.py を追加。ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用し、本番 DB と分離して実行。
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能。Monitoring は環境に関係なく本番 sqlite_path を使用する仕様。

- 実行エンジンと発注フロー
  - ExecutionEngine を実装。シグナル処理（指定時間帯にまとめて発注）と push drain（WebSocket による約定等のプッシュ処理）を備えるセッション実行ロジックを提供。
  - EngineConfig によるターゲット日や稼働時間の設定を追加。
  - セッション起動時に PID ファイルを書き出し、起動時の kill.flag の扱い（KILL_FLAG_CLEAR_ON_START による自動クリアオプション）を実装。
  - WebSocket(push) スレッドを起動して受信 payload を内部キューへ投入し、drain 時に sync / Gate 3 チェックを行う。

- 注文管理（Execution）
  - OrderRecord データモデルおよび状態遷移ロジックを導入（状態列挙 OrderState と遷移検証）。不正な状態遷移は InvalidStateTransitionError を送出。
  - OrderManager を導入：create_order / send_order / sync_order / cancel_order の API を提供。
    - create_order は signal_id の重複チェック（DB インデックス違反を DuplicateOrderError に変換）と UUID の client_order_id 発番を行う。
    - send_order はクラッシュ耐性を意識した 2 相的な永続化シーケンスを実装（OrderSent を先に commit → ブローカ呼び出し → broker_order_id を保存 → OrderAccepted に遷移等）。
    - send_order は OrderRejectedError（拒否）と OrderSentPendingError（注文番号はあるが約定せず保留）を扱う。OrderSentPendingError 発生時は broker_order_id を保存して例外を伝播。
    - sync_order は broker 側ステータス照合で内部状態を更新、部分約定の増分更新（filled_qty / avg_fill_price）や OrderSent→Filled などの間接遷移処理を行う。
    - cancel_order は終端状態のキャンセル不可チェックを行い、必要に応じて broker 側キャンセルを実行してローカルを Cancelled に遷移する。

- ブローカークライアント
  - KabuStationClient（kabu station REST API クライアント）を実装。
    - httpx 同期クライアントを使用。内部で API トークンを取得・キャッシュし、401 で自動再取得・1回リトライを行う。
    - JSON パース失敗やタイムアウト・ネットワークエラー、HTTP ステータスに応じた例外変換（RateLimitError / BrokerAPIError 等）を実装。
    - kabu ステータスコードから内部ステータス ("open"/"partial"/"filled"/"cancelled"/"rejected") へのマッピングを保持。

- リスク管理・Gate チェック
  - ExecutionEngine は複数の Gate を通じて発注を行う設計を実装（Gate1: signal レベル、Gate2: 実行レート・サーキットブレーカー、Gate3: ドローダウン監視）。Gate2 ではリトライやサーキットブレーカー発動時の挙動制御を行う。
  - リスク評価結果に応じて発注の継続/中止や kill_switch 発動を行う。

- 再突合（Reconciliation）
  - セッション開始時に Reconciler を走らせ、Order の同期や不整合検出を行うためのフックを提供（reconciler が設定されている場合のみ実行）。

- 監視・ロギング・プロセス管理
  - setup_logging, set_process_priority を呼び出してログとプロセス優先度を設定するようランナーを統合。
  - 監視 DB へのトレードイベント記録フックを ExecutionEngine 内の発注フローに追加（監視 DB が提供されている場合のみ）。

### 変更 (Changed)
- 初回公開のため該当なし。

### 修正 (Fixed)
- 初回公開のため該当なし。

### 削除 (Removed)
- 初回公開のため該当なし。

### 既知の注意点 / セキュリティ
- .env に機密情報（API トークンやパスワード）が含まれるため、.env をリポジトリに含めないよう強く推奨（config_setup のヘッダにも注意書きあり）。
- KABUSYS_ENV=live（本番）では慎重な設定確認が必須（validate_config にて警告を出力）。本番運用時の LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値などに注意。

（注）この CHANGELOG はソースコードからの推測に基づき作成されています。実際のリリースノートでは追加の背景情報や既知の不具合、マイグレーション手順などを追記してください。