# Changelog

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- - 

## [0.1.0] - 2026-04-23

### Added
- パッケージ初期リリース。
- 環境・設定管理
  - .env ファイルの自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml で探索）。
  - .env のパース機能を実装。`export KEY=val`、シングル/ダブルクォート内のエスケープ、行内コメント処理等に対応。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを導入し、アプリケーション設定プロパティを提供（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、各種閾値、環境・ログレベル 等）。
  - 設定値の妥当性チェック（`KABUSYS_ENV` / `LOG_LEVEL` / `PAPER_FILL_MODE` 等）を実施し、不正値では例外を送出。

- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装し、.env ファイルの初期作成・更新を支援。
  - 作成される .env のテンプレート（項目: KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 設定, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）。
  - 既存 .env の読み込み・再利用、シークレット項目のマスク表示、入力キャンセル処理をサポート。

- 設定検証 CLI
  - `kabusys.validate_config` に設定検証 CLI を実装。
  - 必須環境変数の未設定検出、プレースホルダ値の警告、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性チェック、DB パスの親ディレクトリ存在チェックを実施。
  - `config/*.yaml` の存在確認と（PyYAML が存在する場合）パース検証。PyYAML 未インストール時は警告してスキップ。
  - `--strict` オプションで警告を FAIL（exit code 1）として扱う。
  - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険値検出など）。

- 実行ランナー
  - `run_execution.py`：ExecutionEngine 起動用スクリプトを追加。プロセス優先度設定、PID ファイル管理、stop フラグ検出、DB 接続（paper_trading 環境時の専用 SQLite 分離）を行う。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。

- 発注関連コア
  - OrderRecord / OrderState：注文状態モデルと状態遷移ロジックを実装（遷移許可表を明示）。不正遷移は例外を送出。
  - OrderManager：OrderRecord と OrderRepository を組み合わせた外向き API を実装。
    - create_order：signal_id の重複チェック（DB 制約違反時も DuplicateOrderError に変換する処理を含む）。
    - send_order：OrderCreated → OrderSent → broker 呼び出し → broker_order_id 永続化 → OrderAccepted への遷移、OrderRejected/OrderSentPending のハンドリング、クラッシュ安全性を考慮した 2 相永続化パターンを採用。
    - sync_order：broker 側のステータスと同期し、状態遷移や部分約定情報の更新を行う。
    - cancel_order：キャンセル不可能な状態の検査、broker API 呼び出し、Cancelled への遷移。
  - ExecutionEngine：Signal Queue Pull 型発注エンジンを実装。
    - シグナル処理ループ（デイリー処理の時間帯制御: signal_send_start / signal_send_end / market_close）。
    - Gate1/2/3 のリスクチェック、rate limit リトライ、Circuit Breaker のハンドリング、kill_switch の発動ロジック。
    - WebSocket push の受信・ドレイン処理（push で受け取った注文を sync）、position_entries への書き込み（DuckDB）等。
    - Reconciler による起動時リコンシリエーションサポート。
    - 発注時の監視 DB へのイベント記録インフラ（監視 DB が設定されている場合）。

- ブローカークライアント
  - KabuStationClient を実装（httpx を使用した同期 REST クライアント、websocket 受信サポート）。
  - API トークンの自動取得・遅延初期化、401 時のトークン再取得とリトライ、429 レスポンスでの RateLimitError 投げ分け、ネットワーク/タイムアウト例外の BrokerAPIError への統一変換。

- ユーティリティ
  - 設定読み込み/ログ設定・プロセス優先度設定ユーティリティ呼び出しを実装（run_* スクリプトで利用）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes / Migration
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも明記）。
- validate_config 実行推奨フロー:
  1. python -m kabusys.config_setup で .env を作成
  2. python -m kabusys.validate_config で設定検証
- 本番環境では KABUSYS_ENV=live の設定と LINE 通知設定、KILL_FLAG_CLEAR_ON_START の値を特に注意してください。KILL_FLAG_CLEAR_ON_START=1 は本番で危険です。
- PyYAML がインストールされていない場合、config/*.yaml のパース検証はスキップされ、警告が出ます。YAML の構文チェックを行いたい場合は PyYAML を追加でインストールしてください。

### Known issues
- validate_config は PyYAML がないと YAML の構文検査を行いません（警告のみ）。CI 等で厳密検査する場合は PyYAML の導入を推奨します。
- KabuStationClient は同期 httpx.Client を使用しており、将来的な async 対応は httpx.AsyncClient への切り替えが必要です。

---

開発上の詳細や実装方針はソースコード内のドキュメント文字列（docstring）を参照してください。