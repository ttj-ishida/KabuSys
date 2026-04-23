# KabuSys

日本株自動売買システムのコアライブラリ（README）。このリポジトリは実行エンジン、監視、設定管理、ブローカークライアント等の主要コンポーネントを含みます。

## プロジェクト概要
KabuSys は日本株の自動売買を行うための内部ライブラリ群です。  
主な役割は以下のとおりです。

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカー抽象化層（kabu station 実装 / モック）
- 発注の状態管理（OrderRecord / OrderManager / OrderRepository）
- 再起動時のリコンシリエーション（Reconciler）
- リスクガード（3段階：Gate1/Gate2/Gate3）
- 監視ループ（SystemMonitor を用いたポーリング）
- 環境設定ウィザード・設定検証ツール
- データ処理（マーケットカレンダー、ニュース収集 等）

設計方針として、DBアクセスとビジネスロジックを分離し、クラッシュ時の安全性（永続化の順序、リコンシリエーション）を重視しています。

---

## 主な機能一覧
- 環境設定ウィザード（.env の対話的生成 / 更新）
- 起動前設定検証（必須環境変数、YAML 設定ファイル等のチェック）
- ExecutionEngine（シグナルの読み取り → 発注 → Push ドレイン）
- Mock ブローカー（paper_trading / development 用のテスト用実装）
- KabuStationClient（kabu station REST API の同期クライアント）
- Order の状態遷移モデルと SQLite による永続化
- リスク管理：余力・重複・ポジション上限、レート制限、サーキットブレーカー、ドローダウン監視
- 監視プロセス（監視 DB にログ書き込み、システムメトリクス監視）
- データモジュール：マーケットカレンダー管理、ニュース収集（RSS）

---

## セットアップ手順

1. リポジトリをクローンして依存をインストールします（仮想環境推奨）。

   例（pip）:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb httpx websocket-client defusedxml pyyaml
   ```

   ※ 実際の依存は用途により変わるため、requirements ファイルがある場合はそちらを使用してください。

2. プロジェクトルートに `.env` を作成します。自動で生成・更新するにはウィザードを使います（下記参照）。

3. データディレクトリ（デフォルト `data/`）を作成しておくと良いです：
   ```
   mkdir -p data
   ```

4. DB/設定ファイルの準備：
   - DuckDB のデータファイルや SQLite の監視 DB はデフォルトパスを持ちます（後述）。
   - `config/*.yaml` が必要な場合はプロジェクト固有の生成スクリプト（例: `python scripts/generate_config.py`）を利用してください（リポジトリにある場合）。

注意: `.env` は機密情報を含むため絶対に Git にコミットしないでください（config_setup も注意喚起を出します）。

---

## 環境変数（主なもの）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意/推奨（主な一覧）:
- KABUSYS_ENV — 実行環境（development | paper_trading | live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番での通知設定（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill flag を自動クリアするか（0/1。デフォルト 0）

設定は `.env` / `.env.local` / OS 環境変数から読み込まれます。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能です。

---

## 使い方（コマンド）

- 環境設定ウィザード（.env を対話的に作成/更新）:
  ```
  python -m kabusys.config_setup
  ```
  実行後 `.env` に書き込むかどうかを確認するプロンプトが出ます。

- 設定検証（起動前チェック）:
  ```
  python -m kabusys.validate_config
  ```
  警告を FAIL にしたい場合:
  ```
  python -m kabusys.validate_config --strict
  ```

- 本番 / 実行エンジン起動（ExecutionEngine）:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading または development の場合はモックブローカーを使用します。
  - 実行前に `.env` を正しく設定し、必要なら `data/` 配下のファイル（pid, flag）を確認してください。
  - 停止は `data/stop_requested.flag` を作成することで優雅に停止できます（スクリプト内で検出）。

- 監視ループ起動（SystemMonitor をポーリング）:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視 DB は `SQLITE_PATH` を使用します（監視は常に実環境の sqlite_path を参照します）。

- テスト・開発:
  - MockBrokerClient を使ってローカルで発注フローを検証できます（paper_trading モード）。
  - ExecutionEngine の単体テストなどでは内部メソッド（_process_signals, _drain_push_queue）を直接呼ぶ方が簡単です。

---

## 注意事項（運用）
- 本番環境では `KABUSYS_ENV=live` を設定します。validate_config が警告を出します（警告は危険信号）。
- `kill.flag` / `KILL_FLAG_CLEAR_ON_START`:
  - `kill.flag`（デフォルト: data/kill.flag）は起動中の kill switch 管理に使用します。存在する場合は起動拒否するか（clear_on_start が 0 の場合）、自動でクリアして起動するか（1 の場合）を制御します。
- PID ファイル（既定: data/execution.pid 等）は起動時に書き込まれます。複数インスタンスの衝突に注意してください。
- `.env` を Git に入れないでください（機密情報）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ情報（バージョン）
  - config.py — 環境変数・設定管理（自動 .env 読み込み、Settings クラス）
  - config_setup.py — 環境設定ウィザード（対話式 .env 生成）
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — 監視ループ起動スクリプト
  - execution/
    - __init__.py — execution パッケージの主要エクスポート
    - broker_api.py — ブローカー API の Protocol / データモデル / ファクトリ
    - broker_factory.py — Settings に応じたブローカー生成
    - kabu_client.py — kabu station REST クライアント実装
    - mock_client.py — テスト用 MockBrokerClient
    - order_record.py — 注文状態モデル（OrderRecord）と遷移検証
    - order_repository.py — SQLite による永続化層（orders テーブル）
    - order_manager.py — 発注フロー API（create/send/sync/cancel）
    - execution_engine.py — ExecutionEngine（セッション管理、WebSocket、発注ループ）
    - reconciler.py — 起動時リコンシリエーション（OrderSent 照合、ポジション差分）
    - risk_manager.py — 3段階リスクガード（Gate1/2/3）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB ベース）
    - news_collector.py — RSS ニュース収集（正規化・SSRF対策等）
    - (その他データ関連モジュールを想定)
  - monitoring/
    - monitoring_db.py — 監視 DB 初期化・ログ関係（参照されるがこの README では略）
    - system_monitor.py — システム監視ロジック（参照されるがここでは略）
  - utils/
    - logging_setup.py — ロギング初期化ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ

（上記はリポジトリ内の主要ファイルと役割を抜粋した一覧です。詳細はソースコードを参照してください。）

---

## 参考コマンド例

- .env をウィザードで作る:
  ```
  python -m kabusys.config_setup
  ```

- 設定をチェック:
  ```
  python -m kabusys.validate_config --strict
  ```

- ペーパートレードで実行（前提：.env に KABUSYS_ENV=paper_trading 等を設定）:
  ```
  python -m kabusys.run_execution
  ```

- 監視ループを起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

---

## 開発者向けメモ
- Settings は `.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Order の状態遷移は OrderRecord.transition_to で検証され、不正遷移は例外になります。
- ExecutionEngine はクラッシュ時の整合性を考慮し、OrderSent の永続化 → ブローカー呼出し → broker_order_id 永続化 → OrderAccepted 更新 のような二相的永続化を行います。
- MockBrokerClient はテストに便利な機能（fill_mode, fill_order の手動操作）を提供します。

---

この README はコードベースの主要点を簡潔にまとめたものです。詳細な API や内部挙動はソースコード（各モジュールの docstring）を参照してください。必要であれば、README に実運用手順（デプロイ、監視設定、バックアップ等）を追加します。