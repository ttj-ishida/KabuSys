# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に基づきます。

## [0.1.0] - 2026-04-23

### Added
- 初期リリース。日本株自動売買システム「KabuSys」の基本機能を実装。
- 環境・設定管理
  - Settings クラスによる環境変数ベースの設定管理を追加（src/kabusys/config.py）。
  - .env 自動読み込み機能（プロジェクトルートの .env / .env.local）。OS 環境変数を保護する読み込み順序（OS > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - .env パーサを実装（クォート・エスケープ・コメント処理に対応）。行パース関数で安全に値を取得。
  - run 対応プロパティ群（duckdb/sqlite パス、PID / kill flag パス、閾値、PAPER_FILL_MODE 等）と入力検証（有効値チェック、ValueError 投げる場合あり）。
- 設定ウィザード CLI（src/kabusys/config_setup.py）
  - 対話式に .env を作成・更新するウィザードを提供。
  - シークレット項目は表示時にマスク。
  - 既存 .env 読み込み、Enter で既存値を採用可能。保存前に確認プロンプトを表示。
  - .env の書式テンプレート生成機能（.env に書き込む _write_env）。
- 設定検証 CLI（src/kabusys/validate_config.py）
  - 起動前に .env と config/*.yaml の整合性を検証する CLI を提供。
  - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の値チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START 警告）。
  - 出力に INFO/WARNING/ERROR を整形して表示。--strict フラグで警告も失敗扱い（exit 1）。
- 実行スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine をデーモン的に起動、PID ファイル管理、stop flag 検出、paper_trading 時の DB 分離（paper_trading 用 SQLite を使用）。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを提供。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用。
- Execution エンジン（src/kabusys/execution/execution_engine.py）
  - Signal Queue Pull 型の発注エンジンを実装。シグナル処理時間帯（8:50–9:10）と push ドレイン（9:10–15:30）を管理。
  - kill_flag 検査、PID ファイル書き込み、WebSocket push の受信とドレイン処理、position_entries 更新ロジックを実装。
  - Gate 1（シグナルレベル）、Gate 2（エグゼキューション制御／レート制限・サーキットブレーカー）、Gate 3（ドローダウン監視）によるリスク制御を呼び出すフローを実装。
  - 発注成功・保留（pending）・失敗の処理、監視 DB へのトレードイベント記録（監視DBが渡された場合）。
- 注文管理
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態列挙（OrderState）と許可された状態遷移を定義。遷移チェックと更新ロジック（更新時に UTC タイムスタンプ更新）を実装。
  - OrderManager（src/kabusys/execution/order_manager.py）
    - DB（OrderRepository）と組み合わせた外向き API を提供（create_order, send_order, sync_order, cancel_order）。
    - DuplicateOrderError による同一 signal_id の多重発注防止。
    - send_order における二相的永続化パターンを採用（OrderSent 永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 更新）によりクラッシュ耐性を向上。
    - OrderRejectedError、OrderSentPendingError の扱いを実装。pending の場合は broker_order_id を保存して呼び出し元へ伝播。
    - sync_order で broker の状態をローカルに同期。部分約定更新を差分で反映。必要に応じて OrderAccepted を経由して遷移。
    - cancel_order はキャンセル不可能状態のチェックを行い、broker API 呼び出しと状態遷移を実行。
- ブローカークライアント（kabuステーション用）
  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - httpx を用いた同期 REST クライアント実装。内部でトークン管理を行い、401 時にトークンを再取得して再試行。
    - JSON パース失敗やタイムアウト、ネットワークエラー、429（レート制限）や 5xx を BrokerAPIError / RateLimitError などに変換。
    - 将来の async 対応を容易にする設計（httpx.AsyncClient への置換で対応可能）。
    - kabu ステーションの状態コードを内部ステータス（open/partial/filled/cancelled/rejected）へマップ。
- Reconciler / Risk 管理等の統合ポイントを追加（実装部位は別モジュールだが ExecutionEngine と組み合わされて動作する設計）。
- Logging / プロセス優先度
  - 起動時に共通のログセットアップを呼ぶ（setup_logging の利用点を複数箇所に追加）。
  - プロセス優先度を上げるユーティリティ呼び出し（set_process_priority("high")）を起動初期に実行。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Security
- .env の生成テンプレートに注意書きを追加（.env を絶対に Git にコミットしない旨）。
- config_setup の対話表示でシークレット項目をマスクして表示。

### Notes / Internals
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ実行され、未インストール時は警告してパース検証をスキップする仕組み。
- DUCKDB_PATH / SQLITE_PATH の親ディレクトリが存在しない場合は警告（起動時に自動作成される可能性あり）。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を特に注意する旨の警告を出すガードを実装。
- PAPER_FILL_MODE の値検証を行い、不正値は ValueError を送出して早期に検出する。

---

今後のリリースでは、テストカバレッジ・ドキュメント整備・Reconciler / RiskManager の改善・非同期クライアント対応・追加の監視/アラート機能等を予定しています。