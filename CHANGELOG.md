# CHANGELOG

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-04-22
初回リリース。KabuSys の基本的な設定管理、実行エンジン、発注フロー、監視、および kabuステーション API クライアントを含むコア機能を実装しました。

### 追加
- 設定検証 CLI を追加
  - `src/kabusys/validate_config.py`
  - .env と `config/*.yaml` の存在・基本整合性を起動前に検出するツールを実装。警告を失敗扱いにする `--strict` オプションを提供。
  - 必須/任意の環境変数チェック、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性検証、DBパスの親ディレクトリ存在チェック、PyYAML 有無に応じた YAML パース検証、本番環境用の追加ガードを実装。

- 環境設定ウィザードを追加
  - `src/kabusys/config_setup.py`
  - 対話式に `.env` を初期作成・更新するウィザードを提供。シークレット項目のマスク表示、選択肢/デフォルト値対応、`.env` の読み書きロジックを実装。

- 環境変数 / 設定読み込みモジュールを追加
  - `src/kabusys/config.py`
  - プロジェクトルート探索（`.git` / `pyproject.toml`）に基づく自動 .env ロード（`.env` → `.env.local`、OS 環境変数保護、`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
  - `.env` の行パーサーは `export` 形式、クォート、エスケープ、コメントを考慮している。
  - `Settings` クラスを導入し、各種設定（API トークン、DB パス、PID / kill flag パス、しきい値、環境/ログレベルなど）をプロパティで提供。妥当性検証（例: `PAPER_FILL_MODE`, `KABUSYS_ENV`, `LOG_LEVEL`）は `ValueError` を送出。

- 実行 / 監視スクリプトを追加
  - `src/kabusys/run_execution.py`
    - ExecutionEngine の起動スクリプト。プロセス優先度設定、paper_trading 時の DB 分離（`paper_sqlite_path`）、PID / stop flag 管理、スレッドによるエンジン実行を実装。
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプト。`MONITOR_POLL_INTERVAL` によるポーリング間隔上書き、監視用 DB は環境に関わらず本番 sqlite_path を使用。

- 発注関連コア実装を追加
  - `src/kabusys/execution/order_record.py`
    - 注文状態を列挙する OrderState と状態遷移を検証する OrderRecord（純粋ロジック、DB 非依存）を実装。許可された遷移テーブルと不正遷移時に送出される `InvalidStateTransitionError` を導入。
  - `src/kabusys/execution/order_manager.py`
    - `OrderManager` を追加。`create_order`（重複検知と DB 永続化）、`send_order`（2相永続化パターンによるクラッシュ耐性、`OrderRejectedError` / `OrderSentPendingError` の扱い）、`sync_order`（broker 状態同期）、`cancel_order`（キャンセル可否判定）を実装。DB 側のユニーク制約違反を `DuplicateOrderError` に変換する処理あり。
  - `src/kabusys/execution/order_repository.py` 等と連携して発注フローを構成（関連呼び出しは実装を想定）。

- ExecutionEngine 本体を追加
  - `src/kabusys/execution/execution_engine.py`
  - シグナル取得 → Gate1/2 によるリスクチェック → 発注 → push ドレイン / Gate3 チェック（ドローダウン監視）までの一連のセッションロジックを実装。
  - kill switch（全 active 注文のキャンセル）、WebSocket プッシュ受信ワーカー、発注遅延計測と監視 DB へのログ記録、position_entries への書き込み（DuckDB 使用）などの運用向け機能を含む。
  - Reconciliation（起動時同期）のフックを提供し、`Reconciler` を介した復旧に対応。

- kabuステーション API クライアントを追加
  - `src/kabusys/execution/kabu_client.py`
  - `KabuStationClient` を実装（httpx 同期クライアント、websocket の push 受信をサポート）。トークン管理（遅延取得・401 に対する再取得とリトライ）、HTTP ステータスに応じた例外（429 → RateLimitError、5xx → BrokerAPIError 等）ハンドリング、kabu ステータスコード→内部ステータス変換を実装。

- その他ユーティリティ / 初期化
  - `src/kabusys/__init__.py` にバージョン定義（0.1.0）と公開パッケージ一覧を追加。
  - 監視 DB 初期化関数 `init_monitoring_db`、プロセス優先度設定 `set_process_priority`、ログセットアップ `setup_logging` 等のユーティリティ呼び出しを各起動スクリプトで利用。

### 変更・改善
- .env の読み込みロジックを堅牢化
  - export 形式のサポート、クォート内のバックスラッシュエスケープ、行末コメントの扱いなどを実装（`_parse_env_line`）。
  - OS 環境変数を保護して `.env.local` による上書きを制御する仕組みを追加。

- 発注フローのクラッシュ耐性向上
  - `send_order` における「OrderSent 先行永続化」「broker_order_id の先保存」「OrderAccepted への後続遷移」という2相永続化パターンを導入し、クラッシュ後の状態回復（Reconciliation）を容易にした。

- ロギング・プロセス優先度設定を標準化
  - 起動時に `setup_logging` と `set_process_priority("high")` を各メインスクリプトの先頭で行うようにして運用時の一貫性を確保。

### 修正
- (初回リリースに相当するため既知のバグ修正はなし)

### セキュリティ
- (該当なし)

---

注: 本 CHANGELOG はリポジトリ内のソースコードから動作・意図を推測して作成しています。実際のリリースノートやユーザ向けドキュメントは運用方針に合わせて適宜補完してください。