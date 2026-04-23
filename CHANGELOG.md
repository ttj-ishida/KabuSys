Keep a Changelog
=================

すべての重要な変更点はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。

履歴
----

### Unreleased
- （なし）

### 0.1.0 - 2026-04-23
初回公開リリース。日本株自動売買システム KabuSys のコア機能を実装しました。

主な追加点
- 基本 CLI / 起動スクリプト
  - python -m kabusys.run_execution: ExecutionEngine を起動する実行スクリプトを追加。
    - PID ファイル管理、停止フラグ検査、paper_trading 環境時の DB 分離をサポート。
    - プロセス優先度設定、ロギング初期化を実施。
  - python -m kabusys.run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
  - python -m kabusys.config_setup: 対話式 .env ウィザードを追加（初期作成 / 更新を支援）。
  - python -m kabusys.validate_config: 起動前の設定検証ツールを追加（.env および config/*.yaml の検査）。--strict オプションで警告も失敗扱いにできる。

- 環境変数 / 設定管理
  - config モジュール:
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env 自動読み込みを実装（OS 環境 > .env.local > .env の優先順）。
    - .env のパースは export 形式、シングル/ダブルクォート、エスケープ、行末コメントなど多様なケースに対応。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト用）。
    - Settings クラスを提供し、環境変数から型付きでアクセス可能（パスは Path に変換、bool/float の変換など）。
    - PAPER_FILL_MODE の値検証（"instant"|"partial"|"never"|"reject"）を実装。

- 実行エンジン / 発注フロー
  - ExecutionEngine:
    - シグナル取得（DuckDB）、Gate ベースのリスク検査（Gate1: シグナル、Gate2: エグゼキューション、Gate3: ドローダウン）および発注フローを実装。
    - size_multiplier の適用（BUY のみ）、qty の丸め（100 株単位）などシグナル調整処理。
    - WebSocket push のドレイン処理（kabu push を受けて sync_order 実行）。
    - kill_switch 実装: 全 active 注文のキャンセルとループ停止を行う。
    - PID ファイル書き出し・削除、kill.flag の起動時挙動（KILL_FLAG_CLEAR_ON_START により自動クリア可）を実装。
    - 発注遅延 (latency_ms) の監視 DB への記録をサポート（監視 DB 接続が与えられた場合）。

  - Order 管理
    - order_record: OrderState（状態列挙）と OrderRecord データクラスを実装。状態遷移ロジックを内包し、不正遷移は InvalidStateTransitionError を送出。
    - order_manager:
      - create_order: client_order_id を UUID4 で採番し、同一 signal_id の重複発注を検出して DuplicateOrderError を送出。
      - send_order: 「OrderCreated → OrderSent を先に永続化」する 2 相永続化パターンを採用し、broker_order_id を先に保存することでリコンシリエーションに耐性を持たせた設計。
        - OrderRejectedError, OrderSentPendingError の扱いを明確化（pending 時は broker_order_id を保存して OrderSent のまま残す）。
      - sync_order: broker API の状態を照合して状態遷移・部分約定更新を行う。状態マッピングにより open/partial/filled/cancelled/rejected を内部状態に変換。
      - cancel_order: cancel 不可の状態（Closed, Cancelled, Rejected, Filled）判定と API 呼び出しを経たキャンセル処理を実装。

  - Reconciliation / 可用性設計
    - send_order の永続化順序や OrderSentPendingError の扱いにより、クラッシュ・再起動後でも Reconciler が状態回復できるよう配慮。

- Broker クライアント
  - KabuStationClient（kabu station REST API）を実装（同期 httpx ベース）。
    - トークン取得の遅延初期化と 401 時のトークン再取得 + リトライを行う。
    - 429 を RateLimitError にマッピング、500 系を BrokerAPIError として扱う。
    - push 用に websocket ベースの stream_push を想定（存在する場合に WebSocket ワーカーを起動）。

- 監視関連
  - monitoring_db 初期化関数（init_monitoring_db）の呼び出し箇所を追加し、監視用 SQLite のスキーマ準備を担保。
  - run_monitoring 側では sqlite3/duckdb 接続の管理と例外ハンドリングを実装。

- ユーティリティ / ヘルパ
  - validate_config:
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パス親ディレクトリの存在チェック、config/*.yaml の存在と PyYAML によるパース検証（PyYAML 未インストール時は警告）。
    - --strict を使うと警告も失敗扱い（exit code 1）にできる。
  - .env ウィザード（config_setup）:
    - 項目定義、既存 .env 読み込み、対話入力、ファイル書き出しを実装。機密項目はマスク表示。

品質改善・重要な実装上の注意点
- .env 読み込み時に OS 環境変数を保護（protected）し、.env.local は .env を上書きする設計。
- .env パーサはクォートとエスケープ処理、行末コメントの取り扱いを細かく実装している。
- MONITOR_POLL_INTERVAL が不正（0 以下や非整数）の場合、デフォルトにフォールバックする安全設計。
- monitor/run_execution/run_monitoring 等で接続・ファイルのクローズを finally で保証。

既知の制約 / 将来の改善候補
- KabuStationClient は同期実装（httpx.Client）であり、将来的に async 化する場合は httpx.AsyncClient への置換が想定される。
- config/*.yaml の内容検証は PyYAML に依存。未インストール時は検証をスキップする（警告を出力）。
- 一部ファイル（kabu_client の末尾など）はこの差分で切り出しのため途中までの表示になっているが、主要なエラーハンドリングとトークン管理は実装済み。

開発者向けメモ
- パッケージバージョンは __version__ = "0.1.0" に設定済み。
- 自動テストや CI での利用時は KABUSYS_DISABLE_AUTO_ENV_LOAD をセットして .env 自動ロードを無効化することを推奨。
- 本番環境では KABUSYS_ENV=live 時に LINE の通知設定や KILL_FLAG_CLEAR_ON_START の値に注意すること（validate_config で警告が出る）。

-----