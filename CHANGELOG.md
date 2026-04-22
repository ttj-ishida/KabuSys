# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
主にコードベースから推測できる機能追加・振る舞いを記載しています。

## [Unreleased]

- 現時点での保留事項 / 追加予定の検討点はありません。

## [0.1.0] - 2026-04-22

### Added
- 基本パッケージ情報を追加
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義。

- 環境設定・読み込み機能
  - Settings クラスを追加し、環境変数からアプリケーション設定を取得できるようにした。
  - .env 自動読み込み機能を追加（優先順位: OS 環境変数 > .env.local > .env）。
  - 環境変数ファイルのパース処理を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 環境読み込みの自動実行を無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 必須環境変数未設定時に例外を送出する `_require()` を提供。

- 対話式設定ウィザード
  - `kabusys.config_setup` モジュールに対話式 CLI を実装し、`.env` の初期作成・更新を支援。
  - 各項目の入力・既存値の再利用・シークレット項目のマスク表示・選択肢サポートを実装。
  - `.env` 書き込み用テンプレートを提供（書式コメント付き）。Git に .env を含めないよう注記。

- 設定検証 CLI
  - `kabusys.validate_config` に起動前チェック CLI を実装。
  - 必須/任意環境変数の有無、プレースホルダ値チェック、KABUSYS_ENV / LOG_LEVEL の妥当性判定、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML がない場合はスキップ）などを実行。
  - `--strict` オプションを追加（警告を FAIL 扱いにして exit(1)）。
  - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 設定・KILL_FLAG_CLEAR_ON_START 等）を実装。

- 実行スクリプト
  - `run_execution.py` を追加し、ExecutionEngine を起動するエントリポイントを実装。
    - paper_trading 環境時は paper 用 SQLite を使用して本番 DB と分離。
    - PID ファイル出力、停止フラグ検出、プロセス優先度設定、スレッドでの実行をサポート。
  - `run_monitoring.py` を追加し、SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で間隔上書き可能。
    - Monitoring はすべての環境で本番 sqlite_path を使用する挙動。

- ExecutionEngine と発注ロジック
  - `ExecutionEngine` を実装。セッションの流れ（シグナル処理 / push ドレイン / セッション終了）を管理。
  - シグナル読込は DuckDB を参照（signals と portfolio_targets を JOIN）。
  - 発注フローにおける Gate1（シグナルレベル）、Gate2（エグゼキューションレベル、レート制御、サーキットブレーカー）、Gate3（ドローダウン監視）を実装。
  - size_multiplier 適用や BUY/SELL の扱い差分を反映。
  - WebSocket push（kabu push）を受けて同期処理を行うワーカースレッドを実装。broker が `stream_push` を持たない場合はスキップ。
  - kill_switch 機能を実装: 全 active 注文のキャンセルとループ停止。

- 注文状態管理
  - `OrderRecord` と `OrderState` を実装し、状態遷移の検証とタイムスタンプ更新を行う純粋ビジネスロジックを提供。
  - 許可遷移テーブルを定義し、不正遷移時は `InvalidStateTransitionError` を発生させる。
  - `OrderManager` を実装し、signal_queue からの注文作成、発注、同期、キャンセルの高レベル API を提供。
    - 同一 signal_id の重複注文検出（DuplicateOrderError）。
    - 発注に対する「2 相永続化」戦略を採用（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted に遷移）。
    - `OrderSentPendingError` を扱い、pending の場合は broker_order_id を保存した上で例外を伝播する設計。
    - sync_order にて broker の状態を取得してローカル状態を更新（部分約定の数量/平均価格更新含む）。
    - cancel_order は終端状態では拒否し、必要なら broker API を呼んでから Cancelled に遷移。

- Broker クライアント（kabu）
  - `KabuStationClient` を実装（httpx を使用した同期 REST クライアント）。
  - トークン管理（遅延取得、401 時の再取得・リトライ）を内包。
  - HTTP ステータスに基づいたエラー変換（401/429/5xx を適切に扱う）。429 は RateLimitError にマップ。
  - kabu ステータスコードを内部ステータス文字列にマッピング（open/partial/filled/cancelled/rejected）。

- DB 初期化・監視
  - monitoring 用の DB 初期化（`init_monitoring_db`）呼び出しを run_execution / run_monitoring で行い、監視テーブルの存在を保証。
  - DuckDB 接続を導入し、position_entries などへの記録（発注後に約定予定日を記録）を行う処理を追加。
  - 発注イベントの監視 DB へのログ記録（latency 等）を実装するフックを提供。

- ロギング・プロセス設定ユーティリティ
  - プロセス優先度設定ユーティリティ呼び出し（High 設定）とアプリ別ロギング初期化の呼び出しを導入。

### Changed
- 設定周りのバリデーションを強化
  - Settings のプロパティで KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の妥当性チェックを行い、不正値時に ValueError を送出するようにした。
  - 環境変数のデフォルト取り扱い（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）を明確化。

- ExecutionEngine の DB 周りの挙動
  - paper_trading 時の SQLite を本番 DB と分離（settings.paper_sqlite_path を使用）する仕様に変更。

### Fixed
- （明示的なバグ修正はソースから直接推測できないため記載なし）

### Security
- .env ファイルは絶対に Git にコミットしない旨を .env テンプレートに明記。
- シークレット値は対話表示でマスクされるように実装。

---

注:
- 上記はコード内容から推測して記載した CHANGELOG です。実際のコミット履歴や意図とは差異がある可能性があります。必要があれば、より詳細に項目を分割するか、日付/バージョンの調整を行います。