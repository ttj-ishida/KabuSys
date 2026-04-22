CHANGELOG
=========

すべての注目すべき変更点を記載します。これは Keep a Changelog の形式に準拠しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-22
--------------------

Added
- 新規リリース: KabuSys 初期実装を追加。
- 環境設定・ロード
  - .env/.env.local 自動読み込み実装。プロジェクトルートは .git または pyproject.toml を起点に探索するため CWD に依存しない。
  - OS の既存環境変数を保護する読み込みロジックを実装（.env.local は上書き可能だが OS 環境は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパースを強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理を実装。
- 設定管理
  - Settings クラスを導入し、環境変数経由の設定をプロパティとして提供（例: jquants_refresh_token, kabu_api_password, duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, 各種しきい値など）。
  - env / log_level / PAPER_FILL_MODE などの値検証を追加。無効値は ValueError を送出。
- 対話型設定ウィザード
  - python -m kabusys.config_setup による .env 作成/更新ウィザードを追加。既存 .env の読み込み、入力ヒント、シークレットマスク、確認後の保存をサポート。
- 設定検証ツール
  - python -m kabusys.validate_config による起動前チェックツールを追加。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認・（PyYAML がある場合は）パース検証、KABUSYS_ENV=live の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
  - --strict オプション: 警告も FAIL 扱いにして exit(1)。
- 実行エントリスクリプト
  - python -m kabusys.run_execution: ExecutionEngine を起動するスクリプトを追加。paper_trading 用に本番 DB から分離した専用 SQLite を使用する挙動をサポート。
  - python -m kabusys.run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する。
- 発注エンジン / 実行フロー
  - ExecutionEngine を実装。シグナル処理 (8:50–9:10) と push ドレインループ (9:10–15:30) を備え、WebSocket push 受信と処理をサポート。
  - EngineConfig により target_date / 時刻境界を設定可能。
  - シグナル処理で size_multiplier、Gate1/2（シグナル・実行レベル検査）、Gate3（ドローダウン監視） を実装。Gate2 はレート制限のリトライとサーキットブレーカー挙動を持つ。
  - push 処理で broker からの OrderID を元に同期 (sync_order) を行い、ポートフォリオ評価 → Gate3 判定を実行。
  - kill_switch を実装し、全 active 注文のキャンセルとループ停止を行う。stop() は kill_switch の公開エイリアス。
  - PID ファイル書き出し、起動時の kill.flag チェックと KILL_FLAG_CLEAR_ON_START 挙動をサポート。
- 注文モデルと管理
  - OrderRecord（状態マシン）: 状態列挙 OrderState と、許可遷移テーブル、transition_to による遷移検証を実装。InvalidStateTransitionError を定義。
  - OrderManager: signal_id による重複防止、create/send/sync/cancel の外向き API を実装。
    - create_order は signal_id 部分ユニーク制約違反を DuplicateOrderError に変換。
    - send_order はクラッシュ耐性を考慮した二相的永続化フローを実装（OrderCreated→OrderSent を先に永続化、broker_order_id の保存→OrderAccepted など）。OrderSentPendingError を特別扱いし、pending 状態の処理を保持。
    - sync_order は broker 側の状態を照合して部分約定や状態遷移を同期。filled_qty / avg_fill_price の増分更新も考慮。
    - cancel_order はキャンセル不可能な状態をチェックし、broker API 呼び出しと DB 更新を行う。
- ブローカークライアント
  - KabuStationClient を実装（httpx 同期クライアント + websocket）。
  - トークン取得の遅延初期化、自動再取得、401 時の 1 回リトライ処理を実装。
  - HTTP レスポンスのエラーコードを BrokerAPIError / RateLimitError 等にマッピング（429 → RateLimitError、500 系は BrokerAPIError 等）。
  - kabu ステータスコード -> 内部状態マップを定義（open/partial/filled/cancelled/rejected）。
- モニタリング / データベース
  - monitoring_db 初期化関数の利用（init_monitoring_db）。
  - 発注イベントを監視 DB にログする仕組みを ExecutionEngine の発注フローに組み込み（監視 DB は存在しない場合でもフロー継続）。
- ユーティリティ
  - logging_setup, process_priority 等のユーティリティ統合を通して起動時ログの初期化とプロセス優先度設定を行う。

Changed
- なし（新規リリースのため「追加」が中心）。

Fixed
- .env パースのコメント/クォート処理を改善し、誤った値解釈やエスケープ処理に起因する問題を回避。

Security
- .env 生成時に "絶対に Git にコミットしない" 旨の注意書きを .env ヘッダに追加。

Deprecated
- なし

Removed
- なし

Notes / 補足
- YAML の内容検証は PyYAML がインストールされている場合のみ実行され、未インストール時は警告を出してスキップします。
- ExecutionEngine / OrderManager 周りはクラッシュ耐性・リコンシリエーションを考慮した設計になっており、OrderSent のまま残るケースや broker_order_id が先に永続化されるケースを想定しています（Reconciliation による復旧を前提）。
- paper_trading モードでは発注や DB が本番と分離される設計です（paper_sqlite_path を使用）。

開発者向けコマンド例
- 環境作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視起動: python -m kabusys.run_monitoring
- 実行起動: python -m kabusys.run_execution

---