# CHANGELOG

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。

全体方針:
- バージョンはパッケージ内の __version__ (0.1.0) に合わせています。
- 日付はこのリリースの想定日です。

## [0.1.0] - 2026-04-23

### Added
- 初期リリース: KabuSys 日本株自動売買システムのコア機能を追加。
- 設定/環境系
  - 自動 .env ロード機能（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）を実装（src/kabusys/config.py）。
  - .env のパースロジックを強化（export プレフィックス、シングル/ダブルクォート内のエスケープ、コメント扱いルール等に対応）。
  - Settings クラスを導入し、型付きのプロパティで環境変数を安全に取得（必須項目は未設定時に ValueError を送出）。
  - 環境設定対話ウィザードを追加（python -m kabusys.config_setup）。対話形式で .env を生成/更新し、シークレットはマスク表示して保存する（src/kabusys/config_setup.py）。
  - 設定検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数確認、KABUSYS_ENV / LOG_LEVEL 検証、DB パスや config/*.yaml の存在・パースチェック、KABUSYS_ENV=live 時の追加ガード等を行い、--strict オプションで警告も失敗扱いにできる（src/kabusys/validate_config.py）。
- 実行系エントリポイント
  - 実行エンジン起動スクリプトを追加（python -m kabusys.run_execution）。プロセス優先度設定、PID ファイル管理、paper_trading 時の専用 SQLite 分離、stop フラグ対応等（src/kabusys/run_execution.py）。
  - 監視ループ起動スクリプトを追加（python -m kabusys.run_monitoring）。MONITOR_POLL_INTERVAL によるポーリング間隔上書き、監視用 DB 初期化、停止フラグ検出処理等（src/kabusys/run_monitoring.py）。
- 発注/実行コア
  - OrderRecord（状態モデル）を実装。状態列挙（OrderCreated, OrderSent, OrderAccepted, PartialFill, Filled, Closed, Cancelled, Rejected）と許容遷移のマップ、transition_to メソッドを備える（src/kabusys/execution/order_record.py）。
  - OrderManager を実装。signal_id 重複検出（DuplicateOrderError）、create/send/sync/cancel の外向き API を提供。send_order はクラッシュ耐性を考慮した 2 相永続化手順を採用（OrderSent を先に持続化、broker_order_id を保存してから OrderAccepted に遷移）および OrderSentPendingError / OrderRejectedError の扱いを実装（src/kabusys/execution/order_manager.py）。
  - ExecutionEngine を実装。シグナル処理（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）を含むセッション制御、Gate 1/2/3 によるリスク検査、kill_switch による全注文キャンセル、position_entries への記録、push 処理からの同期処理など（src/kabusys/execution/execution_engine.py）。
  - KabuStationClient（kabu station REST API クライアント）を追加。httpx を用いた同期クライアント、トークンの遅延取得と 401 に対する自動再取得 + リトライ、429 を RateLimitError として扱う、ステータスコードから内部状態へのマッピング等（src/kabusys/execution/kabu_client.py）。
- DB / 監視
  - 監視用 DB 初期化関数を呼び出すコードを run_execution/run_monitoring に追加。monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
- その他ユーティリティ
  - プロセス優先度設定・ロギングセットアップユーティリティを使用して起動時に環境を揃える（run_* スクリプトで利用）。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Notes / Behavior highlights
- .env 読み込みの優先順位:
  - OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- .env のパースは複雑なクォート、エスケープ、インラインコメントを考慮しており、既存のシェルスタイル .env の多くのケースに対応。
- Settings のプロパティは無効な値を検出して ValueError を投げる（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
- ExecutionEngine は発注のクラッシュ安全性を重視:
  - send_order の 2 相永続化により、クラッシュ後でも Reconciler が状態を回復できる。
  - OrderSentPendingError（注文番号は得られたが確定していないケース）を上位に伝播する。Reconciliation により後続で状態回復可能。
- paper_trading モードでは監視 DB と本番 DB を分離（paper 用 sqlite を使用）。
- validate_config は PyYAML がインストールされている場合に config/*.yaml のパース検証を行い、未インストール時は警告を出してスキップする。
- run_monitoring は MONITOR_POLL_INTERVAL の不正な値に対して警告を出しデフォルトにフォールバックする（0 以下は不正扱い）。
- kill.flag の取り扱い:
  - ExecutionEngine 起動前に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START の設定に従い起動を拒否または自動クリアする。
  - kill_switch 発動時は全 active 注文をキャンセルし、stop イベントでループを停止する。

---

注記:
- 本 CHANGELOG はソースコードから推測して作成したものであり、実際のリリースノートは実装状況やリリースポリシーに合わせて適宜調整してください。