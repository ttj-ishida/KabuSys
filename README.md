# KabuSys

日本株自動売買システムのコアライブラリ（小規模な証券会社 API ラッパー、発注エンジン、リスクガード、監視、データ取り込み等）。

バージョン: 0.1.0

---

## 概要

KabuSys は、シグナルに基づいて証券会社 API に発注を行う実行エンジン（ExecutionEngine）と、それを支える各種コンポーネント群を提供します。設計の主な方針は以下のとおりです。

- 発注フローを堅牢にするための状態管理（OrderRecord / OrderRepository / OrderManager）
- 発注前・発注時・発注後の3段階リスクガード（RiskManager: Gate1/2/3）
- 再起動時の自動復旧（Reconciler）
- 本番向け監視ループ（run_monitoring）
- ローカル開発やペーパートレード用のモックブローカー（MockBrokerClient）
- データ側：マーケットカレンダー管理、ニュース収集などのユーティリティ
- 簡易 CLI：.env 作成ウィザード、設定検証ツール、起動スクリプト

注意: 現時点では本番向けの KabuStationClient を用いた Live モードは完全実装されていない箇所があります（BrokerClientFactory は live の場合 NotImplementedError を投げます）。開発・ペーパートレード用途での利用を想定しています。

---

## 主な機能一覧

- 設定管理
  - .env、自動ロード（.env > .env.local の優先順）
  - Settings クラスによる型付きアクセス（kabusys.config.Settings）
  - 環境変数の自動検証 CLI（kabusys.validate_config）
  - 対話式 .env 作成ウィザード（kabusys.config_setup）

- 発注・実行
  - ExecutionEngine：シグナルプル型の発注エンジン（シグナル処理 + WebSocket ドレイン）
  - OrderRecord / OrderState：注文状態の状態遷移管理
  - OrderRepository：SQLite による永続化
  - OrderManager：発注フロー（create → send → sync → cancel）
  - Broker API 層（Protocol）とファクトリ（create_broker_api）
  - MockBrokerClient：テスト／開発用のブローカー実装
  - KabuStationClient：kabuステーション REST API クライアント（HTTP + WebSocket）

- リスク管理
  - RiskManager：Gate1（シグナルレベル）、Gate2（レート制限/CB）、Gate3（ドローダウン監視）

- リコンシリエーション（再同期）
  - Reconciler：OrderSent の照合・ポジション差分検出・ログ出力

- 監視
  - run_monitoring：SystemMonitor ポーリングループ（監視用 DB にログ）

- データ処理（ユーティリティ）
  - カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS パース、正規化、SSRF 対策等）

---

## セットアップ手順（開発向け）

以下は一般的な Python プロジェクトのセットアップ手順です。requirements.txt は本リポジトリには含まれていないため、下記パッケージを手動でインストールしてください。

必須（少なくとも）:
- Python 3.9+
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（config の YAML 検証に必要）
- その他（プロジェクトの他コンポーネントや CLI に応じて追加）

例（venv を使う）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb httpx websocket-client defusedxml pyyaml

3. プロジェクトのルートに移動（pyproject.toml/.git がある場所）。.env を作成するか、環境変数を設定します。

4. .env の作成はウィザードが便利:
   - python -m kabusys.config_setup

5. 生成した .env を検証:
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

注意: 自動で .env を読み込む機能が有効 (デフォルト) です。テストや特殊用途で自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（デフォルト値ありや運用用）:
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (例: data/kabusys.duckdb)
- SQLITE_PATH (例: data/monitoring.db)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABU_API_BASE_URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用）
- MONITOR_POLL_INTERVAL（監視ループ間隔、秒）

その他設定例:
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか）
- PID_FILE_PATH / KILL_FLAG_PATH / etc.

Settings 型を使ってアクセスできます（kabusys.config.Settings）。

---

## 使い方（主要 CLI / スクリプト）

1. .env 作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - 既存の .env を読み込み、Enter で再利用できます。
   - 保存後に validate_config 実行を推奨。

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1) にします。

3. 監視ループ起動（production/dev 共通で使用）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。
   - 監視は設定に従い SQLite / DuckDB に接続します。停止は data/stop_requested.flag を作成して行います。

4. 実行エンジン起動（発注）
   - python -m kabusys.run_execution
   - KABUSYS_ENV が paper_trading / development の場合は MockBrokerClient を使用します。
   - run_execution は ExecutionEngine を立ち上げ、シグナル処理（8:50–9:10）と push ドレイン（9:10–15:30）を行います。
   - 停止は data/stop_requested.flag を作成するか、kill.flag を利用します（設定に応じた挙動）。

実行順の推奨:
- .env を作成 -> validate -> （監視が必要なら）run_monitoring -> run_execution

注意:
- BrokerClientFactory は live モードの実本番クライアントの返却は未実装（NotImplementedError）。本番運用をする際は実装の完成が必要です。

---

## .env（例）

簡易サンプル（実運用ではトークン等を必ず安全に設定してください）:

JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

.env は絶対にリポジトリにコミットしないでください（config_setup でも注意喚起があります）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数の自動読み込み、Settings クラス、.env パーサ
- config_setup.py
  - 対話式 .env 作成ウィザード
- validate_config.py
  - .env / config/*.yaml の事前検証 CLI
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト

サブパッケージ: execution
- execution/__init__.py
- broker_api.py
  - BrokerAPIProtocol, データモデル（OrderRequest/Response/Status/Position）,
    例外, create_broker_api ファクトリ
- broker_factory.py
  - Settings に応じたブローカー生成
- kabu_client.py
  - KabuStation REST/WebSocket クライアント（httpx/websocket-client）
- mock_client.py
  - MockBrokerClient（fill_mode: instant/partial/never/reject）
- order_record.py
  - OrderState, OrderRecord（状態遷移検証）
- order_repository.py
  - SQLite を用いた永続化層 / DB 初期化関数 init_orders_db
- order_manager.py
  - Order の作成・送信・同期・取消を担う高位 API
- execution_engine.py
  - ExecutionEngine（シグナル処理・push ドレイン・kill_switch 等）
- reconciler.py
  - 再起動時のリコンシリエーション
- risk_manager.py
  - Gate1/2/3 の実装

サブパッケージ: data
- calendar_management.py
  - JPX カレンダー管理、営業日判定、calendar_update_job
- news_collector.py
  - RSS 収集・正規化・SSRF 対策・raw_news 保存（DuckDB）

サブパッケージ: monitoring, utils, その他
- monitoring/* （監視用 DB 初期化や SystemMonitor 実装）
- utils/logging_setup.py, process_priority.py などユーティリティ

設定ファイル:
- config/*.yaml が期待される（ファイル一覧は validate_config.py 参照）
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

スクリプト:
- scripts/generate_config.py（存在が想定され、config/*.yaml を生成可能とする旨のメッセージが validate_config で参照されています）

データディレクトリ（実行時に使用）:
- data/
  - monitoring.db（SQLite）
  - kabusys.duckdb（DuckDB）
  - execution.pid, stop_requested.flag, kill.flag など

---

## 運用上の注意・補足

- 設定検証は起動前に実行して警告・エラーを確認してください。--strict モードで CI に組み込むことを推奨します。
- run_execution は kill.flag の有無・KILL_FLAG_CLEAR_ON_START の設定を参照します。kill.flag による安全停止の挙動を理解してから運用してください。
- ペーパートレード / 開発環境では MockBrokerClient を利用することで実際の証券会社 API を使わずに検証可能です。
- 本番ブローカークライアント（KabuStationClient）の動作には kabuステーション® アプリがローカルで動作していることが前提です。接続先 URL は KABU_API_BASE_URL で指定します。
- YAML の内容検証には PyYAML が必要です。インストールされていない場合は YAML 内容検証はスキップされます（validate_config の挙動を参照）。

---

この README はコードベースの主要部分（設定、実行エンジン、ブローカー抽象、リスク管理、リコンシリエーション、データユーティリティ）をまとめたものです。実装の詳細は各モジュールの docstring / コメントを参照してください。必要であれば、個別モジュールの使い方や API 仕様（OrderRequest/OrderStatus のフィールド説明等）についての README 拡張を作成します。