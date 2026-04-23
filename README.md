# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。

この README はコードを元に作成した概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたシステムです。  
主な設計方針は次のとおりです：

- 発注ロジックと永続化（SQLite）を分離した堅牢な注文処理フロー
- 発注前/発注中/約定後の多段階リスクガード（Gate1/2/3）
- 再起動後の自動リコンシリエーション（OrderSent 状態の注文を突合）
- ペーパートレード用のモックブローカー（テスト・開発向け）
- DuckDB を使ったデータ分析 / シグナル取得 / カレンダー管理
- 監視プロセス（SystemMonitor）によるシステム資源・ログの監視

本リポジトリは CLI ベースでの設定ウィザードや設定検証、監視・実行プロセス起動スクリプトを提供します。

---

## 主な機能一覧

- .env ウィザード（対話式）: .env の作成・更新を支援（`kabusys.config_setup`）
- 設定検証 CLI: .env と config/*.yaml の妥当性チェック（`kabusys.validate_config`）
- ExecutionEngine:
  - Signal Queue ベースの発注ループ（8:50–9:10 シグナル処理、9:10–15:30 push ドレイン）
  - OrderManager / OrderRepository による安全な注文送信と状態遷移
  - RiskManager による Gate1/2/3 のチェック（余力、重複、レート制限、ドローダウン等）
  - Reconciler による再起動時の自動復旧
  - ペーパートレード時は MockBrokerClient を使用（DB 分離）
- KabuStation REST クライアント（同期実装・WebSocket push 対応）
- Data モジュール: マーケットカレンダー管理、ニュース収集（RSS）、J-Quants などの連携
- 監視プロセス（monitoring）: SystemMonitor のポーリングループ（SQLite + DuckDB）

---

## 主要な環境変数

必須（起動前に設定が必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / よく使うもの
- KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視 DB の SQLite パス（デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: `data/paper_trading.db`）
- LOG_LEVEL — ログレベル（`DEBUG|INFO|WARNING|ERROR|CRITICAL`，デフォルト: `INFO`）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: `http://localhost:18080/kabusapi`）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番環境での通知設定
- KILL_FLAG_PATH — kill flag のパス（デフォルト: `data/kill.flag`）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（`0`/`1`，デフォルト: `0`）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: `60`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（`1`）

注意:
- 自動で .env ファイルをプロジェクトルートから読み込みます（優先順: OS > .env.local > .env）。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。

---

## セットアップ手順（開発環境向け）

1. Python 環境（推奨: 3.10+）を用意する。
2. 必要なパッケージをインストールする（プロジェクトに requirements.txt があればそちらを使用してください）。例:

   pip install httpx websocket-client duckdb defusedxml pyyaml

   - 注意: validate_config は PyYAML がないと YAML 中身の検証をスキップします（存在確認のみ行います）。
   - duckdb は分析・シグナル取得・calendar 処理で使用します。
3. プロジェクトルートに移動し、対話式ウィザードで .env を生成（推奨）:

   python -m kabusys.config_setup

4. 作成した .env を検証:

   python -m kabusys.validate_config

   - 追加オプション: `--strict` を付けると警告もエラー（exit code=1）扱いになります。
5. データベース初期化や config/*.yaml を用意（必要に応じて）。validate_config の警告に従って `config/*.yaml` を生成してください（プロジェクトに generate_config.py がある想定）。

---

## 使い方（実行例）

- 環境設定ウィザード（.env の新規作成 / 更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）。

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient が使われ、paper_trading 用 SQLite（data/paper_trading.db）を使用します。
  - run_execution は PID ファイル（デフォルト: `data/execution.pid`）や stop flag（`data/stop_requested.flag`）を利用します。

- 注意点
  - 本番環境(`KABUSYS_ENV=live`)では追加の注意喚起や警告が出ます。LINE 通知設定などを適切に行ってください。
  - `KILL_FLAG_CLEAR_ON_START=1` を本番で使うと危険です（kill flag が自動でクリアされます）。

---

## 主要コンポーネント説明（簡易）

- config.py / Settings
  - .env/.env.local の読み込みロジック、Settings クラス（型安全なアクセス）
  - 自動ロードはプロジェクトルート（.git / pyproject.toml）を基準に行われる

- config_setup.py
  - 対話式ウィザードで .env を生成・更新する

- validate_config.py
  - 必須環境変数の確認、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス存在確認、config/*.yaml の存在・YAML パース（PyYAML がある場合）

- run_execution.py
  - ExecutionEngine を起動するスクリプト（プロセス優先度設定、DB 接続、PID/stop フラグの管理）

- execution パッケージ
  - broker_api.py — ブローカー用 Protocol、データモデル、ファクトリ
  - kabu_client.py — kabu station REST クライアント（HTTP + WebSocket）
  - mock_client.py — テスト用モック（fill_mode など指定可）
  - order_record.py / order_repository.py / order_manager.py — 注文状態管理、SQLite 永続化、発注 API を組み合わせた上位 API
  - execution_engine.py — 発注エンジン（シグナル処理、push ドレイン、kill switch）
  - risk_manager.py — Gate1/2/3 の実装
  - reconciler.py — 再起動時の OrderSent 照合・ポジション突合

- data パッケージ
  - calendar_management.py — マーケットカレンダー管理（DuckDB を利用）
  - news_collector.py — RSS ニュース収集（XML パースの安全対策、SSRF 対応など）
  - （その他 J-Quants クライアント等が想定）

- monitoring
  - run_monitoring.py — SystemMonitor のポーリングループを実行するスクリプト
  - 監視用 SQLite を利用（設定により path を指定）

- utils
  - logging_setup / process_priority など、共通ユーティリティ（ログの初期化やプロセス優先度設定）

---

## ディレクトリ構成（抜粋）

プロジェクトルート（src/kabusys を含む想定）の代表的なファイル・フォルダ:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/
      - __init__.py
      - broker_api.py
      - broker_factory.py
      - kabu_client.py
      - mock_client.py
      - order_record.py
      - order_repository.py
      - order_manager.py
      - execution_engine.py
      - reconciler.py
      - risk_manager.py
      - (その他 execution 関連モジュール)
    - data/
      - calendar_management.py
      - news_collector.py
      - (jquants_client など)
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - strategy/  (エクスポート先として存在)
    - (その他)

- .env.example / .env (ユーザー管理、.env は Git にコミットしないでください)
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  - （各種設定 YAML — validate_config で存在チェック/パース検証）

---

## 運用・注意事項

- .env は絶対にリポジトリにコミットしないこと（シークレットを含む）。
- 本番起動時（KABUSYS_ENV=live）は設定や通知設定を慎重に確認すること。validate_config の警告を参考にしてください。
- kill.flag（デフォルト: data/kill.flag）により即時停止が可能。KILL_FLAG_CLEAR_ON_START は本番では `0` を推奨します。
- ExecutionEngine は時間帯（シグナル処理や市場時間）に依存する動作を行います。テスト時は直接メソッドを呼ぶか、環境を paper_trading にして MockBrokerClient を使ってください。
- リコンシリエーションはクラッシュ後の整合性回復に重要です。OrderSent の状態が残るシナリオを想定して設計されています。

---

## よく使うコマンドまとめ

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring

---

必要であれば、README にサンプル .env のテンプレートや、より詳細な開発手順（ユニットテスト、CI、データベース初期化手順、依存パッケージの具体的バージョン等）を追加します。どの情報を優先して追記するか指示してください。