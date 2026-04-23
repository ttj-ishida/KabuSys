# KabuSys

日本株自動売買システム（開発中）  
このリポジトリは、シグナルに基づく発注エンジン、モニタリング、設定管理・検証ツール等を含む軽量な自動売買フレームワークです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群を備えた自動売買基盤です。

- 発注エンジン（ExecutionEngine）：Signal Queue からシグナルを読み取り、Gate（リスクガード）を通して発注を実行する。
- ブローカークライアント抽象化：実際の kabuステーション API と、テスト用の Mock クライアントを切り替え可能。
- 注文状態管理：状態遷移の検証（OrderRecord / OrderManager）と SQLite 永続化（OrderRepository）。
- リコンシリエーション：クラッシュ後の OrderSent 状態の突合・復旧処理。
- 監視（monitoring）：SystemMonitor ベースのポーリングループと監視 DB。
- データ処理ユーティリティ：マーケットカレンダー管理、ニュース収集など。
- 設定ツール：対話式 .env 作成ウィザードと起動前設定検証 CLI。

設計方針として、DB 操作とビジネスロジックを分離し、クラッシュ時の整合性（2相永続化やリコンシリエーション）を考慮しています。

---

## 主な機能一覧

- 設定管理
  - 対話式ウィザードで .env を作成・更新（python -m kabusys.config_setup）
  - 起動前に .env と config/*.yaml を検証（python -m kabusys.validate_config）
- 実行（Execution）
  - ExecutionEngine によるシグナル処理（発注ルーチン、WebSocket push ドレイン）
  - RiskManager による 3 段階ガード（Gate1: シグナル、Gate2: レート/CB、Gate3: ドローダウン）
  - BrokerClientFactory による mock/live クライアント選択（現在は mock が主）
  - 注文状態の永続化（SQLite）とリコンシリエーション
- モニタリング
  - SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔変更可）
  - 監視 DB（SQLite）へイベント記録
- データ
  - カレンダー管理（DuckDB ベース、J-Quants から差分取得可）
  - ニュース収集（RSS フィード、SSRF/XML 脆弱性対策を考慮）
- テスト支援
  - MockBrokerClient（fill_mode: instant/partial/never/reject）
  - ローカル専用 paper_trading モード（paper_trading 用 SQLite を分離）

---

## セットアップ手順

前提:
- Python 3.9+ を想定（typing / Path などを利用）
- Git 等でリポジトリを取得済み

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール  
   必要なパッケージ（代表例）:
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML（YAML ファイル検証に利用。任意）
   - その他標準ライブラリは不要（sqlite3 等は標準）

   例:
   - pip install duckdb httpx websocket-client defusedxml PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使ってください）

4. 初期設定ファイルの作成
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
     ウィザードに従って J-Quants トークンや Kabu API パスワードなどを入力します。
   - または手動で .env を作成（.env.example を参考に）

5. 設定検証（起動前）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. DB ディレクトリ作成（任意）
   - 多くのパスはデフォルトで data/*.db を参照します。親ディレクトリが存在しない場合は自動作成されないことがあるため、必要に応じて `mkdir -p data` を作成してください。起動時に作成されることも多いです。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup
  - オプション:
    - --env-file <path> で .env の保存先を変更可能

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い（exit code 1）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒, デフォルト 60）
  - 監視は常に設定の sqlite_path を使用（環境にかかわらず本番 DB ）

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV によって動作:
    - development / paper_trading → MockBrokerClient が使われる（paper_trading 用 DB は data/paper_trading.db）
    - live → 現時点では NotImplemented（実運用クライアントは未実装）
  - 起動時、PID ファイルと kill.flag の動作に注意（kill_flag_clear_on_start の設定で起動時のクリア挙動を制御）

- その他（ライブラリ利用例）
  - from kabusys.config import settings
  - from kabusys.execution import ExecutionEngine 等をテストコードから直接利用可能

---

## 環境変数（主要項目）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨:
- KABUSYS_ENV — 実行環境（development / paper_trading / live） デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） デフォルト: INFO
- KABU_API_BASE_URL — kabu station API ベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- PAPER_FILL_MODE — ペーパートレード時の fill_mode（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite パス（デフォルト data/paper_trading.db）

自動読み込み:
- プロジェクトルート（.git か pyproject.toml が存在するディレクトリ）を基準に、.env（デフォルト）および .env.local（上書き）を自動で読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 実装上の注意・挙動

- validate_config は PyYAML が無ければ config/*.yaml のパース検証をスキップします（警告）。PyYAML をインストールしておくとより厳密に検証できます。
- ExecutionEngine は以下の流れで動作します:
  - 起動時にリコンシリエーション（OrderSent の突合）
  - 指定時間帯（デフォルト 8:50-9:10）にシグナル読み込みと発注処理
  - その後 WebSocket push（kabu station の通知）をドレインして注文状態を同期
  - kill.flag を検出すると全 active 注文をキャンセルして安全停止
- OrderManager の send_order はクラッシュ安全性を考慮し、OrderSent 状態を先に永続化してから broker 呼び出しを行い、broker_order_id を先にコミットする等の処理を行います（2相永続化的な扱い）。
- MockBrokerClient は複数の fill_mode をサポートし、統合テストが容易です。

---

## ディレクトリ構成

（主要ファイル / ディレクトリのみ抜粋）

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  - （config/*.yaml は validate_config で確認）
- data/
  - (データファイル格納ディレクトリ。例: kabusys.duckdb, monitoring.db, paper_trading.db)
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・.env ロードロジック、Settings
  - config_setup.py          — 対話式 .env 作成ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - broker_api.py          — Broker API のデータ模型・Protocol・ファクトリ
    - kabu_client.py         — kabu station REST クライアント（httpx）
    - mock_client.py         — テスト用 MockBrokerClient
    - broker_factory.py      — Settings に基づくクライアント生成
    - order_record.py        — Order の状態遷移ロジック（純粋モデル）
    - order_repository.py    — SQLite 永続化層 + 初期化関数
    - order_manager.py       — 注文管理（作成・送信・同期・キャンセル）
    - execution_engine.py    — ExecutionEngine（シグナル処理 + push ドレイン）
    - reconciler.py          — リコンシリエーション（起動時復旧）
    - risk_manager.py        — 3 段階リスクガード
  - data/
    - calendar_management.py — マーケットカレンダー（DuckDB）
    - news_collector.py      — RSS ニュース収集
    - jquants_client.py      — （J-Quants API ラッパ、コードベースに依存）
  - monitoring/
    - monitoring_db.py       — 監視 DB 初期化・ログ関数
    - system_monitor.py      — システム監視ロジック
  - utils/
    - logging_setup.py       — ロギングの共通設定
    - process_priority.py    — プロセス優先度設定（可能な場合）

---

## 開発・運用上のヒント

- ローカル開発では KABUSYS_ENV=development / paper_trading を使い、MockBrokerClient で十分に検証できます。
- 本番（live）環境での実行は慎重に。validate_config は live 設定時に追加の警告を出します（LINE 通知設定や KILL_FLAG_CLEAR_ON_START 等）。
- データベースファイルのバックアップ、ログ監視、監視 DB の検査は運用前に必須です。
- Reconciler はクラッシュ復帰のための重要な機能です。起動時にリコンシリエーションが失敗するとポジション照合をスキップします（安全上の判断）。

---

## 参考コマンドまとめ

- 仮想環境作成
  - python -m venv .venv
  - source .venv/bin/activate
- 依存インストール（例）
  - pip install duckdb httpx websocket-client defusedxml PyYAML
- .env 作成
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視起動
  - python -m kabusys.run_monitoring
- 実行エンジン起動
  - python -m kabusys.run_execution

---

README に記載の内容はコードベースから抽出した現時点（v0.1.0）の概要です。実装が進むにつれて機能や挙動が変わる可能性があります。質問や追加したい内容があれば教えてください。