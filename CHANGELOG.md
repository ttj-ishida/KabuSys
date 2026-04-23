Keep a Changelog に準拠した CHANGELOG.md（日本語）
※コードベースから推測して作成しています。実装の意図や細部はソースを参照してください。

0.1.0 - 2026-04-23
=================

Added
-----
- 初回リリース: KabuSys v0.1.0 を追加。
- 実行エンジン (ExecutionEngine)
  - Signal Queue ベースの発注フローを実装（kabu push ドレイン／シグナル処理の2相構成）。
  - EngineConfig による実行日・発注開始/終了/市場クローズの設定。
  - シグナル取得は DuckDB から行い、position_entries の更新（発注成功時）を行う。
  - WebSocket プッシュを受け取る _websocket_worker を持ち、受信推移は内部キューへ格納して処理。
  - kill_switch による全注文キャンセル、外部停止（stop）API、PID ファイル管理を提供。
  - Reconciler を利用した起動時のリコンシリエーション処理をサポート。
  - ポーリングやスレッド管理、ログ出力を含むセッション実行ロジックを実装。

- 注文管理 (OrderRecord / OrderManager / OrderRepository 連携)
  - OrderRecord: 状態遷移（状態マシン）を明示し、不正遷移時に InvalidStateTransitionError を投げる。
  - 許可遷移セットを定義し、状態（created → sent → accepted → partial/filled → closed/cancelled/rejected）を明確化。
  - OrderManager:
    - create_order/send_order/sync_order/cancel_order の外向き API を実装。
    - DuplicateOrder の検出（signal_id の部分ユニーク制約と DB 参照の両面で対応）。
    - send_order のクラッシュ耐性設計（OrderSent を先に永続化、broker_order_id を先にコミットする2相的保存によりリコンシリエーション対応）。
    - OrderRejectedError / OrderSentPendingError の扱いを明確化（pending は永続化して再照合対象にする）。
    - sync_order による broker 側ステータス照合と部分約定情報の更新ロジック。
    - cancel_order は終端状態の検出と API 呼び出し、状態遷移を担保。

- ブローカークライアント（KabuStationClient）
  - kabuステーション REST API 用クライアントを httpx で実装。
  - トークン取得の遅延初期化、401 に対する自動再取得とリトライの仕組みを持つ。
  - レスポンス JSON パースのエラーハンドリング、429 を RateLimitError にマッピング。
  - WebSocket ベースの push（stream_push）をサポートする実装想定に対応。

- 実行スクリプト
  - run_execution.py:
    - プロセス優先度設定、高優先度での実行をサポート。
    - paper_trading モードでは paper_trading 用 SQLite DB を使用して本番 DB と分離。
    - 停止フラグ検知によるデーモン制御、スレッドベースのセッション実行。
  - run_monitoring.py:
    - SystemMonitor のポーリングループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境に関係なく本番 sqlite_path を使用。

- 設定管理 / .env ユーティリティ
  - config.py:
    - Settings クラスによる環境変数ラッパーを実装（型変換、検証付き）。
    - .env / .env.local の自動読み込み機能（OS 環境変数を保護して上書き制御）。
    - プロジェクトルート検出は .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - .env パーサは export 形式、クォート、エスケープ、インラインコメントを考慮して堅牢に実装。
    - PAPER_FILL_MODE 等の列挙的な検証ロジックを実装（不正値は ValueError）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
  - config_setup.py:
    - 対話式ウィザードで .env を生成／更新する CLI を提供。
    - シークレット項目はマスク表示、選択肢サポート、デフォルト値、保存前の確認を実装。
    - .env を生成する際にコミット禁止の注意コメントをファイルに含める。

- 設定検証 CLI（validate_config）
  - .env と config/*.yaml（ファイル存在チェック、PyYAML があればパース検証）を起動前に検出する CLI を追加。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）、プレースホルダ検出（"_here" や "your_value"）で警告。
  - KABUSYS_ENV の妥当性チェック、live の場合の注意喚起（LINE 通知設定や Kill Flag の設定）を追加。
  - --strict モードで警告を FAIL（exit code 1）として扱う。
  - DB パス（DUCKDB_PATH, SQLITE_PATH）の親ディレクトリ存在チェック（存在しない場合は警告）。

- 監視 & ロギング周り
  - 監視 DB 初期化（init_monitoring_db）を run_execution/run_monitoring で呼び出し、監視用テーブルが存在することを保証。
  - 実行中は監視 DB に発注イベントをログ（latency_ms 等）できるフックを配置（監視 DB が提供されている場合）。
  - utils 側に logging_setup, process_priority などの補助ユーティリティを想定して統合。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Security
--------
- .env は絶対に Git にコミットしないよう、config_setup で生成されるファイルに注意文を付与。
- シークレット項目は対話でマスク表示（config_setup）。

Notes / Implementation Remarks
------------------------------
- クラッシュ安全性: send_order の設計はクラッシュ後に再照合（Reconciliation）で回復可能なように、broker_order_id の永続化や OrderSent のまま残すシナリオを想定しています。
- Paper trading の DB 分離: 本番 DB と paper_trading 用 DB を明確に分離して動作します（実データと取り扱いを混在させない）。
- YAML 検証は PyYAML の有無に依存します。PyYAML が未インストールの場合はパース検証をスキップして警告を出します。
- 多くのコンポーネント（BrokerFactory、RiskManager、Reconciler、OrderRepository、MonitoringDB 等）はモジュール間で連携する設計になっており、単体テストや統合時のモック差し替えが想定されています。

Future (提案)
------------
- async 対応（httpx.AsyncClient）や非同期 WebSocket 処理への移行。
- モニタリング／メトリクスの更なる拡充（Prometheus 等）。
- より詳細なリリースノート（機能ごとの小バージョンで追記）。

---
以上。必要であれば日付や項目の粒度を調整して更新版 CHANGELOG を作成します。