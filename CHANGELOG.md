# Changelog

すべての重要な変更をここに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

全般的な注意:
- このリリースはパッケージの初期公開版（0.1.0）に相当する機能群をコードベースから推測してまとめたものです。
- CLI ツール、設定読み込み・検証、発注エンジン、監視プロセス、kabuステーション API クライアント、注文状態機構などを含みます。

## [0.1.0] - 2026-04-23

### Added
- 基本アプリケーション情報
  - パッケージバージョン定義: `__version__ = "0.1.0"` を追加。

- 設定管理
  - Settings クラスを実装し、環境変数からアプリケーション設定を取得する API を提供（例: `settings.jquants_refresh_token` 等）。
  - 自動 `.env` ロード機能を実装（プロジェクトルートの検出: `.git` または `pyproject.toml` を基準）。
  - `.env` パーサを実装:
    - export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの取り扱いをサポート。
  - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 必須環境変数取得時に未設定なら `ValueError` を発生させる `_require()` を実装。
  - Paper Trading 用の分離された SQLite パス（`PAPER_TRADING_SQLITE_PATH`）と `paper_fill_mode`（値検証）をサポート。
  - 各種監視しきい値（CPU/MEM/DISK）や PID / kill flag のパス、`KILL_FLAG_CLEAR_ON_START` 等の設定を提供。

- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装し、`.env` の初期作成・更新を支援。
  - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DBパス, LINE 通知設定, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）を含む。
  - 既存 `.env` の読み込み、入力のマスク（シークレット項目）、選択肢・デフォルトの提示、保存確認を実装。
  - `.env` ファイル生成時のテンプレート（コメント付き）を書き出す `_write_env()` を実装。

- 設定検証 CLI
  - `kabusys.validate_config` を実装。起動前に環境変数や `config/*.yaml` の問題を検出。
  - 必須環境変数チェック、プレースホルダ値の警告、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性チェック、DB パス親ディレクトリ存在チェック、`config/*.yaml` ファイル存在確認と（PyYAML があれば）パース検証を行う。
  - `--strict` オプションを実装（警告も敗北扱いにして exit(1)）。
  - `KABUSYS_ENV=live` の場合は追加ガード（LINE 通知未設定や kill flag 自動クリア設定の警告）を実施。
  - PyYAML が未インストールの場合は YAML 内容検証をスキップして警告を出力。

- 実行プロセス起動スクリプト
  - `run_execution`:
    - ExecutionEngine の起動スクリプトを実装（プロセス優先度設定、DB 接続、paper_trading 用 DB 分離）。
    - ストップフラグ、PID 書き込み、スレッド管理、クリーン終了処理を実装。
  - `run_monitoring`:
    - SystemMonitor のポーリングループ起動スクリプトを実装（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能）。
    - 監視用 DB 初期化、duckdb 接続、停止フラグ検知や例外ハンドリングを実装。

- 注文周り（Execution）
  - 注文状態機構（OrderRecord / OrderState）を実装:
    - 明確な状態列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許容される状態遷移マップと、不正遷移時に `InvalidStateTransitionError` を投げる仕組み。
    - `transition_to()` により状態変更とオプションフィールド（broker_order_id, filled_qty, avg_fill_price, error_message）の更新を行う。
  - OrderManager を実装:
    - `create_order`（signal ごとの重複チェック、UUID 付与、DB 保存、DuplicateOrderError の扱い）。
    - `send_order`：二相永続化パターンを採用（OrderSent を先にコミット → ブローカー送信 → broker_order_id を永続化 → OrderAccepted へ遷移）。OrderRejected / OrderSentPending の扱いを含む。
    - `sync_order`：broker 側のステータス取得により DB を同期（部分約定の増分更新をサポート）。Reconciliation 対応。
    - `cancel_order`：キャンセル不可能な状態の検出と Broker API 呼び出し、Cancelled への遷移。
    - Pending（OrderSent のまま）やクラッシュ回復を想定した設計（Reconciliation で回復可能にするため broker_order_id を先に保存など）。

- ExecutionEngine（発注エンジン）
  - シグナル読み込み（DuckDB）→ Gate1 (signal-level) / Gate2 (execution-level) を通じて発注。
  - Gate2 のレート制限処理（リトライ最大3回、Circuit Breaker の扱い）。
  - 発注成功/保留/失敗のログとモニタリング DB への記録（latency 等）。
  - position_entries の更新ロジック（buy / sell の処理差分、fill_date を翌営業日で記録）。
  - WebSocket push を受けての drain 処理（sync_order 呼び出し）と Gate3（ドローダウン監視）による kill_switch 発動。
  - kill_switch により全 active 注文をキャンセルし、ループ停止。外部からの停止は `stop()` で行える。
  - セッション制御（signal_send_start / signal_send_end / market_close）に基づく処理フロー。

- Broker クライアント（kabu station）
  - `KabuStationClient` を実装（同期 httpx を使用）。
  - トークン取得の遅延初期化と 401 に対する再取得リトライを実装。
  - レスポンス JSON パース時の例外変換、HTTP ステータスごとのエラー分類（401, 429, 5xx など）を実装。
  - kabu ステーションのステータスコードを内部状態文字列にマッピングするマップを追加。

- モニタリング
  - monitoring 用 DB 初期化ユーティリティ（init_monitoring_db）を利用する統合。
  - SystemMonitor / 監視ループを起動するランナーを提供。

### Changed
- なし（初期リリース相当の実装群のまとめ）。

### Fixed
- なし（この CHANGELOG はコードから推測した初期状態の記載です）。

### Security
- `.env` は絶対に Git にコミットしない旨のテンプレートコメントを `.env` 生成で明記（config_setup の書き出し時）。

### Notes / Implementation details
- データベース分離: paper_trading 環境では monitoring/実行用の SQLite を本番と分離している（settings.paper_sqlite_path を使用）。
- 冪等性とクラッシュ安全性: send_order の二相永続化や Reconciler による同期設計は、クラッシュ後の整合性回復を意図している。
- 設定検証: validate_config は PyYAML が存在する場合に限り config/*.yaml のパース検証を行う。未インストール時は警告でスキップ。
- 環境読み込みの優先順位: OS 環境 > .env.local > .env（ただし OS 環境は protected として .env.local でも上書きされない）。
- `.env` のパーシングは実運用でありがちなパターン（export、クォート、エスケープ、行末コメント）に対応。

もしリリースノートに追記したい項目（例えば既知の制限、互換性注意点、将来的な改善予定など）があれば教えてください。必要に応じて Unreleased セクションや次バージョンの目標を追加します。