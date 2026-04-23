# KabuSys

日本株自動売買システムの一部（ライブラリおよび起動スクリプト群）。  
このリポジトリは発注エンジン・リスク管理・リコンシリエーション・監視・データ処理（カレンダー・ニュース収集）などのコンポーネントを含みます。開発／ペーパートレード／本番運用を想定した設計になっています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（代表的なコマンド）
- 環境変数（主要な設定）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動発注エンジンを構成するモジュール群です。主な設計要件は次のとおりです。

- 発注ワークフロー（Signal → OrderManager → Broker API）
- 頑健な状態管理（OrderRecord の状態遷移チェック）
- 再起動時のリコンシリエーション（OrderSent 状態の突合せとポジション差分検出）
- リスク管理（Gate1〜3：シグナル、エグゼキューション、メトリクス）
- ペーパートレード用の MockBrokerClient（本番 DB と切り離し）
- 監視ループ（SystemMonitor をポーリングして状態を記録）
- データ機能（マーケットカレンダー、ニュース収集など）
- 環境設定ウィザード（.env の生成）と設定検証ツール

---

## 主な機能一覧

- 設定管理
  - .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
  - 設定取得用 Settings クラス（型付きプロパティ）
- 環境セットアップ支援
  - 対話式ウィザードで .env を生成・更新（python -m kabusys.config_setup）
  - 設定ファイル・環境変数の検証 CLI（python -m kabusys.validate_config）
- 発注サブシステム
  - OrderRecord（状態遷移の検証を行う純粋モデル）
  - OrderRepository（SQLite による永続化）
  - OrderManager（発注、同期、キャンセル処理）
  - ExecutionEngine（シグナル処理ループ／WebSocket ドレイン）
  - Broker API 抽象（Protocol）とファクトリ
  - MockBrokerClient（テスト／ペーパートレード用）
  - KabuStationClient（kabuステーション REST API クライアント）
- リスク管理
  - Gate1: シグナルレベル（余力・重複・ポジション上限）
  - Gate2: エグゼキューション（レート制限・サーキットブレーカー）
  - Gate3: ドローダウン監視（キルスイッチ）
- リコンシリエーション
  - 起動時に OrderSent を照合し、ポジション差分を検出してログ記録
- 監視
  - Monitoring ポーリングループ（run_monitoring.py）
- データ関連
  - マーケットカレンダー（DuckDB ベースの判定ロジック）
  - ニュース収集（RSS 取り込み・正規化・保存のためのユーティリティ）

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を作成・有効化してください。
   (例)
   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージをインストールしてください。requirements.txt がある場合はそれを使います（例示）:
   ```
   pip install -r requirements.txt
   ```
   主要依存（コードベースから読み取れるもの）:
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML（YAML の検証を行う場合）
   - その他は標準ライブラリ（sqlite3 等）

   ※ 実行環境によって追加の OS パッケージが必要になる場合があります。

3. データディレクトリを作成（任意。実行時に自動作成される箇所もあります）:
   ```
   mkdir -p data
   ```

4. .env を作成：
   - 初回は対話式ウィザードを使うのが便利です:
     ```
     python -m kabusys.config_setup
     ```
   - 既存 .env を手動で作る場合は .env.example を参考にしてください（このリポジトリに例がある想定）。

5. 設定検証を実行（警告・エラーを事前に確認）:
   ```
   python -m kabusys.validate_config
   # 警告も失敗と見なす場合
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（代表的なコマンド）

- 環境設定ウィザード（.env を作成/更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（.env と config/*.yaml の存在・妥当性をチェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
  ```

- 発注エンジン（ExecutionEngine）を起動
  - シンプルに起動:
    ```
    python -m kabusys.run_execution
    ```
  - 補足:
    - KABUSYS_ENV=paper_trading では MockBrokerClient を使い、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）へ記録します。
    - 起動前に stop_requested.flag（data/stop_requested.flag）が存在すると起動を行いません。
    - PID ファイル（デフォルト data/execution.pid）を作成します。

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視データは常に一箇所に集約）。

- ライブラリの利用例（コード内で Settings を使う）
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  ```

---

## 環境変数（主要な設定）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーションの API パスワード

任意／推奨:
- KABUSYS_ENV — 実行環境（development | paper_trading | live）。デフォルト: development
  - 注意: live に設定した場合は本番用の注意・警告が強化されます
- DUCKDB_PATH — 分析用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパー用 SQLite（paper_trading 時に上書き）
- LOG_LEVEL — ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL）
- KABU_API_BASE_URL — kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（本番では必須推奨）
- LINE_USER_ID — LINE 通知先ユーザー ID（本番では必須推奨）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

自動ロード:
- プロジェクトルートにある .env と .env.local を自動で読み込みます（OS 環境 > .env.local > .env）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

セキュリティ:
- .env は決して Git にコミットしないでください。config_setup は .env を生成する際に注意喚起を出します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数読み込みと Settings
    - config_setup.py          — 対話式 .env ウィザード
    - validate_config.py       — 起動前設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring ポーリング起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py          — Broker API の Protocol / データモデル / ファクトリ
      - broker_factory.py      — Settings に基づくクライアント生成
      - kabu_client.py         — kabuステーション REST クライアント実装
      - mock_client.py         — MockBrokerClient（テスト用）
      - order_record.py        — Order の状態・遷移ロジック（純粋モデル）
      - order_repository.py    — SQLite 永続化層（orders テーブル管理）
      - order_manager.py       — 発注ワークフローの外向き API
      - execution_engine.py    — シグナル処理 / push ドレイン / セッション管理
      - reconciler.py          — 起動時リコンシリエーション
      - risk_manager.py        — Gate1〜3 のリスク制御
    - monitoring/
      - monitoring_db.py       — 監視 DB 初期化 / ログ機能（参照）
      - system_monitor.py      — システム監視ロジック（参照）
    - data/
      - calendar_management.py — マーケットカレンダー操作（DuckDB）
      - news_collector.py      — RSS ニュース収集・正規化
    - utils/
      - logging_setup.py       — ロギング設定ヘルパ
      - process_priority.py    — プロセス優先度設定ユーティリティ

- config/
  - （設定用 YAML ファイル一覧: system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）
  - validate_config は存在チェックと PyYAML を使ったパース検証を行います（PyYAML が無ければ内容検証はスキップ）。

- data/
  - デフォルト DB / PID / フラグなどを格納（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/stop_requested.flag）

---

## 注意事項 / 運用上のヒント

- KABUSYS_ENV を `live` にすると警告や追加安全チェックが有効になります。本番設定に切り替える前に必ず validate_config を実行してください。
- ペーパートレード（paper_trading）モードは MockBrokerClient により本番口座を操作しません。開発・検証ではまずこちらを使用してください。
- kill.flag（デフォルト data/kill.flag）を使って緊急停止を行います。起動時にこのフラグが存在するとエンジンは起動しません（KILL_FLAG_CLEAR_ON_START を 1 にすると起動時にクリア）。
- 発注ワークフローはクラッシュ安全性を意識して設計されていますが、実運用ではログ・監視設定を充実させてください。
- .env は機密情報を含むため、アクセス管理・バックアップには注意してください。

---

この README はリポジトリ内のソース（src/kabusys 以下）を元に作成しています。追加の使用例や運用手順、CI 設定、詳細な API ドキュメントは必要に応じて追記してください。