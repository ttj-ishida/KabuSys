# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-22

Added
- 基本リリース: KabuSys 日本株自動売買システムの初期実装を追加。
- 環境検証 CLI:
  - `kabusys.validate_config` モジュールを追加。`.env` と `config/*.yaml` の起動前検証を行う CLI を提供。
  - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスや config YAML の存在・パース検証を実装。
  - `--strict` オプションで警告を FAIL 扱いにできる。
- 環境設定ウィザード:
  - `kabusys.config_setup` に対話式ウィザードを追加。`.env` の初期作成・更新を支援。
  - シークレット値は表示マスク、選択肢/デフォルト値の提示、保存時確認を実装。
  - `.env` の書き出しテンプレート（コメント付き）を提供。
- 設定管理:
  - `kabusys.config` に Settings クラスを追加し、環境変数から型付き設定値を取得する API を提供（例: `settings.env`, `settings.duckdb_path`）。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml 基準）。読み込み順序: OS 環境 > .env.local > .env。OS 環境変数は保護され、`.env.local` は上書き可能。
  - `.env` パーサーを強化:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしでのインラインコメント処理（空白直前の '#' をコメントとみなす）
  - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - 必須環境変数取得時に未設定なら ValueError を投げる `_require()` を追加。
  - `PAPER_FILL_MODE` のバリデーション（"instant"|"partial"|"never"|"reject"）を実装。
- 実行エントリポイント:
  - `run_execution.py` を追加。ExecutionEngine の起動スクリプト。paper_trading 環境では専用 SQLite（paper_trading.db）を使用して本番 DB と分離。
  - `run_monitoring.py` を追加。SystemMonitor のポーリングループ起動スクリプト。環境にかかわらず本番 sqlite_path を使用。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
- Execution エンジン・発注フロー:
  - `execution/execution_engine.py` を追加。セッション制御、シグナル処理ループ（8:50-9:10）、push ドレイン（9:10-15:30）、WebSocket スレッドなどを実装。
  - ExecutionEngine に kill switch、PID ファイル書き込み、kill_flag の起動時クリア判定（設定に依存）を実装。
  - DuckDB を使用してシグナルの読み出しと position_entries への記録を行う処理を含む。
  - WebSocket 経由の push 受信を _push_queue 経由で処理し、受信時に order の同期・Gate 3 チェックを実行。
- 注文管理・状態機械:
  - `execution/order_record.py` に OrderRecord と OrderState（状態遷移ルール）を実装。不正遷移時に `InvalidStateTransitionError` を送出。
  - `_ALLOWED_TRANSITIONS` を定義し、状態遷移の整合性を強制。
  - `execution/order_manager.py` を追加。OrderRecord（純粋ロジック）と OrderRepository（SQLite）を組み合わせ、発注の作成(create)、送信(send)、同期(sync)、キャンセル(cancel) を実装。
  - 重複発注防止（signal_id ベース）として `DuplicateOrderError` を導入。
  - send_order 実装はクラッシュ耐性を考慮した 2 相永続化設計:
    - Step1: OrderCreated → OrderSent を DB にコミット（broker 呼び出し前）。
    - Step2: broker.send_order 呼び出し。
    - Step3a: broker_order_id を DB に先に保存（state は Sent のまま）。
    - Step3b: OrderAccepted へ遷移してコミット。エラー時は Rejected に遷移。
  - `OrderSentPendingError`（ブローカーから注文番号は発行されたが約定しないケース）を扱い、broker_order_id を保存したまま OrderSent のまま残す処理を実装。
  - sync_order は broker.get_order_status の結果に基づき状態を同期。broker が None を返す場合はスキップ。
  - cancel_order は終端状態に対してはキャンセル不可として例外を投げ、ブローカー API の cancel を呼んでから Cancelled に遷移。
- ブローカー実装（kabuステーション）:
  - `execution/kabu_client.py` を追加。httpx 同期クライアントで kabuステーション REST API を実装。
  - トークン管理を内部で行い、401 時にトークン再取得して 1 回リトライ。
  - レスポンス JSON パース失敗やネットワーク/タイムアウトを独自例外に変換して扱う。
  - HTTP ステータス 429 を RateLimitError に、5xx を BrokerAPIError にマッピングする基礎ロジックを実装。
  - kabu 注文状態コードを内部ステータス（"open"/"partial"/"filled"/"cancelled"/"rejected"）へマッピング。
  - WebSocket/stream_push の存在チェックに基づく push スレッド起動ロジックを ExecutionEngine に接続。
- モニタリング:
  - `monitoring` 初期化ロジック（monitoring_db.init_monitoring_db の呼び出し）を run_* スクリプトや ExecutionEngine 起動フローに統合。
  - 発注時に監視 DB へトレードイベント（Sent 等）を記録するフックを追加（レイテンシ計測・書き込みの例外は警告ログで無視）。
- リスク管理 / レート制御連携:
  - `execution/risk_manager`（参照）を ExecutionEngine 内で使用。Gate1（シグナルレベル検査）、Gate2（実行レベル検査、レート制限・サーキットブレーカー）、Gate3（ポートフォリオドローダウン監視）を導入。
  - Gate2 はリトライ（最大 3 回）を行い、サーキットブレーカー発動時はシグナルループを停止（ただしドレインループは継続）する挙動。
- ユーティリティ:
  - `utils.process_priority.set_process_priority` を使用して起動時にプロセス優先度を "high" に変更する呼び出しを run_* スクリプト・ExecutionEngine 起動に追加。
  - ロギングセットアップ（utils.logging_setup.setup_logging）の呼び出しをエントリポイントに追加。
- パッケージ情報:
  - パッケージ初期化 `__init__` にバージョン `0.1.0` と主要サブパッケージを定義。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Security
- `.env` ファイルは絶対に Git にコミットしない旨を .env 生成テンプレートに明記。

Notes / 注意事項
- config/*.yaml の詳細なスキーマ検証は PyYAML の有無に依存（PyYAML 未インストール時はパース検証をスキップし警告を出力）。
- 実際のブローカー API エラー分類（BrokerAPIError / RateLimitError / OrderRejectedError 等）はブローカー実装に依存するため、外部 API の仕様変更に応じて更新が必要。
- ExecutionEngine と監視の統合は本番運用を想定した安全策（kill switch、pid ファイル、stop flag、リコンシリエーション）を含むが、実運用前に十分なテストを実施してください。

----- 

（今後の変更はここに追記してください）