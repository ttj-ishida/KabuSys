CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、Semantic Versioning を採用します。

[Unreleased]
------------

なし

0.1.0 - 2026-04-22
------------------

Added
- 初回リリース。
- 環境・設定管理:
  - Settings クラスを導入し、環境変数から各種設定（J-Quants トークン、kabu API パスワード、DB パス、LINE トークン、ログレベルなど）を取得する API を提供。
  - Settings をグローバルに一つのインスタンス settings として公開。
  - env 値の簡易バリデーション（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE など）を導入し、不正値で例外を投げる。
  - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml で探索）。読み込み優先度: OS 環境 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーの強化: export プレフィックス対応、クォート・エスケープシーケンス対応、行内コメント処理などを実装。
  - .env 読み書き関係の保護（既存 OS 環境のキーを protected として上書き制御）。

- 設定ウィザード CLI:
  - config_setup.py を追加。対話式に .env を作成 / 更新するウィザードを提供。
  - J-Quants / kabu / DB / LINE / システム設定項目を網羅。シークレットはマスク表示、選択肢やデフォルト値の提示、保存確認を実装。
  - .env のテンプレート生成ロジック（_write_env）を実装。

- 設定検証 CLI:
  - validate_config.py を追加。起動前に .env と config/*.yaml の妥当性をチェックする CLI を提供。
  - 必須環境変数の未設定検出、プレースホルダ値検出（"_here", "your_value"）で警告。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
  - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在確認（存在しない場合は警告）。
  - config/*.yaml ファイルの存在確認および PyYAML があればパース検証（未インストール時はスキップし警告）。
  - KABUSYS_ENV=live のときの追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START=1 の警告）。
  - --strict オプションで警告を FAIL（exit(1)）として扱う機能。

- 実行スクリプト:
  - run_execution.py を追加。ExecutionEngine の起動スクリプトを提供。
    - process priority を高く設定（起動直後）。
    - paper_trading 環境では専用の paper_trading SQLite DB を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検出で優雅に停止。
    - PID ファイル管理（書き込み・削除）。
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用。

- Execution サブシステム（発注ロジック）:
  - OrderRecord: 注文状態を表す State Machine をデータクラスとして実装（OrderState enum）。遷移検証と InvalidStateTransitionError を導入。
  - OrderManager: DB（OrderRepository）と OrderRecord を組み合わせ、create/send/sync/cancel の一連の外向き API を実装。
    - create_order: signal_id の重複チェック、UUID による client_order_id 発番、DB の部分ユニーク制約違反を DuplicateOrderError に変換。
    - send_order: クラッシュ耐性を考慮した 2 段階の永続化戦略（OrderSent の事前コミット → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted へ遷移）を実装。OrderRejectedError / OrderSentPendingError の取り扱いを実装。
    - sync_order: broker 側のステータス照合による状態同期、部分約定進展の更新、OrderSent→Filled/Partial の場合は OrderAccepted を経由する補正ロジック。
    - cancel_order: 終端状態ではキャンセル不可とする検査、broker_order_id があれば API 呼び出しを行い Cancelled へ遷移。
  - ExecutionEngine:
    - Signal Queue Pull 型の発注エンジンを実装。シグナル読み込み、Gate 1/2（シグナルレベル・エグゼキューションレベル）チェック、発注、push ドレイン（Gate 3）を実装。
    - size_multiplier の適用ロジック（BUY のみ）、100 株単位切り捨て、qty=0 のスキップ。
    - Gate 2 のレート制限リトライ（最大 3 回）とサーキットブレーカ判定（開放時はシグナルループ停止）。
    - 発注結果に応じた position_entries への書き込み（fill_date = 翌営業日）とエラー耐性（失敗時は警告でフロー継続）。
    - 発注レイテンシ等の監視 DB への記録（MonitoringDB が渡された場合）。
    - push 通知処理: broker_order_id から client_order_id を見つけて sync_order を呼び出す。push に依らず Gate 3（ドローダウン）評価を実行し NG の場合は kill_switch を発動。
    - kill_switch: 全 active 注文をキャンセルし、ループを停止。外部停止として stop() をエイリアス実装。
    - WebSocket スレッドをサポート（broker に stream_push が無ければスキップ）。
    - run_session: 起動時の Reconciliation（任意）実行、kill.flag の取り扱い（KILL_FLAG_CLEAR_ON_START による自動クリアオプション）、PID ファイル管理、セッションタイミング（8:50 発注開始、9:10 発注締切、15:30 終了）。

- ブローカークライアント:
  - KabuStationClient を実装（httpx を使用した同期 REST クライアント）。
    - トークン取得の遅延初期化と自動再取得（401 を受けた場合に再トライ）。
    - レスポンス JSON パースを一元化してエラーを BrokerAPIError に変換。
    - HTTP ステータスに応じた RateLimitError / BrokerAPIError の扱い。
    - kabu station の状態コードマッピング (_KABU_STATUS_MAP) を実装。

- 監視・DB 初期化:
  - monitoring 用 DB 初期化ユーティリティ（init_monitoring_db）の利用を各起動スクリプトで行い、監視テーブルの存在を保証。

Changed
- N/A（初回リリースのため変更履歴なし）

Fixed
- N/A（初回リリース）

Security
- N/A

Notes / Internals
- 設計上の注意:
  - send_order の永続化シーケンスや OrderSentPendingError の取り扱いはクラッシュ後リコンシリエーションでの復旧を考慮した設計。
  - ExecutionEngine はテスト時に _process_signals() と _drain_push_queue() を直接呼び出して部分的に検証できる設計。
  - monitoring は環境に依存せず本番 sqlite_path を使用して監視データを一元化する（run_monitoring の挙動）。
- 今後の拡張案（参考）:
  - KabuStationClient の async 化（httpx.AsyncClient への切替）で並列処理の効率化。
  - config/*.yaml のスキーマ検証（PyYAML に加えて JSON Schema 等の採用）。
  - より詳細な監視・メトリクス収集の拡張。

貢献
- 初回機能実装に関わったすべての貢献者に感謝します。今後のバグ修正・機能追加はセマンティックバージョニングに従って本 CHANGELOG に追記してください。