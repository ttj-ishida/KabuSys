# KabuSys

日本株自動売買システムのコアライブラリ（README）

このリポジトリは KabuSys の主要コンポーネントを含む Python パッケージです。発注エンジン、リスクガード、モニタリング、カレンダー管理、ニュース収集などの機能を備え、ローカル開発 / ペーパートレード / 本番の各実行環境を想定しています。

## プロジェクト概要
- 発注エンジン（ExecutionEngine）によりシグナルを取り込み、ブローカー API 経由で発注を行います。
- リスク管理は 3 段階（Gate1: シグナルレベル、Gate2: エグゼキューションレート制御 + サーキットブレーカー、Gate3: ドローダウン監視）で設計されています。
- ブローカークライアントは抽象化されており、モック（MockBrokerClient）と kabuステーション用クライアント（KabuStationClient）を切り替え可能です。
- 起動前に環境設定を対話式で生成するウィザード（config_setup）と、設定検証ツール（validate_config）を提供します。
- 監視（SystemMonitor）を独立プロセスで実行する run_monitoring スクリプトがあります。
- DuckDB / SQLite を用いたデータ管理、J-Quants からのカレンダー取得、RSS ニュース収集用のユーティリティを含みます。

## 主な機能一覧
- 設定管理
  - .env の自動読み込み（プロジェクトルートの .env / .env.local）と Settings API（kabusys.config.Settings）
  - 対話式ウィザードで .env を生成・更新（python -m kabusys.config_setup）
  - 起動前チェック（環境変数、config/*.yaml の存在・パース）を行う CLI（python -m kabusys.validate_config）
- 実行エンジン
  - ExecutionEngine：シグナルの読み込み、発注フロー、WebSocket push ドレイン、kill switch
  - OrderManager / OrderRecord / OrderRepository：注文状態管理と SQLite 永続化
  - RiskManager：Gate1/2/3 によるリスク統制（レート制限、サーキットブレーカー、ドローダウン等）
  - Reconciler：再起動時の OrderSent 注文照合とポジション差分検査
- ブローカークライアント
  - MockBrokerClient：テスト／ペーパートレード用（fill_mode サポート）
  - KabuStationClient：kabuステーション REST API 実装（httpx / websocket-client ベース）
- データ関連
  - DuckDB を使ったマーケットカレンダー管理、シグナル／ポートフォリオ参照
  - RSS ニュース収集と前処理（defusedxml ベースの安全なパーシング）
- 監視
  - run_monitoring による SystemMonitor のポーリングループ（SQLite／DuckDB を利用）

## 必要な環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意／設定推奨（例）:
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABU_API_BASE_URL
- LINE_CHANNEL_ACCESS_TOKEN（本番アラート用）
- LINE_USER_ID（本番アラート用）

注:
- .env を生成する際は secrets（API トークン等）を Git にコミットしないでください。
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

## セットアップ手順（開発向け）
1. リポジトリを clone
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（プロジェクトに requirements ファイルが無い場合の例）
   - pip install duckdb httpx websocket-client PyYAML defusedxml
   - ※ PyYAML が無くても動作する箇所がありますが、config/*.yaml のパース検証を行うには必要です。
4. .env を作成
   - 対話式ウィザードを使用: python -m kabusys.config_setup
   - 手動で作成する場合はルートの .env に必要なキーを設定
5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

## 使い方（主要コマンド）
- 環境設定ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup
  - 対話式に項目を入力し .env を保存します。

- 設定検証
  - python -m kabusys.validate_config
  - 警告も失敗扱いにする（CI 等で使用）
    - python -m kabusys.validate_config --strict

- 実行エンジン（本番／ペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV に応じて MockBrokerClient を選択（paper_trading / development）または本番クライアント（live は未実装エラーになる設計）

- 監視ループ
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

- 停止制御
  - 停止フラグファイル: data/stop_requested.flag を作成するとループは検知して終了します。
  - kill.flag（KILL_FLAG_PATH）を用いることで起動拒否や kill_switch をトリガできます（KILL_FLAG_CLEAR_ON_START による動作も設定可能）。

## よく使う設定例（.env の一部）
例:
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=paper_trading
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
LINE_CHANNEL_ACCESS_TOKEN=              # 任意
LINE_USER_ID=                           # 任意

（実際のシークレット値は "your_value" などのプレースホルダから変更してください。validate_config で検出されます）

## ディレクトリ構成（主要ファイル）
プロジェクトルート（_PROJECT_ROOT）
- .env, .env.local (プロジェクトルートに配置)
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/
  - (DuckDB/SQLite ファイル、pid/flag ファイルなど)
- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込みと Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - execution/
    - broker_api.py — Broker API の Protocol、データモデル、ファクトリ
    - broker_factory.py — Settings に応じたブローカークライアント生成
    - kabu_client.py — kabuステーション REST API 実装
    - mock_client.py — モックブローカー
    - order_record.py — 注文状態モデルと遷移
    - order_repository.py — SQLite 永続化層（orders テーブル）
    - order_manager.py — 注文フローの外向き API
    - execution_engine.py — 発注エンジン本体
    - reconciler.py — 起動時リコンシリエーション
    - risk_manager.py — 3 段階リスクガード
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集と前処理
  - monitoring/ (監視関連モジュール)
  - utils/ (ロギング設定やプロセス優先度などのユーティリティ)

各モジュールはソース内に詳細な docstring を持っており、設計上「DB に触れない」「I/O を隠蔽」「テスト可能な分離」を意識して実装されています。

## 注意点・運用上のヒント
- KABUSYS_ENV=live を使う場合は設定を慎重に確認してください（validate_config は live での警告を出します）。
- .env は絶対にリポジトリにコミットしないでください（config_setup でも注意喚起があります）。
- 実際のブローカークライアント（KabuStationClient）を使用するには kabuステーションが動作している環境と API の設定が必要です。本リポジトリでは主にペーパートレード/ローカル開発向けに MockBrokerClient をサポートしています。
- config/*.yaml は任意ツール（scripts/generate_config.py 等）で生成可能。PyYAML がない場合、validate_config は YAML パース検証をスキップします（警告）。

---

この README はコードベースの主要ポイントを整理したものです。各モジュールの詳細な使い方や API（OrderRequest / OrderResponse 等）はソースの docstring を参照してください。必要であれば README の拡張やコマンド例（systemd ユニット、Dockerfile、CI 設定例）も作成します。希望があれば教えてください。