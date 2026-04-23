# Changelog

すべての重要な変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog のガイドラインに従います。
慣習的なセマンティックバージョニングを使用します。

## [Unreleased]

- なし（初回リリース以外の未リリース変更はありません）

## [0.1.0] - 2026-04-23

初回公開リリース。本リポジトリに含まれる主要機能・設計決定はソースコードから推測して以下の通りです。

### Added
- 全体
  - KabuSys: 日本株自動売買システムの基盤を実装。
  - パッケージバージョン: `__version__ = "0.1.0"` を設定。

- 設定 / 環境変数管理
  - Settings クラス実装（kabusys.config）
    - 環境変数から各種設定を取得する一元インターフェースを提供（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、監視閾値、PID/KILL フラグパス等）。
    - env 値の妥当性チェック（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。不正値は ValueError を発生。
    - paper_trading 向けの分離された SQLite パス（PAPER_TRADING_SQLITE_PATH）と paper_fill_mode のサポート。
  - .env 自動読み込み
    - プロジェクトルート（.git または pyproject.toml を起点）から `.env` と `.env.local` を自動で読み込み（OS 環境変数優先、.env.local は上書き）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサー（export 形式、クォート、バックスラッシュエスケープ、コメント処理に対応）。
  - .env 読み込み時の保護機構: OS 環境変数キーを protected として上書きを制御。

- 設定ウィザード CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` の初期作成・更新を支援。
    - 秘匿項目は表示をマスク。選択肢/デフォルト/説明を提供。
    - .env の読み書き機能（テンプレートヘッダを含む整形出力）。
    - 中断/キャンセル対応。

- 設定検証 CLI
  - `kabusys.validate_config`：起動前に `.env` と `config/*.yaml` の問題を検出する CLI。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（開発/ペーパー/本番判定、本番時は警告）。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）の親ディレクトリ存在チェック（存在しない場合は警告）。
    - config/*.yaml の存在確認と（PyYAML がインストールされている場合の）パース検証。PyYAML 未インストール時は検証スキップ警告。
    - 本番環境向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定検出）。
    - `--strict` オプションで警告も失敗（exit code 1）として扱う。

- 実行 / 監視ランナー
  - `run_execution`：ExecutionEngine 起動スクリプト
    - プロセス優先度を設定し、PID ファイル・停止フラグを管理。
    - paper_trading モード時は専用の SQLite（本番 DB と完全分離）を使用。
    - DuckDB 接続と監視 DB 初期化（init_monitoring_db）。
  - `run_monitoring`：SystemMonitor ポーリングループ起動スクリプト
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（デフォルト 60 秒）を上書き可能。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。

- Execution エンジン本体
  - `ExecutionEngine` 実装
    - シグナル処理（例: 8:50-9:10）と WebSocket push ドレインループ（9:10-15:30）を備えるセッション実行フロー。
    - Signal 読み取り（DuckDB）、Gate1/Gate2（シグナル・実行レベルのリスク検査）、発注、Gate3（ドローダウン監視）による kill_switch 発動。
    - WebSocket ワーカースレッドから push を受け付け `_push_queue` で非同期処理。
    - PID / kill.flag の管理、起動時リコンシリエーションの呼び出し（Reconciler）。

- 注文関連（発注ロジック）
  - `OrderRecord`—状態遷移とモデル
    - 状態列挙 OrderState と許可遷移表を実装。InvalidStateTransitionError を導入。
    - transition_to() により状態遷移と関連フィールド（broker_order_id, filled_qty, avg_fill_price, error_message）を安全に更新。
  - `OrderManager`
    - create_order(): signal_id 単位での重複検知（DB 部分ユニーク制約を含む）と DuplicateOrderError。
    - send_order(): 2相永続化を考慮した堅牢な発注フロー（OrderSent を先に永続化 → broker 呼び出し → broker_order_id 保存 → OrderAccepted）と OrderSentPendingError 取り扱い。
    - sync_order(): broker の状態取得による同期処理（部分約定の進行検知を含む）。
    - cancel_order(): キャンセル不可能状態のチェック、broker cancel 呼び出しと Cancelled への遷移。
    - 発注フロー中の例外ハンドリング（リトライ・レート制限・サーキットブレーカーなどのリスク管理との統合）。

- ブローカークライアント
  - `KabuStationClient`（kabu station REST API 実装）
    - httpx 同期クライアントによる同期 API 呼び出し実装。
    - トークン管理: トークンの遅延取得・401 時の自動再取得と1回リトライ。
    - レスポンス JSON パース失敗 / ネットワーク / タイムアウトを BrokerAPIError に変換。
    - 429 を RateLimitError にマッピング。
    - kabu station の注文状態コードを内部ステータスにマッピング（open/partial/filled/cancelled/rejected）。
    - 将来的な WebSocket / push 受信（stream_push の存在を想定）による通知処理に対応。

- リスク管理 / モニタリング連携
  - RiskManager / RiskConfig による Gate 判定（rate limit / circuit breaker / ドローダウン閾値など）。
  - 発注時の成功/失敗メトリクスを MonitoringDB に記録するフックを追加（監視 DB 書き込みの例外は警告で扱う）。

- その他ユーティリティ
  - process_priority 設定ユーティリティ（優先度を "high" に設定する呼び出しを使用）。
  - ロギングセットアップ helper の利用（setup_logging）。
  - stop_requested.flag / kill.flag / pid ファイルの取り扱い。

### Changed
- 初回リリースのため履歴無し（初回実装として上記機能を追加）。

### Fixed
- 初回リリースのため履歴無し。

### Security
- 特記事項無し

---

注意:
- 実行には外部依存ライブラリ（例: httpx, websocket, duckdb, sqlite3, PyYAML（任意））が必要です。PyYAML が無い場合は validate_config の YAML 内容検証がスキップされ、警告が出ます。
- `.env` は絶対に Git にコミットしないでください（config_setup のヘッダにも注意喚起あり）。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値など慎重に確認してください（validate_config が警告を出します）。

（この CHANGELOG はソースコードの構造・コメント・実装から推測して作成しています。実際のリリースノート作成時はリリース日や変更セットを正確に反映してください。）