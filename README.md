# KabuSys

日本株向け自動売買システムのコア部分（実行エンジン、ブローカーラッパー、リスクガード、監視、データユーティリティ等）のサンプル実装です。

> 注: 本 README はリポジトリ内のソースコードに基づき作成しています。実運用で使用する場合は必ずコードと設定を十分にレビューしてください。

## 概要

KabuSys は以下の責務を持つコンポーネントを含む自動売買フレームワークです。

- ExecutionEngine: シグナルを読み取り、発注・状態管理・リスクガードを行う
- Broker クライアント層: 実際の kabuステーション API クライアント（KabuStationClient）とテスト用のモック（MockBrokerClient）
- Order 管理: 注文の状態遷移（OrderRecord）、永続化（SQLite）および OrderManager による送信/同期/キャンセルロジック
- Reconciler: 再起動時の未確定注文の突合とポジション差分検出
- RiskManager: 3 段階（Gate1/2/3）のリスクガード（余力・重複・ポジション上限、レート制限・サーキットブレーカー、ドローダウン監視）
- Monitoring: 監視ループ（定期ポーリング）と監視 DB
- Data utilities: マーケットカレンダー管理、RSS ニュース収集など
- ユーティリティ: 環境変数ロード、設定ウィザード、設定検証 CLI など

## 主な機能一覧

- .env / .env.local の自動読み込み（OS 環境変数を優先）
- 対話式 `.env` 生成ウィザード（kabusys.config_setup）
- 起動前の設定検証ツール（kabusys.validate_config）
- ExecutionEngine によるシグナルプル型発注（発注フェーズと push ドレイン）
- MockBrokerClient によるペーパートレード / テスト実行
- Order の堅牢な状態遷移と SQLite 永続化（クラッシュ耐性を考慮）
- リコンシリエーション（OrderSent の復旧、ポジション差分検出）
- 監視ループ（SystemMonitor、監視 DB へのイベント記録）
- マーケットカレンダー管理（DuckDB を使用）と RSS ニュース収集（防御的な XML 解析・SSRF 対策）

## 要件

- Python 3.10 以上（型ヒントに `X | None` といった Python 3.10 構文を使用）
- 推奨パッケージ（一部は必須、検証や機能により任意）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（設定検証時に YAML パースを行いたい場合）
- SQLite（Python 標準ライブラリ sqlite3 を使用）
- ネットワーク接続（kabu station とやり取りする場合）

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml PyYAML
```
実際のプロジェクトでは `requirements.txt` や Poetry / PDM などで依存管理してください。

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して依存をインストールする。
2. `.env` を作成する:
   - 対話式ウィザードを使う（推奨）:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは既存の `.env` を読み込み、入力に応じて `.env` を上書きまたは作成します。
   - 手動で作成する場合はルートに `.env` を置き、必要な環境変数を設定してください（下記参照）。
3. 設定を検証する:
   ```
   python -m kabusys.validate_config
   ```
   警告も失敗扱いにする場合:
   ```
   python -m kabusys.validate_config --strict
   ```
4. 実行前に必要なディレクトリ（デフォルトでは `data/`）が作成されていることを確認してください。必要に応じて `.env` の DUCKDB_PATH / SQLITE_PATH を調整します。

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意（代表例）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト `development`
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の専用 SQLite（デフォルト: `data/paper_trading.db`）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station の base URL（デフォルト: `http://localhost:18080/kabusapi`）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（本番環境でのアラート）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill flag を自動クリアするか（0/1, 本番は 0 推奨）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

.env の自動ロード:
- OS 環境変数 > `.env.local` (override) > `.env`
- 自動ロードを無効化する: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

注意: `.env` は常に機密情報を含むため絶対に Git にコミットしないでください。

例（ダミー）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

## 使い方（主要 CLI / スクリプト）

- 設定ウィザード（対話式 `.env` 生成）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）:
  ```
  python -m kabusys.validate_config
  # 警告も FAIL 扱い:
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（本番/ペーパー両対応。KABUSYS_ENV に依存）:
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を用い、ペーパートレード用の DB (`PAPER_TRADING_SQLITE_PATH`) に記録します。
  - プロセスは `data/execution.pid`（デフォルト）に PID を書きます。
  - 停止は `data/stop_requested.flag` を作成することで検知します。
  - 起動時に `kill.flag` が残っている場合の挙動は `KILL_FLAG_CLEAR_ON_START` に依存します。

- 監視ループ起動（SystemMonitor）:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は `MONITOR_POLL_INTERVAL`（秒）で上書き可（デフォルト 60）。
  - 監視用は常に本番の sqlite_path を使用します（環境にかかわらず）。

## 実装メモ・運用上の注意

- ExecutionEngine はシグナル処理（08:50–09:10）と push ドレイン（09:10–15:30）の２相で動作します（テスト時は直接メソッド呼び出し可）。
- OrderManager は送信前に OrderSent を永続化し、ブローカー呼び出しと合わせた二相永続化でクラッシュ耐性を高めています。
- Reconciler により再起動時に OrderSent の状態をブローカー側と同期して回復を試みます。
- RiskManager は Gate1/2/3 を通じて重複・余力・ポジション上限やレート制限、ドローダウン等を防ぎます。サーキットブレーカーの設定値は RiskConfig で調整可能です。
- 本番（KABUSYS_ENV=live）設定では追加の警告/チェックが行われます。LINE 通知などの設定漏れに注意してください。

## ディレクトリ構成（主要ファイル）

リポジトリのルートに `src/kabusys` がある想定です。主なファイルと役割は以下の通り。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数読み込み・Settings（型安全なアクセサ）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（メイン）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - execution/
    - __init__.py — execution パッケージ公開 API
    - broker_api.py — BrokerAPI の Protocol / データモデル / 例外 / ファクトリ
    - kabu_client.py — kabu station REST API 実装（httpx）
    - mock_client.py — MockBrokerClient（テスト用）
    - broker_factory.py — Settings に基づくブローカーファクトリ
    - order_record.py — 注文状態モデルと状態遷移ロジック
    - order_repository.py — SQLite を使った永続化層
    - order_manager.py — 発注フロー（create/send/sync/cancel）
    - reconciliation.py — 再起動時の突合（Reconciler）
    - execution_engine.py — ExecutionEngine（シグナル処理 / push ドレイン / kill switch）
    - risk_manager.py — 3 段階リスクガード
    - その他: order_*、reconciler など
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB 連携）
    - news_collector.py — RSS ニュース収集（defusedxml 等で安全に解析）
    - jquants_client.py — J-Quants クライアント（別途実装の想定）
  - monitoring/
    - monitoring_db.py — 監視 DB 初期化 / ログ書き込み（実装ファイル）
    - system_monitor.py — システム監視ロジック（実装ファイル）
  - utils/
    - logging_setup.py — ロギング設定ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ

（上記は主要ファイルの抜粋です。細かいユーティリティや補助モジュールも含まれます。）

## 開発／テストのヒント

- MockBrokerClient を使えば kabu station の稼働無しに発注フローの単体テストが可能です。
- settings.paper_fill_mode を変更して発注の fill 動作（instant/partial/never/reject）を切り替えられます。
- ExecutionEngine の run_session は内部メソッド（_process_signals, _drain_push_queue）を直接呼べる設計のため、単体テストで時刻依存を回避できます。
- SQLite / DuckDB の初期化関数（init_monitoring_db, init_orders_db）はスクリプト起動時に呼ばれるため、ローカルで事前に接続先パスを確認してください。

## ライセンス・注意事項

このコードはサンプル実装であり、実際の金銭を扱うシステムで使用する場合は十分な監査・テスト・セキュリティ対策が必要です。本 README は実運用の保証をするものではありません。

---

問題や追加で README に含めたい情報（例: 実行例ログ、設定例、CI／デプロイ手順など）があれば教えてください。必要に応じて README を拡張します。