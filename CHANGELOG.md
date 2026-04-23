# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

- リリース日付は ISO 形式 (YYYY-MM-DD) です。
- 重要な変更のみを記載しています（内部実装の微細な修正やリファクタは省略する場合があります）。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-04-23

### Added
- パッケージ初期リリース。日本株自動売買システム「KabuSys」の基礎機能を追加。
- 環境設定・管理
  - Settings クラスを提供（src/kabusys/config.py）。環境変数からアプリ設定を取得する共通インターフェースを実装。
  - 自動 .env ロード機能を追加（プロジェクトルートの .env/.env.local を読み込む）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサを実装（export 形式やシングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
- 対話式セットアップ
  - 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）。.env の初期作成・更新を対話式でサポート。
  - ウィザードは各設定項目の説明、選択肢、マスク表示（シークレット）に対応。生成される .env のテンプレート出力を実装。
- 設定検証ツール
  - validate_config CLI を追加（src/kabusys/validate_config.py）。起動前に .env や config/*.yaml の有無・基本整合性を検査。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DBパス親ディレクトリ存在チェック、PyYAML があれば config/*.yaml のパース検証、KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）を実装。
  - --strict オプションで警告を失敗扱いにできる（exit code 1）。
- 実行用スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。プロセス優先度設定、DB 接続、ExecutionEngine の起動/ループ制御、停止フラグ検出を実装。
  - 監視プロセス起動スクリプト（src/kabusys/run_monitoring.py）を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用。
- Execution (発注) 基盤
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）を実装。指定時刻レンジでのシグナル処理と WebSocket push ドレインループ、kill flag 処理、PID ファイル管理、リコンシリエーション呼び出し等を実装。
  - EngineConfig による実行パラメータ管理（target_date / signal_send_start / signal_send_end / market_close）。
  - WebSocket push 受信を別スレッドで処理し、push による同期・Gate 3 チェックを実施。
- 注文状態管理
  - OrderRecord（src/kabusys/execution/order_record.py）を追加。状態遷移（OrderState 列挙）と遷移検証ロジック（InvalidStateTransitionError）を純粋モデルとして実装。
  - OrderManager（src/kabusys/execution/order_manager.py）を追加。OrderRecord と OrderRepository を組み合わせた外向き API（create/send/sync/cancel）を実装。DuplicateOrderError、OrderSentPendingError などのエラー扱いを実装。
  - send_order における「2 相永続化」戦略を導入：OrderSent を先にコミットし、broker_order_id を保存 → OrderAccepted に移行。クラッシュ時の復旧パターンを考慮。
- ブローカー API クライアント
  - KabuStationClient（src/kabusys/execution/kabu_client.py）を実装。httpx を利用した同期 REST クライアント、トークンの遅延取得・自動再取得、401/429/5xx のハンドリング、WebSocket push のサポート（stream_push を前提）を実装。
  - API レスポンスパース失敗時のエラー変換を実装。
- リスク管理・リコンシリエーション・監視連携
  - RiskManager / Reconciler / MonitoringDB との連携ポイント（ExecutionEngine/OrderManager）を実装（詳細実装ファイルは別途含まれる想定）。
  - 発注成功時に position_entries へ約定日登録を行い、監視 DB にトレードイベントを記録するフックを追加。
- データベース
  - duckdb と SQLite を併用する設計を導入。paper_trading モードでは paper_trading 用 SQLite DB（data/paper_trading.db）を使用し、本番 DB と分離。
  - 監視用 DB の初期化ヘルパ（init_monitoring_db）呼び出しを追加。
- ユーティリティ
  - process_priority 設定・logging セットアップユーティリティを利用してプロセス起動時に適切なログ設定・優先度設定を行う。

### Changed
（初回リリースのため該当なし）

### Fixed
（初回リリースのため該当なし）

### Notes / Design decisions
- .env の自動ロードは OS 環境変数を保護するため、読み込み時に既存 OS 環境変数を上書かない（.env.local は override=True で上書き可能だが protected による保護あり）。
- validate_config は PyYAML が未インストールでも警告を出して YAML 内容検証をスキップするようにして、導入ハードルを下げている。
- ExecutionEngine の発注フローはクラッシュ・再起動時の復旧を考慮しており、OrderSent のまま残るケースや broker_order_id の永続化を活用して Reconciler により状態回復可能にしている。
- Monitoring は常に「本番」 sqlite_path を使用する（監視は環境に依存しない観点からの設計）。
- KabuStationClient は将来的な非同期化（httpx.AsyncClient）を見据えた設計。

### Known limitations / TODO
- 一部依存コンポーネント（OrderRepository、RiskManager、Reconciler、MonitoringDB、SystemMonitor 等）の詳細実装/テストについては別途整備が必要。
- CLI の入出力は現在標準入力/出力に依存しており、自動化スクリプトからの利用時には注意が必要（config_setup の対話をスキップするオプションは未実装）。
- config/*.yaml のスキーマ検証は PyYAML でのパースのみで、より厳密なスキーマ検証（JSON Schema 等）は未実装。

-----

作者: KabuSys 開発チーム  
初版: 0.1.0 (2026-04-23)