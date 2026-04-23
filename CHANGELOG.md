# Changelog

すべての注目すべき変更はこのファイルに記録されます。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-23

### 追加 (Added)
- パッケージ初期リリース: バージョン情報を __version__ = "0.1.0" として導入。
- 設定検証 CLI を追加 (`kabusys.validate_config`)
  - .env と config/*.yaml の起動前検証を実行。
  - 必須 / 任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性判定、DB パス・親ディレクトリ確認、YAML パース検査（PyYAML がある場合）。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起）。
  - --strict オプション: 警告を FAIL として exit(1) を返す。
  - 検証結果を INFO/WARNING/ERROR で出力し、適切な終了コードを返す。
- 環境設定ウィザード CLI を追加 (`kabusys.config_setup`)
  - 対話式で .env を初期作成・更新するウィザード。
  - 各設定項目の説明・選択肢・デフォルトを表示。シークレット項目は表示マスク（保存時はマスク解除）。
  - .env の読み込み／既存値の再利用、保存確認、保存後の次手順案内を実装。
- 設定管理モジュールを追加 (`kabusys.config`)
  - .env 自動ロード機能（優先順位: OS 環境 > .env.local > .env）。プロジェクトルートは .git または pyproject.toml により検出。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーを強化:
    - export プレフィックス対応。
    - シングル/ダブルクォート内のエスケープ処理。
    - 非クォート値のインラインコメント処理（直前がスペース/タブの場合に '#' をコメントと認識）。
  - .env 読み込み時の上書き制御 (override, protected keys) を実装し、OS 環境変数を保護。
  - Settings クラスを導入。環境変数の取得、妥当性チェック（KABUSYS_ENV, LOG_LEVEL など）、パスの Path 化、PAPER_FILL_MODE の検証などを提供。
- 実行スクリプトを追加
  - Execution エントリポイント: `kabusys.run_execution`
    - プロセス優先度設定、PID ファイル管理、停止フラグ検出、paper_trading 用 DB を本番 DB と分離、監視 DB 初期化を実装。
  - Monitoring エントリポイント: `kabusys.run_monitoring`
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔制御（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用。
- 発注系コアを実装
  - OrderRecord（`kabusys.execution.order_record`）
    - 注文状態列挙 OrderState と許可遷移テーブルを実装。
    - 状態遷移検証と更新（updated_at 自動更新、オプションフィールド更新）を提供。違反時は InvalidStateTransitionError を送出。
  - OrderManager（`kabusys.execution.order_manager`）
    - create_order: signal_id の重複検査（DB 部分ユニーク違反を DuplicateOrderError に変換）。
    - send_order: 2相永続化（OrderSent 登録 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted へ遷移）を実装し、クラッシュ耐性を向上。
    - OrderSentPendingError の扱い（broker_order_id を保存して再送出し、Reconciliation 対象にする）。
    - sync_order: broker 側ステータスをローカル状態へ同期（部分約定の更新を含む）。
    - cancel_order: 終端状態判定とキャンセル処理（broker API 呼び出し）を実装。
  - ExecutionEngine（`kabusys.execution.execution_engine`）
    - Signal Queue Pull 型発注フローを実装（シグナル処理ウィンドウ、WebSocket push ドレイン、セッション管理）。
    - Gate 1/2/3 のリスクチェックフロー（シグナルレベル、実行レベル、ポートフォリオ指標）を統合。Gate 3 NG で kill_switch を発動。
    - size_multiplier 適用（BUY 時のみ、100 株単位丸め）、発注結果の position_entries 登録。
    - WebSocket スレッド（broker が stream_push を提供する場合）からの通知を _push_queue で受け取り同期処理を行う。
    - kill_switch: 全 active 注文のキャンセル、ループ停止。外部 stop() での停止をサポート。
    - PID ファイル書き出し／削除、起動時の kill.flag 処理（KILL_FLAG_CLEAR_ON_START による自動クリア動作）。
- ブローカークライアント実装
  - KabuStationClient（`kabusys.execution.kabu_client`）
    - httpx 同期クライアントを用いた kabuステーション REST API 実装。
    - トークン取得の遅延初期化と 401 の場合の自動再取得・リトライ処理。
    - HTTP エラーを BrokerAPIError / RateLimitError へ変換。
    - kabu station の状態コード → 内部ステータスマップを定義。
    - WebSocket / push 受信（ライブラリ依存）への下地を用意。
- 監視関連
  - 監視 DB 初期化ユーティリティ（monitoring_db の init）を呼び出す連携を追加。
  - 発注時の監視イベント記録（latency 等）を ExecutionEngine から監視 DB に記録（監視 DB が与えられた場合）。

### 修正 (Fixed)
- .env ファイル読み込みにおいて、読み込みエラー時に警告を出すようにし、プロセスを停止させない堅牢性を追加。
- validate_config における YAML 未インストール時の挙動を警告にし、パース検証をスキップするように変更。
- MONITOR_POLL_INTERVAL や PAPER_FILL_MODE 等の環境変数の不正値に対するフォールバック／検証を追加し、想定外入力に対する安全性を向上。

### その他 / ドキュメント (Other)
- config_setup にて .env を生成するテンプレートを定義し、Git に .env をコミットしない旨の注意を追加。
- 対話ウィザードでの中断 / キャンセル時の挙動を明確化（変更未保存で終了）。
- 機密情報（トークン/パスワード等）はウィザード表示時にマスクする実装を追加。

### 既知の制限 (Known issues)
- 一部の低レベルコンポーネント（例: broker 側 API のエッジケース処理、外部ネットワーク障害シナリオ）は今後の改良余地あり。
- config/*.yaml の構文チェックは PyYAML がインストールされていることが前提（未インストール時はスキップして警告）。

---

注: 本 CHANGELOG はソースコードの状態から推測して作成したもので、実際のコミット履歴が存在する場合はそれに合わせて差分を調整してください。