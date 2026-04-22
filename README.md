# KabuSys

日本株自動売買システム（モジュール群）の軽量リポジトリ。  
この README はソースツリー（src/kabusys/*.py）の構成と主要な利用方法、セットアップ手順を簡潔にまとめています。

注意: このリポジトリは実運用を意図したサンプル実装／ライブラリであり、実際に取引を行う場合は十分な検証と責任ある運用が必要です。

---

## 概要

KabuSys は、シグナルに基づいて日本株の発注を行うためのモジュール群を提供します。主な機能は以下のとおりです。

- Execution Engine（Signal Pull 型発注ループ）
- Broker API 抽象化（kabuステーション用クライアントとモック）
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- リスク管理（3 段階ガード: Gate1/2/3）
- リコンシリエーション（再起動後の自動復旧）
- 監視用ループ（SystemMonitor をポーリング）
- データユーティリティ（マーケットカレンダー管理、ニュース収集等）
- 環境設定ウィザードと設定検証 CLI（.env の対話生成・検証）

設計方針として、API クライアント層は DB に触らず純粋に通信を担当し、注文状態や永続化は SQLite（orders テーブル）を用いた厳密なワークフローで扱います。Paper trading（ペーパートレード）用に MockBrokerClient を用意しており、本番環境と本番 DB を分離できるようになっています。

---

## 主な機能一覧

- .env 生成ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
  - --strict オプションで警告も失敗扱い
- 実行エンジン起動スクリプト
  - 実行（発注）: python -m kabusys.run_execution
  - 監視（SystemMonitor）: python -m kabusys.run_monitoring
- Broker 抽象: create_broker_api() により Mock/KabuStation クライアントを切替可能
- 注文永続化・状態管理（SQLite）: OrderRepository / OrderRecord / OrderManager
- リスク管理: Rate limit、Circuit breaker、Position/Utilization/Drowdown のガード
- リコンシリエーション: 再起動時に OrderSent 状態の注文を突合して復旧
- Data 関連ユーティリティ: カレンダー（DuckDB ベース）やニュース収集用クラス

---

## 前提 / 必要環境

- Python 3.10+
- SQLite（標準ライブラリ）
- DuckDB（分析用 DB 接続）：pip install duckdb
- HTTP クライアント：pip install httpx
- WebSocket（kabu push 用）：pip install websocket-client
- XML セキュア処理：pip install defusedxml
- PyYAML（config/*.yaml のパース検証に任意）：pip install PyYAML

推奨: 仮想環境を作成してからパッケージをインストールしてください。

例:
- 仮想環境作成・有効化（Unix/macOS）
  - python -m venv .venv
  - source .venv/bin/activate
- 必要パッケージのインストール（例）
  - pip install duckdb httpx websocket-client defusedxml PyYAML

本リポジトリに requirements.txt があればそれを利用してください:
- pip install -r requirements.txt

---

## セットアップ手順

1. リポジトリをクローンする
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を用意して依存パッケージをインストール（上記参照）

3. .env ファイルの作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成／更新します。生成後は必ず .env を Git にコミットしないでください（README 内にも警告があります）。

4. 設定検証を実行
   - python -m kabusys.validate_config
   - 警告も含めて厳密にチェックしたい場合:
     - python -m kabusys.validate_config --strict

5. データベース初期化（必要に応じて）
   - 実行時にスクリプトが必要なテーブルを作成します（init_orders_db / init_monitoring_db 等）。
   - 監視・実行スクリプトは起動時に DB 接続を作成し、必要なテーブルがなければ初期化する箇所があります。

6. 実行
   - 発注エンジン（Execution）
     - python -m kabusys.run_execution
   - 監視ループ（Monitoring）
     - python -m kabusys.run_monitoring

環境変数で挙動を上書き:
- KABUSYS_ENV (development | paper_trading | live) — 実行モード
- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite
- LOG_LEVEL — (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABU_API_BASE_URL — kabu station のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時 kill flag 自動クリア（0/1）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（概要コマンド）

- 環境ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- 発注エンジン起動（本番またはペーパートレード）
  - python -m kabusys.run_execution

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）

開発用モック:
- Paper trading / development 環境では MockBrokerClient が使われ、外部 kabu ステーション不要でテスト可能です。
- Mock の挙動は Settings.paper_fill_mode（instant|partial|never|reject）で制御できます。

停止フラグ:
- リポジトリの data/stop_requested.flag を作成するとループが検知して停止します。
- ExecutionEngine は data/execution.pid を PID ファイルとして書き出します。起動前に kill.flag を検査し、KILL_FLAG_CLEAR_ON_START に応じて動作を決定します。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py — パッケージ宣言、バージョン
- config.py — 環境変数読み込みと Settings クラス（.env 自動読み込みロジック含む）
- config_setup.py — 対話式 .env ウィザード
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine を起動するエントリスクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ / 主要モジュール:
- execution/
  - broker_api.py — Broker API のデータモデル・Protocol・例外・ファクトリ
  - kabu_client.py — kabuステーション API クライアント（HTTP + WebSocket）
  - mock_client.py — MockBrokerClient（テスト / ペーパートレード用）
  - broker_factory.py — Settings に応じたブローカーファクトリ
  - order_record.py — 注文状態モデルと遷移ロジック
  - order_repository.py — SQLite ベースの永続化層（orders テーブル）
  - order_manager.py — OrderRecord と repo を組み合わせた外向き API
  - execution_engine.py — Signal Pull 型発注エンジン本体
  - reconciler.py — 再起動時のリコンシリエーション
  - risk_manager.py — Gate1/2/3 のリスク制御ロジック
- data/
  - calendar_management.py — マーケットカレンダー管理（DuckDB）
  - news_collector.py — RSS ベースのニュース収集（DefusedXML を利用）
  - （jquants クライアント等が別ファイルとして存在する想定）
- monitoring/
  - monitoring_db.py (参照されるがここに含まれていることを想定)
  - system_monitor.py (同上)
- utils/
  - logging_setup.py — ログ初期化ユーティリティ（参照）
  - process_priority.py — プロセス優先度設定ユーティリティ（参照）

（注）README に記載している一部ユーティリティ / モジュールは抜粋して示しています。リポジトリ全体を参照して詳細を確認してください。

---

## 設定例（.env の主要項目）

必須:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password

推奨/任意:
- KABUSYS_ENV=development
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=
- KILL_FLAG_CLEAR_ON_START=0

対話ウィザードを使うと安全に .env を作成できます:
- python -m kabusys.config_setup

---

## 開発メモ / 注意点

- Settings クラスは環境変数から必要値を取得し、必須値が未設定の場合は例外を投げます。アプリケーション起動前に validate_config を実行して設定状態を確認することを推奨します。
- Execution の本番ブローカークライアント（KabuStationClient）はネットワーク・証券会社 API に依存するため、ペーパートレード（MockBrokerClient）でロジック検証を行ってください。
- Order の永続化は SQLite を用い、同一 signal_id の active 注文を DB 制約で 1 件に制限しています。複数プロセスからの同時実行を想定する際はトランザクション設計に注意してください。
- WebSocket 接続は kabu station の push を受け取る仕組みを備えています。接続断時の再接続ロジックがありますが、プロダクションでは監視とリソース管理を適切に行ってください。
- 外部ライブラリのバージョンや OS 依存の挙動は適宜 lock して検証することを推奨します。

---

## 参考・次のステップ

1. 仮想環境を作り、依存をインストールする
2. python -m kabusys.config_setup で .env を作る
3. python -m kabusys.validate_config で検証
4. paper_trading モードで python -m kabusys.run_execution を実行して挙動を確認
5. 実データ連携（J-Quants / kabu station）・監視設定を整え、本番運用の前に十分なテストを行う

---

問題の報告や改善提案があれば Issue を立ててください。