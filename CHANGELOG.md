# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-22

### 追加
- 初回公開: KabuSys 日本株自動売買システムの基本コンポーネントを実装。
- 環境設定・読み込み
  - Settings クラスによる環境変数ベースの設定取得を実装（src/kabusys/config.py）。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - .env の行パーサを実装（export プレフィックス対応、クォート文字列のバックスラッシュエスケープ、コメント処理など）。
  - Settings による各種プロパティ（J-Quants トークン、kabu API パスワード、DB パス、PID/kill flag パス、閾値、PAPER_FILL_MODE など）を実装。無効な値は ValueError を送出。
- 設定ウィザード CLI
  - 対話式ウィザードで .env を生成/更新するツールを追加（src/kabusys/config_setup.py）。
  - 秘匿項目はマスク表示、選択肢・デフォルト・説明表示、保存確認を実装。
  - .env 書き出しではテンプレートヘッダを付与し Git へのコミット禁止を注意喚起。
- 設定検証 CLI
  - .env と config/*.yaml の起動前検証ツールを追加（src/kabusys/validate_config.py）。
  - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と YAML パース検証（PyYAML 未導入時は警告スキップ）を実装。
  - --strict オプションで警告を失敗扱いにする機能を提供。
- 実行エントリポイント
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
    - プロセス優先度設定と PID/stop flag による起動制御。
  - 監視プロセス起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用。
- Execution コンポーネント
  - ExecutionEngine を実装（src/kabusys/execution/execution_engine.py）。
    - シグナル処理（8:50–9:10）と push ドレイン（9:10–15:30）を想定したセッション制御。
    - kill.flag による起動拒否 / 自動クリア（KILL_FLAG_CLEAR_ON_START）対応、PID ファイル書き込み。
    - シグナルの読み取り（DuckDB クエリ）、size_multiplier 適用、Gate 1/2（リスクチェック）を経て発注。
    - 発注後の position_entries 更新とモニタリング DB へのトレードイベント記録（可能な場合）を実装。
    - WebSocket push を受けて _push_queue に投入するワーカーを提供（broker が stream_push を持つ場合）。
    - kill_switch による全 active 注文キャンセル処理を提供。
- 注文関連ロジック
  - OrderRecord（状態遷移ロジック）を実装（src/kabusys/execution/order_record.py）。
    - 明示的な OrderState 列挙と許可遷移表、遷移時の更新処理、InvalidStateTransitionError を提供。
  - OrderManager（外向き API）を実装（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id 重複チェック（DB 部分ユニーク制約も解釈）と UUID 発番。
    - send_order: 「OrderCreated → OrderSent（永続化） → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 更新」という二相永続化を設計し、クラッシュ安全性（OrderSent / broker_order_id の残存）を考慮。
    - OrderSentPendingError の扱い（order_id を永続化して再スロー）や OrderRejectedError の処理を実装。
    - sync_order: broker 側ステータスと内部状態の同期（状態遷移の補正や部分約定のフィールド更新）を実装。
    - cancel_order: 終端状態のキャンセル禁止チェックおよび broker への cancel 呼び出しを実施。
  - OrderRepository（SQLite）との組合せで DB 永続化を行う設計（リポジトリ実体は別モジュールで想定）。
- ブローカークライアント（kabu station）
  - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
    - httpx による同期的 REST 呼び出し、Token 取得の遅延初期化・自動再取得（401 リトライ）を実装。
    - レスポンス JSON パース失敗、タイムアウト・ネットワークエラー、429（Rate Limit）の専用例外化（RateLimitError）を実装。
    - WebSocket push サポート（stream_push を持つ broker 向け）を予定（stream_push 実装は broker 側に依存）。
- 監視 / DB 初期化
  - init_monitoring_db を監視開始時に呼び出して監視テーブルの存在を保証（冪等）。
- ユーティリティ
  - ログ設定セットアップ・プロセス優先度設定ユーティリティを参照する仕組み（実装は別モジュール）。
- モード分離
  - paper_trading モードの分離（専用 SQLite、MockBroker の想定）と PAPER_FILL_MODE 設定の検証を追加。

### 変更
- （初回リリースにつき該当なし）

### 修正
- （初回リリースにつき該当なし）

### 破壊的変更
- （初回リリースにつき該当なし）

### セキュリティ
- 機密情報（API トークン / パスワード）は Settings では空文字列を返すか、config_setup と validate で明示的に取り扱い、.env を誤ってコミットしないよう README 等で注意喚起する構成にしています。

---

注:
- 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートとして公開する際は必要に応じて実装担当者による追記・修正を行ってください。