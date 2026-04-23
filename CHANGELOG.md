# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトの初回リリースを以下にまとめます。

## [0.1.0] - 2026-04-23

### 追加
- 全体
  - プロジェクト初期実装を追加。モジュール群は自動売買システム「KabuSys」の基盤機能を提供します。
  - パッケージバージョンを定義: `__version__ = "0.1.0"`。

- 設定管理 (`src/kabusys/config.py`)
  - .env ファイル / 環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルートを `.git` または `pyproject.toml` から検出して `.env` と `.env.local` を読み込む。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - OS 環境変数を保護して .env による上書きを制御。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用）。
  - .env パーサ実装の注意点:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のエスケープ処理をサポート。
    - クォートなし行ではインラインコメント（`#`）を取り扱うルールを実装。
  - Settings が提供する主要プロパティ:
    - J-Quants / kabu API トークン取得 (`jquants_refresh_token`, `kabu_api_password`, `kabu_api_base_url`)。
    - LINE 通知設定（`line_channel_access_token`, `line_user_id`）。
    - DB パス（`duckdb_path`, `sqlite_path`, `paper_sqlite_path`）、PID/kill flag パス。
    - 環境種別（`env`）・ログレベル（`log_level`）・paper_trading 用の挙動（`paper_fill_mode`）等。
    - 各種しきい値（CPU/Memory/Disk）と kill flag の自動クリア設定。
  - 未設定の必須環境変数取得時は例外を投げる `_require()` を実装。

- 環境設定ウィザード CLI (`src/kabusys/config_setup.py`)
  - 対話式ウィザードにより .env の初期作成／更新を支援。
  - 項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を備える。
  - 既存 .env の読み込み、入力補助（デフォルト、選択肢、シークレットのマスク）、保存プレビュー、確認して書き出す機能を実装。
  - 書き出しフォーマットはコメントを含むテンプレート化された .env（Git へコミットしない注意書き付き）。

- 設定検証 CLI (`src/kabusys/validate_config.py`)
  - .env および config/*.yaml の起動前検証ツールを実装。
  - チェック内容:
    - 必須環境変数の存在（プレースホルダ値の検出と警告）。
    - KABUSYS_ENV の妥当性チェック（development, paper_trading, live）。
    - LOG_LEVEL の妥当性チェック。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）の親ディレクトリ存在チェック。
    - config/*.yaml ファイルの存在確認と（PyYAML があれば）パース検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定未設定、KILL_FLAG_CLEAR_ON_START の危険値検出）を実行。
  - CLI オプション `--strict` を追加（警告も FAIL として exit(1)）。
  - 実行例: `python -m kabusys.validate_config`。

- 実行用スクリプト
  - 監視ループ起動スクリプト `src/kabusys/run_monitoring.py` を追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用。
    - stop フラグ検出・例外ログ処理・DB の初期化（`init_monitoring_db`）を行う。
  - エンジン起動スクリプト `src/kabusys/run_execution.py` を追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（settings.paper_sqlite_path）を使用し、本番 DB と分離。
    - ExecutionEngine を別スレッドで起動し、停止フラグ検出で安全停止する。
    - PID ファイル・停止フラグ管理・プロセス優先度設定（high）を行う。

- Execution / 発注基盤
  - ExecutionEngine (`src/kabusys/execution/execution_engine.py`)
    - Signal Queue ベースの発注エンジンを実装（シグナル処理時間帯、push ドレインループ等のセッション制御）。
    - run_session: 起動時リコンシリエーションの呼び出し、kill.flag チェック、PID ファイル管理、WebSocket スレッド起動、シグナル処理（8:50-9:10）、push ドレイン（9:10-15:30）を実装。
    - _process_signals: size_multiplier の適用、Gate 1（シグナルレベル）/ Gate 2（実行レベル、レート制限・サーキットブレーカー）を通して発注を実行。
    - _drain_push_queue/_handle_push: ブローカー push を処理し sync_order を実行、Gate 3（ドローダウン監視）を実施して必要なら kill_switch を発動。
    - kill_switch: 全 active 注文のキャンセルとループ停止。外部 stop() はこれの公開エイリアス。
    - WebSocket は broker が stream_push を持たない場合はスキップする設計になっている。
    - 発注時の監視データ（latency 等）を monitoring DB にログ可能。

  - OrderRecord / Order State Machine (`src/kabusys/execution/order_record.py`)
    - 注文状態を列挙する OrderState 列挙型を導入（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許可遷移テーブルと transition_to による遷移検証を実装。無効遷移時は InvalidStateTransitionError を raise。
    - レコードは DB 操作を持たず、純粋なビジネスロジックのみを提供。

  - OrderManager (`src/kabusys/execution/order_manager.py`)
    - signal_id をキーにした重複注文検出（DuplicateOrderError）。
    - create_order: UUID ベースの client_order_id を採番して OrderCreated レコードを保存。DB 側の部分ユニーク制約違反を DuplicateOrderError に変換。
    - send_order: クラッシュ耐性を考慮した発注フロー（OrderSent に先に永続化 → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted に遷移）を実装（2相永続化の考慮）。
      - OrderRejectedError は Rejected に遷移して保存。
      - OrderSentPendingError（注文番号は発行されたが約定しないケース）は broker_order_id を保存した上で OrderSent のまま残し、呼び出し元へ再送出。
    - sync_order: broker から状態を取得して内部状態に同期。部分約定の進行はフィールド直接更新で対応。
    - cancel_order: 終端状態の場合は InvalidStateTransitionError を返す。broker_order_id がある場合は API によるキャンセルを行う。

  - Broker API / KabuStationClient (`src/kabusys/execution/kabu_client.py`)
    - kabu station REST API 用の同期クライアントを実装（httpx を使用）。
    - トークン管理（遅延取得・401 時の再取得と1回リトライ）を実装。
    - レスポンス JSON パースエラーやネットワークエラーを BrokerAPIError に変換。
    - HTTP 429 を RateLimitError として扱う。
    - kabu ステータスコードと内部状態のマッピングを定義（open/partial/filled/...）。
    - 将来の WebSocket / 非同期対応を考慮した設計（stream_push の有無で WebSocket スレッドを切り替え）。

- リスク管理 / 再調整理 / モニタリング連携
  - ExecutionEngine は RiskManager（Gate 1/2/3）と連携して発注判断（rate limit, circuit breaker, ドローダウン等）を行う。
  - Reconciler（部分的に実装を想定）と起動時リコンシリエーションの呼び出しを統合。
  - 発注成功/失敗に応じた監視 DB へのログ出力処理を組み込み（失敗しても発注フローを継続する設計）。

### 変更
- なし（初回リリース）。

### 修正
- なし（初回リリース）。

### 既知の注意点 / 設計上の挙動
- .env のパーサは多くのケースを扱うが、極端に複雑なシェル展開や特殊なエスケープは想定外となる場合があります。
- validate_config は PyYAML がインストールされていない場合、YAML の内容検証をスキップして警告を出します。
- ExecutionEngine の発注ルーチンはクラッシュ安全性を重視しており、OrderSent 状態でクラッシュした場合は再調整（reconciliation）で回復できるように broker_order_id の永続化順序等を工夫しています。
- KABUSYS_ENV=live の場合は本番用の注意喚起が多数出ます。LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の設定ミスは警告対象です。

---

今後のリリースでは各コンポーネント（broker API の詳細実装、Reconciler の完全実装、テストの追加、ドキュメント整備など）を追記していく予定です。