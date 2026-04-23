# KabuSys

日本株自動売買システム（KabuSys） — 小規模な自動売買エンジン、ブローカー抽象、監視・リコンシリエーション・カレンダー・ニュース収集などを含むモジュール群です。

---

## プロジェクト概要

KabuSys は、kabuステーション（ローカル/擬似API）やモックブローカーを利用して日本株の自動発注・監視を行うためのライブラリ／実行スクリプト群です。  
主に以下の責務を持ちます：

- 環境設定のウィザード・自動読み込み（`.env`）
- 起動前の設定検証（必須環境変数のチェック、config/*.yaml の検査）
- 発注エンジン（ExecutionEngine） — シグナルに基づく発注、WebSocket push ドレイン、3段階のリスクガード
- ブローカー抽象（実際の KabuStationClient とテスト用 MockBrokerClient）
- 注文の永続化（SQLite）と状態遷移の管理（OrderRecord）
- 起動時のリコンシリエーション（Reconciler）
- 監視（SystemMonitor）ポーリングループ
- データ側ユーティリティ（マーケットカレンダー管理、RSS ニュース収集 等）

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine：シグナルの読み込み→Gate1/Gate2→発注→WebSocket push ドレイン
- Broker API 層（Protocol 定義、Mock 実装、KabuStationClient 実装）
- 注文状態管理（OrderRecord）と永続化層（OrderRepository）
- リスク管理（3段階ガード: check_signal, check_execution, check_metrics）
- リコンシリエーション（起動時に OrderSent 状態を照合）
- 監視ループ（run_monitoring、MONITOR_POLL_INTERVAL で間隔調整）
- データ処理：マーケットカレンダー、ニュース収集など

---

## 要件

- Python 3.10 以上（Union 型 A | B を利用しているため）
- 推奨パッケージ（機能に応じて）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config yaml のパース検証を行う場合）
- SQLite（標準ライブラリで利用）
- ネットワークアクセス（kabuステーション または外部 API 利用時）

依存関係を requirements.txt 等で管理している場合はそれを使ってインストールしてください。無ければ次の例を参考に手動インストールできます:

pip install duckdb httpx websocket-client defusedxml PyYAML

---

## セットアップ手順

1. リポジトリをクローン／取得し、プロジェクトルートに移動します（src/ 以下が存在する構成を想定）。

2. Python 仮想環境を作成・有効化（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要な依存パッケージをインストール:
   - pip install duckdb httpx websocket-client defusedxml PyYAML

4. データディレクトリを作成（デフォルトの DB パス等に合わせる）:
   - mkdir -p data

5. 環境変数ファイル（.env）を生成または編集:
   - python -m kabusys.config_setup
     - 対話式ウィザードが起動し、.env ファイル（デフォルト: プロジェクトルート/.env）を作成または更新します。

6. 設定を検証:
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにしたい場合:
     - python -m kabusys.validate_config --strict

7. SQLite / orders DB の初期化は、通常 run_execution または該当モジュールが起動時に必要なら自動でテーブルを作成します（init_monitoring_db / init_orders_db が存在）。必要に応じてスクリプトや REPL から該当関数を呼んで初期化してください。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

オプション（よく使う）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知のための任意設定
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

例（.env の一部）:
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

注意: .env は決して Git にコミットしないでください。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 警告も FAIL 扱いに: python -m kabusys.validate_config --strict

- 実行エンジン起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用して発注が本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更可能: MONITOR_POLL_INTERVAL=<秒>

- 停止 / 強制停止
  - 実行中にファイル data/stop_requested.flag を作成するとループは検出して終了します。
  - Kill スイッチ（kill.flag）により ExecutionEngine はすべての active 注文をキャンセルして停止します（KILL_FLAG_CLEAR_ON_START に注意）。

---

## 実行上のポイント / 注意事項

- KABUSYS_ENV=paper_trading では MockBrokerClient を用いるため、ローカルで安全にテストできます。
- KABUSYS_ENV=live を使う場合は慎重に全設定（LINE 通知、kill_flag など）を確認してください（validate_config は live 時に追加の警告を出します）。
- ExecutionEngine は以下の時間ロジックに従います（デフォルト）:
  - シグナル処理開始: 08:50
  - 発注締切: 09:10
  - セッション終了: 15:30
- PID ファイル、kill.flag、stop_requested.flag などにより複数プロセス間の制御を行います。デフォルトのパスは data/ 以下です（Settings で変更可能）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル／モジュールの概観です。

src/
  kabusys/
    __init__.py            — パッケージ定義（__version__ 等）
    config.py              — 環境変数読み込み・Settings クラス（.env の自動ロードを含む）
    config_setup.py        — .env 対話式ウィザード
    validate_config.py     — 起動前設定検証 CLI
    run_execution.py       — ExecutionEngine 起動スクリプト
    run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
    execution/              — 発注関連コンポーネント
      broker_api.py        — BrokerAPI の Protocol / データモデル / ファクトリ
      broker_factory.py    — Settings に基づく Broker クライアント生成
      kabu_client.py       — kabuステーション API 実装（HTTP + WebSocket）
      mock_client.py       — テスト用モックブローカー
      order_record.py      — 注文状態・状態遷移ロジック（ビジネスルール）
      order_repository.py  — SQLite による永続化
      order_manager.py     — 外向け注文 API（create/send/sync/cancel）
      execution_engine.py  — ExecutionEngine（シグナルループ / push ドレイン / kill_switch）
      reconciler.py        — 起動時リコンシリエーション
      risk_manager.py      — 3段階リスクガード
    data/                   — データ処理モジュール
      calendar_management.py — マーケットカレンダー管理
      news_collector.py      — RSS ニュース収集
    monitoring/            — 監視関連（DB 初期化、SystemMonitor 等）※ファイルはリポジトリにより異なる
    utils/                 — ロギング設定・プロセス優先度などユーティリティ（logging_setup 等）

（実際のリポジトリには上記以外にもモジュール・テスト・スクリプトが存在する場合があります）

---

## 追加情報 / 開発メモ

- 設定検証は PyYAML がインストールされていると config/*.yaml のパース検証も行います。インストールしていない場合はスキップして警告が出ます。
- ExecutionEngine の発注フローはクラッシュ安全性を意識した 2 相永続化設計（OrderSent の事前永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 永続化）を採っています。
- MockBrokerClient はテスト用に fill_mode（instant / partial / never / reject）をサポートします。
- news_collector は SSRF 対策（スキーム検証、プライベートIP検査）や XML の安全パーシング（defusedxml）を組み込んでいます。

---

README の内容やスクリプトの挙動について不明点があれば、どの部分を詳しく知りたいか教えてください。必要なら README をプロジェクトの実ファイル（pyproject.toml 等）に合わせて微調整します。