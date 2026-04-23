# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。

## [0.1.0] - 2026-04-23

初回リリース。KabuSys のコア設定管理、実行／監視ランナー、発注エンジン周りの主要コンポーネントを追加。

### 追加
- パッケージ基礎
  - パッケージ初期化とバージョン定義を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - 公開モジュール群の宣言: data, strategy, execution, monitoring。

- 設定管理
  - 環境変数・設定管理モジュールを実装（src/kabusys/config.py）。
    - .env ファイルおよび環境変数から設定を自動読み込み（.env → .env.local、OS 環境変数優先）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能。
    - .env パース機能を強化（export プレフィックス対応、シングル/ダブルクォート中のエスケープ、インラインコメント処理）。
    - _require() による必須環境変数チェックを提供。
    - Settings クラスで各種設定プロパティを提供（J-Quants トークン、kabu API パスワード、データベースパス、ログレベル、PID/Kill フラグパス等）。
    - PAPER_FILL_MODE の検査や env/log_level のバリデーションを実装。

- 設定ウィザード CLI
  - 対話式 .env 生成・更新ツールを追加（src/kabusys/config_setup.py）。
    - 主要設定項目の対話入力（実行環境、J-Quants トークン、kabu パスワード、DB パス、LINE 設定、ログレベル、Kill Flag 設定など）。
    - 既存 .env 読み込み・Enter による既存値再利用、シークレット値のマスク表示。
    - 最終確認後に .env を生成・保存する機能（保存フォーマットに注意喚起コメントを含む）。
    - --env-file オプションで書き出し先パスを指定可能。
    - 使用方法のヘルプメッセージを提供。

- 設定検証 CLI
  - 起動前に .env および config/*.yaml を検証する CLI を追加（src/kabusys/validate_config.py）。
    - 必須／任意環境変数リストによるチェック、プレースホルダ検出、LOG_LEVEL/KABUSYS_ENV の妥当性検査を実装。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック（起動時自動作成の注意表示）。
    - config ディレクトリ下の YAML ファイル存在確認および PyYAML が利用可能な場合はパース検証（PyYAML 未インストール時はスキップして警告）。
    - KABUSYS_ENV=live 時の本番向け追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定など）。
    - --strict オプションを追加（警告も失敗扱いにする）。
    - 実行例をヘルプに記載。

- 実行／監視ランナー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を設定、PID ファイル管理、stop フラグ検知による安全停止、データベース接続（paper_trading 環境では専用 SQLite を使用）を実装。
  - Monitoring ポーリングスクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する挙動を明記。
    - stop フラグ検知でループ終了、例外時のログ出力とリカバリを実装。

- Execution (発注エンジン)
  - ExecutionEngine のコア実装を追加（src/kabusys/execution/execution_engine.py）。
    - セッション（シグナル処理、WebSocket push ドレイン）スケジュール管理（8:50 発注開始、9:10 発注締切、15:30 セッション終了）。
    - 起動時にリコンシリエーション実行（Reconciler が提供される場合）。
    - kill.flag の挙動（存在時の起動拒否 / KILL_FLAG_CLEAR_ON_START による自動クリア）と PID ファイル管理。
    - シグナル読み取り（DuckDB から）、size_multiplier 適用、qty の 100 単位丸め（BUY）、Gate 1/2（信号・実行レベル）による検査、発注実行、position_entries への記録、発注遅延計測と監視DBへのログ記録（監視 DB が設定されている場合）。
    - WebSocket スレッドによる push 受信（broker に stream_push があれば利用）と _push_queue を経由した同期処理。
    - Gate 3（ドローダウン等のメトリクス）検査による kill_switch 発動。
    - kill_switch による全 active 注文キャンセル処理とエラー/例外ハンドリング。

  - OrderRecord（状態遷移モデル）を実装（src/kabusys/execution/order_record.py）。
    - 注文状態列挙 OrderState と許可遷移テーブルを定義。
    - OrderRecord dataclass と transition_to() による遷移検証（不正遷移で InvalidStateTransitionError を送出）。
    - created_at / updated_at の自動更新、オプションフィールド（broker_order_id, filled_qty, avg_fill_price, error_message）の取り扱い。

  - OrderManager（外向け API）を実装（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id の重複検査（DB 上の部分ユニーク制約違反は DuplicateOrderError に変換）、uuid4 による client_order_id 発番。
    - send_order: クラッシュ安全性を考慮した二相的永続化フローを実装（OrderSent を DB に残してから broker 呼び出し、broker_order_id の先行コミット、OrderAccepted への遷移等）。OrderRejectedError/OrderSentPendingError の扱いを明確化。
    - sync_order: broker のステータスを照合して状態を同期。部分約定進行時に filled_qty/avg_fill_price の差分更新を行う挙動。
    - cancel_order: キャンセル不可状態の判定と broker API 呼び出し、状態遷移。
    - DuplicateOrderError / InvalidStateTransitionError による明示的なエラー種別。

  - 実行コンポーネントの連携を想定したエントリポイント（run_execution）を実装。
    - Broker クライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動と停止管理。

- ブローカークライアント（kabu station）
  - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
    - httpx を使った同期 REST クライアント。
    - トークン取得の遅延初期化と自動再取得（401 レスポンスで再取得してリトライ）。
    - レスポンス JSON パース失敗、ネットワークエラー、タイムアウト、HTTP ステータス（401/429/5xx）に対する明確な例外変換（BrokerAPIError, RateLimitError 等）。
    - WebSocket push を想定した stream_push 連携（別実装の broker が提供する場合に ExecutionEngine から利用）。
    - kabu ステータスコード → 内部状態マッピングを定義。

- 監視 DB 初期化ユーティリティ
  - Monitoring DB 初期化関数（init_monitoring_db）が存在する箇所への参照を追加（run_monitoring / run_execution で使用）。

- ユーティリティ呼び出し
  - プロセス優先度設定ユーティリティ（set_process_priority）、ロギングセットアップ（setup_logging）を各ランナーで呼び出す実装を追加（run_monitoring / run_execution）。

### 変更
- （新規リリースのため該当なし）

### 修正
- （新規リリースのため該当なし）

### 削除
- （新規リリースのため該当なし）

### 既知の注意点 / 設計上の留意点
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダに警告を出力）。
- validate_config の YAML 検証は PyYAML がインストールされている場合のみ実行されます。PyYAML がない環境では警告を出しますが検証自体はスキップされます。
- Monitoring は常に本番 sqlite_path を使用するため、paper_trading での監視は本番 DB と分離されていません（設計上の意図を明記）。
- ExecutionEngine の時間依存ロジック（8:50/9:10/15:30）や kill.flag の自動クリアは運用方針に合わせて注意して設定してください。

---

今後の予定・改善案（例）
- broker API / websocket の非同期実装（httpx.AsyncClient）への対応。
- より細かな監視メトリクスの拡充と監視用 UI 連携。
- OrderRepository や RiskManager のユニットテスト強化とモック実装例の提供。