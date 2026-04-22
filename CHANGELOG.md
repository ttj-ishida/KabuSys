CHANGELOG
=========

すべての変更は Keep a Changelog の規約に準拠して記載しています。

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-22
-------------------

Added
- 全体: 初回リリース。日本株自動売買システム「KabuSys」の基盤的な設定管理、実行エンジン、監視機能、ブローカー API クライアント等を実装。
- 設定読み込み / 管理:
  - Settings クラスを追加。環境変数から型変換・バリデーションを行い、アプリケーション設定を一元提供。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。読み込み順序は OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パースを堅牢化（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理の取り扱い改善）。
  - PAPER_FILL_MODE（paper_trading 動作モード）など特定設定のバリデーションを実装。
  - paper_trading 用に paper_sqlite_path を分離。Paper Trading 環境では本番 DB と完全分離して動作。
- 設定ウィザード / CLI:
  - config_setup.py: 対話式ウィザードを追加 (.env の初期生成／更新を支援)。機密値は入力表示をマスク、既存値の再利用、デフォルト選択肢の提示、保存前の確認を実装。生成される .env ファイルにヘッダと注意書きを挿入（.env をコミットしない旨）。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数の未設定検出、プレースホルダ値の警告、KABUSYS_ENV / LOG_LEVEL の検証、DB パス親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML が利用可能な場合）パース検証、KABUSYS_ENV=live 時の追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の警告）。--strict オプションで警告も失敗扱いにできる。
- 実行スクリプト:
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。起動時にプロセス優先度を上げ、PID ファイル管理、停止フラグ検出（data/stop_requested.flag）などを実装。paper_trading 時は専用 SQLite を使用。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
- Execution / 発注関連:
  - ExecutionEngine: シグナルベースの発注フローを実装（シグナル処理窓: 8:50–9:10、push ドレイン: 9:10–15:30）。WebSocket push を受けて同期処理する機構、PID/kill.flag の扱い、reconciler による起動時リコンシリエーション呼び出し、position_entries への約定予定日記録、監視 DB へのイベントロギングを実装。
  - OrderRecord: 注文状態を表す状態マシン（OrderState）と状態遷移ロジックを実装。不正遷移は InvalidStateTransitionError を送出。
  - OrderManager: DB（OrderRepository）と OrderRecord を組み合わせた外向き API を実装。create/send/sync/cancel の各処理を提供。send_order はクラッシュ安全性を考慮した 2 相的な永続化戦略を採用（OrderSent の永続化 → ブローカー呼び出し → broker_order_id の永続化 → OrderAccepted へ遷移）。OrderSentPendingError、OrderRejectedError の扱い、duplicate（同一 signal_id）検出と DuplicateOrderError 変換、sync_order による外部状態との再同期ロジックを実装。
  - ExecutionEngine 側におけるリスク Gate:
    - Gate 1: シグナル単位の検査
    - Gate 2: 実行（レート制限等）検査（リトライと Circuit Breaker 扱い）
    - Gate 3: ポートフォリオメトリクス（ドローダウン）検査。NG の場合は kill_switch を発動して全 active 注文をキャンセル。
  - cancel_order ではキャンセル不可能な状態セット（Closed / Cancelled / Rejected / Filled）を定義し、適切にエラーを返す。
- ブローカー API クライアント:
  - kabu_client.py (KabuStationClient): httpx を用いた同期 REST クライアントを実装。トークンの遅延取得と自動再取得、401 による一回のリトライ、429 に対する RateLimitError、JSON パース失敗の変換など堅牢化を行った。また WebSocket（push）受信のサポートを想定（stream_push を持つブローカーに依存）。
- 監視 / DB 初期化:
  - monitoring_db.init_monitoring_db の呼び出しを導入し、監視用 SQLite のテーブル存在を保証する（冪等）。
- ユーティリティ:
  - ロギングセットアップ・プロセス優先度設定ユーティリティを呼出し（setup_logging, set_process_priority）、各スクリプト起動時に適用。

Changed
- 設計 / 安全性:
  - 発注フローおよびリコンシリエーション戦略を導入し、クラッシュ耐性を向上（OrderSent の中間状態の扱い、broker_order_id 永続化による復旧）。
  - Paper trading と本番データを明確に分離（専用 SQLite path / fill モード設定等）。
  - .env の読み込み時に OS 環境変数を保護することで、CI / テスト環境での予期せぬ上書きを防止。

Fixed
- N/A（初回リリースのため既知の不具合修正はなし）

Security
- .env ファイルに機密情報（API トークン／パスワード等）を含めるため、config_setup に .env を絶対に Git にコミットしない旨の注意を追加。
- HTTP API の認証トークン管理を内部で行い、401 発生時にトークンを再取得してリトライすることで一時的な認証切れに対応。

Notes / Known limitations
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ実行される。PyYAML 未導入時はパースチェックがスキップされ、警告が出力される。
- KabuStationClient は同期 httpx.Client ベース。将来の非同期化は httpx.AsyncClient に差し替えることで対応可能。
- 実運用では KABUSYS_ENV=live を指定した場合、LINE 通知などの追加設定を適切に整備する必要あり（validate_config が警告を出します）。
- ExecutionEngine の時間判定はローカル時計に依存するため、運用環境の時刻管理に注意が必要。

作者
- KabuSys チーム

---