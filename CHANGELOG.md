# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-04-23

### Added
- 基本パッケージ情報
  - パッケージバージョンを設定: `__version__ = "0.1.0"`。

- 環境設定 / 設定読み込み
  - `kabusys.config` モジュールを追加。
    - `Settings` クラスにより環境変数からアプリケーション設定を取得する統一 API を提供（J-Quants トークン、kabu API パスワード、DB パス、PID/KILL フラグ等）。
    - `.env` の自動読み込み機構を導入（プロジェクトルート検出: `.git` / `pyproject.toml` を探索）。優先順位は OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env パーサは `export KEY=val`、クォート（シングル/ダブル）およびバックスラッシュエスケープ、インラインコメント処理をサポート。
    - `PAPER_FILL_MODE` 等、いくつかの設定値に対するバリデーションを実装（不正値は例外を raise）。

- .env 対話式ウィザード
  - `kabusys.config_setup` CLI を追加。対話式で `.env` の初期作成・更新を支援。
    - 秘匿項目はマスク表示、選択肢・デフォルト表示、キャンセル時の挙動、書き込みテンプレート（セクション分け）を提供。
    - 生成された `.env` に関する注意書き（絶対に Git にコミットしない）を明記。

- 設定検証ツール
  - `kabusys.validate_config` CLI を追加。
    - 必須環境変数の存在チェック（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）とプレースホルダ検出。
    - `KABUSYS_ENV` / `LOG_LEVEL` 値の妥当性検証。
    - DB パス（`DUCKDB_PATH`, `SQLITE_PATH`）の親ディレクトリ存在確認。
    - `config/*.yaml` ファイルの存在確認と、PyYAML が利用可能な場合はパース検証（未インストール時は警告でスキップ）。
    - `KABUSYS_ENV=live` 時の本番ガード（LINE 関連設定、KILL_FLAG_CLEAR_ON_START の警告など）。
    - `--strict` フラグで警告を FAIL として扱う挙動を追加。戻りコードで FAIL/OK を判定。

- 実行スクリプト（監視・運転）
  - `kabusys.run_monitoring` を追加。
    - `SystemMonitor` のポーリングループを起動。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視 DB 初期化（SQLite）と DuckDB 接続を行う。停止フラグ検出・例外処理・リソースクローズを実装。
  - `kabusys.run_execution` を追加。
    - `ExecutionEngine` の起動ラッパー。プロセス優先度設定、PID 書き出し、stop フラグ検出、paper_trading 環境時は専用 SQLite を使用する分離を実装。

- 発注エンジン / 注文管理
  - `kabusys.execution.execution_engine` を追加。
    - Signal-queue ベースの発注フロー（シグナル処理時間帯、push ドレインループ、WebSocket スレッドの起動/スキップ判定）。
    - 起動時の Reconciliation 実行、kill.flag の扱い（`KILL_FLAG_CLEAR_ON_START` に基づくクリア判定）と PID 管理。
    - シグナル処理における Gate 1/2（シグナル/実行レベルのリスクチェック）、Gate 3（ドローダウン監視）ロジックの統合。
    - 発注後の position_entries 更新（DuckDB）や監視 DB へのイベントログ記録（レイテンシ等）。
    - `kill_switch()` による全 active 注文のキャンセル・停止手順を実装。

  - `kabusys.execution.order_record` を追加。
    - OrderState 列挙と明確な許可遷移テーブルを実装。`OrderRecord.transition_to()` による遷移検証、optional フィールド更新、`updated_at` の自動更新を提供。
    - 不正遷移時に `InvalidStateTransitionError` を raise。

  - `kabusys.execution.order_manager` を追加。
    - 発注ワークフローの外向け API（`create_order`, `send_order`, `sync_order`, `cancel_order`）を実装。
    - `create_order` は同一 signal_id の active 注文検出（メモリ／DB 両面）し、重複時は `DuplicateOrderError` を raise。DB のユニーク制約違反を DuplicateError に変換。
    - `send_order` はクラッシュ安全性を考慮した 2 相永続化パターン（まず OrderSent を DB に保存 → broker 呼び出し → broker_order_id を保存 → OrderAccepted へ遷移）を実装。`OrderRejectedError`、`OrderSentPendingError` の扱いを明確化。
    - `sync_order` は broker 側ステータスを取得してローカル状態を同期。部分約定更新は idempotent にフィールド更新する実装。
    - `cancel_order` はキャンセル不可状態のチェックを行い、broker API 呼び出し後に Cancelled に遷移。

- broker クライアント（kabuステーション）
  - `kabusys.execution.kabu_client` を追加。
    - `KabuStationClient` の同期 HTTP 実装（httpx 使用）。内部でトークン取得/キャッシュを行い、401 受信時は自動でトークン再取得して再試行。
    - レスポンス JSON パース失敗やネットワーク/タイムアウトエラーは専用例外に変換。HTTP 429 は `RateLimitError` にマッピング。将来の async 化を意識した設計。
    - WebSocket（push）経由の通知を受けるための `stream_push` 呼び出し（broker 側実装があれば利用）を想定。

- その他ユーティリティ
  - プロセス優先度設定ユーティリティ、ロギング初期化呼び出し箇所（`setup_logging`）を各起動スクリプトで使用。
  - 監視 DB 初期化 (`init_monitoring_db`) の呼び出しを追加し、監視用テーブルの存在保証を行う（冪等に実行可能）。

### Changed
- 初期リリースのため該当なし（新規追加中心）。

### Fixed
- .env パーサの堅牢化
  - コメントやクォート付き値、エスケープシーケンスに対する正しいパース処理を実装し、実運用での .env 読み込みの信頼性を向上。

### Security / Notes
- 生成される `.env` ファイルは機密情報を含むため、必ず .gitignore 等で管理し Git にコミットしないことを明記。
- `validate_config` や `config_setup` の導入により、本番環境（KABUSYS_ENV=live）での設定ミスを起動前に検出しやすくなっています。

---

注: 本 CHANGELOG はコードベースから推測して作成したものであり、実際のコミット履歴やリリース手順に基づくものではありません。実際の変更履歴（コミット単位）を残す場合は、Git の履歴を元に項目を補足してください。