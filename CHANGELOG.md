# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の慣習に従っています。  

## [0.1.0] - 初期リリース

### 追加
- パッケージの初期バージョンを追加（__version__ = 0.1.0）。
- CLI / ユーティリティ
  - `kabusys.config_setup`：対話式の .env 作成/更新ウィザードを追加。
    - 項目定義（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DUCKDB_PATH / SQLITE_PATH / LINE_* / LOG_LEVEL / KILL_FLAG_CLEAR_ON_START 等）。
    - 既存 .env の読み込みと Enter による既存値再利用。
    - シークレット項目は表示をマスクして扱う。
    - 保存前の確認ダイアログと .env ファイル出力。
  - `kabusys.validate_config`：起動前設定検証 CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DUCKDB/SQLite パスの親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。
    - `--strict` オプション（警告を FAIL 扱いにして exit(1)）。
- 実行スクリプト
  - `kabusys.run_execution`：ExecutionEngine 起動スクリプトを追加。
    - paper_trading 環境時に paper_trading 用 SQLite を使用して本番 DB と分離。
    - 停止フラグ検出による起動抑止 / 実行中の停止処理。
    - プロセス優先度設定、PID ファイル出力。
  - `kabusys.run_monitoring`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用。
- 環境設定管理
  - `kabusys.config`：.env 読み込みと Settings クラスを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）。
    - .env / .env.local の自動読み込み（OS 環境変数を保護）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
    - .env の堅牢なパース実装（export プレフィックス、クォート値、バックスラッシュエスケープ、インラインコメント扱いの正確化）。
    - protected（OS 環境）キーを破壊しない上書き挙動。
    - Settings クラスに各種プロパティを提供（トークン・パス・閾値・フラグ等）と入力値バリデーション（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。
- Execution エンジン周辺
  - `kabusys.execution.execution_engine`：Signal Queue Pull 型の ExecutionEngine を追加。
    - シグナル処理時間帯（8:50-9:10）と push ドレイン（9:10-15:30）を実装。
    - Gate 1/2/3 によるリスクチェック（シグナルレベル / 実行レート制御 / ドローダウン監視）。
    - kill_switch による全 active 注文キャンセルとループ停止。
    - WebSocket push の非同期受信（push_queue）と処理。
    - PID ファイル管理、起動時のリコンシリエーション呼び出し、kill.flag の挙動（KILL_FLAG_CLEAR_ON_START を考慮）。
    - position_entries への書き込み（約定日計算は next_trading_day を使用）。
    - 監視 DB への発注イベント記録サポート（MonitoringDB が渡された場合）。
- 注文管理
  - `kabusys.execution.order_record`：OrderRecord（状態機械）を追加。
    - 明示的な OrderState 列挙と許可される状態遷移マップ。
    - transition_to による遷移検証。InvalidStateTransitionError を導入。
    - レコードは DB に触れない純粋ビジネスロジック。
  - `kabusys.execution.order_manager`：上位 API を追加。
    - create_order（signal_id 重複チェック、UUID client_order_id 付与）。
    - send_order：クラッシュ耐性を考慮した実装（OrderSent を事前永続化、broker_order_id を先に保存、OrderAccepted への遷移等。OrderSentPendingError の伝播）。
    - sync_order：broker 側のステータス照合で差分同期（部分約定の更新、OrderSent→Filled の間に OrderAccepted を経由する補正）。
    - cancel_order：キャンセル可否チェックと broker cancel 呼び出し、状態遷移。
    - DuplicateOrderError の導入。SQLite の一意制約違反を適切に DuplicateError に変換。
- ブローカークライアント
  - `kabusys.execution.kabu_client`：kabu station REST API クライアント（同期 httpx ベース）を追加。
    - トークン取得の遅延初期化・自動再取得（_get_token）。
    - 認証付きリクエストで 401 発生時にトークン再取得してリトライ。
    - レスポンス JSON パース失敗を明確に BrokerAPIError に変換。
    - 429 を RateLimitError に変換、タイムアウト／ネットワーク例外を BrokerAPIError に変換。
    - kabu station 注文状態コード → 内部状態マッピングを定義。
    - WebSocket（websocket 依存）で push を受け取る仕組みを想定（stream_push を持つ実装に依存）。
- 監視関連
  - `kabusys.monitoring`（参照）を使った監視 DB 初期化（init_monitoring_db）や SystemMonitor ロジック呼び出しを各スクリプトで利用。

### 変更（設計上の決定）
- DB / ロギング / プロセス優先度関連の初期化順序を明確化（プロセス優先度の先行設定、PID 書き込み前の kill.flag チェック等）。
- 監視（run_monitoring）は環境に依存せず常に本番 sqlite_path を使用する設計に決定。
- Execution の paper_trading モードは DB を完全に分離（paper_trading 用 SQLite）する設計。

### 修正（堅牢性・エラー処理）
- .env 読み込み処理でファイル読取失敗時に警告を出して継続するよう改善（warnings.warn）。
- YAML の検証は PyYAML がなければスキップし、適切に警告を出すようにした。
- MONITOR_POLL_INTERVAL の不正値に対してデフォルトにフォールバックし、ログで警告するようにした。
- send_order の 2相的永続化によりクラッシュ時の復旧可能性を改善（broker_order_id を先にコミットして Reconciliation を可能にする）。

### 既知の注意点 / 推奨
- .env は絶対にリポジトリにコミットしないこと（config_setup のヘッダに注意喚起あり）。
- KABUSYS_ENV=live の場合は本番運用となるため、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の設定を慎重に確認するよう警告を出す設計（validate_config / Settings の挙動）。
- Settings の一部プロパティ（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）は不正値で ValueError を送出するため、起動前に validate_config で検証することを推奨。

---

（必要に応じて将来の変更は Unreleased セクションに記載してください。）