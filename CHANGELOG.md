# Changelog

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-23

初回公開リリース。

### 追加 (Added)
- パッケージ基本構成を導入
  - バージョン定義: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 環境変数 / 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env の自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - _require() による必須環境変数取得（未設定時は ValueError を送出）。
    - 各種プロパティを提供: J-Quants / kabu API / LINE / DB パス / PID/killing フラグ / CPU/MEM/DISK閾値 / env/log_level など。
    - paper_trading 用の専用 SQLite パス（PAPER_TRADING_SQLITE_PATH）と PAPER_FILL_MODE 検証。
- .env 対応ユーティリティ
  - 高機能な .env パーサを実装（export プレフィックス対応、クォート/エスケープ/インラインコメント処理等）。
  - .env ファイルを上書き/保護付きで読み込む _load_env_file を実装。
- .env 対応 ウィザード CLI（src/kabusys/config_setup.py）
  - 対話式ウィザードで .env を新規作成・更新。
  - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB/SQLITE パス, LINE トークン, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）。
  - 既存 .env 読み込み、シークレットマスク表示、保存確認、書き込みヘッダを追加。
  - --env-file オプションで保存先を変更可能。
- 設定検証 CLI（src/kabusys/validate_config.py）
  - .env と config/*.yaml の設定不備（未設定の必須環境変数、プレースホルダ値、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在、YAML パースエラー等）を起動前に検出。
  - PyYAML が未インストールの場合は YAML 内容検証をスキップして警告を出す。
  - --strict モードで警告を FAIL として exit(1)。
  - 出力は INFO / WARNING / ERROR を列挙して終了コードを返す。
- 実行エントリスクリプト
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
    - stop_requested.flag による停止検知、例外時のログ出力、DB 初期化・接続管理（SQLite / DuckDB）。
  - 発注エンジン起動スクリプト: src/kabusys/run_execution.py
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用して本番 DB と分離。
    - PID / stop フラグ管理、プロセス優先度設定、DB 初期化、ExecutionEngine の起動ループ管理。
- Execution コア実装
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - Signal Queue 型発注エンジン。シグナル処理時間帯（デフォルト 8:50–9:10）、push ドレイン（9:10–15:30）を実装。
    - kill.flag に基づく Kill Switch、PID ファイル管理、WebSocket push の受信と処理（_push_queue を介した非同期処理）。
    - Gate1/Gate2/Gate3 による多段リスク検査と再試行戦略（rate limit、circuit breaker、ドローダウン検査）。
    - 発注遅延・監視 DB ログ出力フック（MonitoringDB が渡された場合）。
    - DuckDB を用いた signals / portfolio_targets の読み込みロジック。
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態列挙（OrderCreated, OrderSent, OrderAccepted, PartialFill, Filled, Closed, Cancelled, Rejected）。
    - 状態遷移許可テーブルと transition_to メソッド（不正遷移時は InvalidStateTransitionError を送出）。
    - 約定数量・平均価格・エラーメッセージ等のフィールド更新ロジック。
  - OrderManager（src/kabusys/execution/order_manager.py）
    - create_order / send_order / sync_order / cancel_order の外向け API を実装。
    - create_order は signal_id の重複チェック（DB の部分ユニーク制約違反も DuplicateOrderError に変換）。
    - send_order はクラッシュ耐性を意識した 2 相永続化（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted に遷移）を実装。
    - OrderSentPendingError を処理して broker_order_id を保存したまま保留扱いとする挙動。
    - sync_order による broker 側状態照合と部分約定更新。OrderSent→Filled 等の一気通貫状態を OrderAccepted を経由して扱う安全策。
    - cancel_order は終端状態ではキャンセル不可のチェック（InvalidStateTransitionError）。
- ブローカー/KabuStation クライアント
  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - httpx を使用した同期 REST クライアント実装。
    - トークン取得 (_get_token)、401 時の再取得 + 1 回リトライ、429 (RateLimit) と 5xx のエラーハンドリングを実装。
    - stream_push の存在に応じて WebSocket push 受信をサポートする設計（on_message コールバックで _push_queue に投入する想定）。
    - レスポンス JSON パース失敗を BrokerAPIError に変換するユーティリティを実装。
- 監視関連
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を利用して監視テーブルの存在を保証（run_monitoring / run_execution）。
  - 監視ループ・発注時に監視 DB へイベント記録するフックポイントを提供（MonitoringDB が注入された場合）。
- ユーティリティ
  - プロセス優先度設定ユーティリティ（set_process_priority）の利用が導入され、監視/実行プロセスを高優先度で動かす仕組みを組み込み。

### 変更 (Changed)
- 設定検証（validate_config）と Settings の検証ロジックを整理
  - validate_config は必須/任意環境変数リスト、KABUSYS_ENV / LOG_LEVEL 値の妥当性チェック、DB パス親ディレクトリ存在チェック、config/*.yaml の存在・パース検証を行う。
  - validate_config に --strict オプションを追加（警告も失敗扱いにできる）。

### 修正 (Fixed)
- 初期リリースにおける安全性強化
  - 発注フローのクラッシュ耐性を考慮した永続化順を実装（OrderSent を先にコミット → broker 呼び出し → broker_order_id をコミット → OrderAccepted に遷移）。
  - Reconciliation によるクラッシュ後の状態回復を念頭に broker_order_id の永続化を保証。
  - kill.flag / KILL_FLAG_CLEAR_ON_START の扱いと関連ログ出力を明確化（ ExecutionEngine 起動時の既存 kill.flag の挙動）。

### ドキュメント (Documentation)
- config_setup ウィザードの各項目説明を追加（ラベル・説明・選択肢・デフォルトを表示）。
- validate_config の使い方をモジュールドクストリングで説明（--strict の説明含む）。
- run_monitoring/run_execution のトップレベルドクストリングで動作概要を説明（MONITOR_POLL_INTERVAL、paper_trading の DB 分離等）。

### 既知の制限 / 注意点
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ実行され、未インストール時は警告でスキップされる。
- KabuStationClient は同期 httpx.Client を使用しており、将来 async 化する場合は httpx.AsyncClient へ移行する設計になっている。
- 一部のコンポーネント（RiskManager, Reconciler, BrokerClientFactory, OrderRepository, MonitoringDB 等）はこのリリースでの参照実装を前提としている。外部実装に依存する部分については実行環境での適切な提供が必要。

---

次回リリースでは以下が考慮されています（例）:
- テストカバレッジの追加（OrderRecord / OrderManager のユニットテスト）
- 非同期化やパフォーマンス改善（httpx AsyncClient への移行、WebSocket 処理の最適化）
- CLI ドキュメントの整備とヘルプ強化

（以上）