# KabuSys

日本株自動売買システムの内部ライブラリ群（README）。本ドキュメントはリポジトリ内の主要スクリプト・設定方法・ディレクトリ構成を簡潔にまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。発注エンジン、リスクガード、ブローカークライアント（kabu station のラッパー / モック）、監視（Monitoring）、データ処理（カレンダー・ニュース収集）などの主要機能を持ち、小規模な自動売買運用・テスト環境を構築できるよう設計されています。

主な特徴：
- ExecutionEngine：シグナルの読み込み → 発注フロー（Gate1/2/3）→ WebSocket push 処理
- Order 管理：状態遷移（OrderRecord）、SQLite による永続化（OrderRepository）
- ブローカー抽象（BrokerAPIProtocol）：実運用用クライアント（KabuStationClient）とテスト用モック（MockBrokerClient）
- リスク管理（RiskManager）：3段階ガード（シグナル、実行、メトリクス）
- リコンシリエーション（Reconciler）：クラッシュ後の復旧
- 設定管理（Settings）：.env 自動読み込み、Settings クラス経由でアクセス
- 設定ウィザード / 検証 CLI：.env 生成・検証を支援
- データユーティリティ：マーケットカレンダー管理、ニュース収集モジュールなど

---

## 機能一覧

- 設定管理
  - .env / .env.local からの自動読み込み（OS 環境変数が優先）
  - Settings クラスを通じた安全な設定取得（必須変数はエラー）
  - config_setup.py による対話式 .env ウィザード
  - validate_config.py による起動前チェック（--strict オプション有）

- 実行（Execution）
  - ExecutionEngine：シグナル読み込み → 発注（OrderManager） → WebSocket push ドレイン
  - OrderRecord、OrderRepository による厳密な状態管理と永続化
  - BrokerClientFactory：環境に応じたブローカークライアント生成（mock / live）
  - MockBrokerClient：fill モードを切り替え可能（instant / partial / never / reject）
  - Reconciler：OrderSent 状態の自動照合とポジション差分検出
  - RiskManager：余力・重複・ポジション上限・レート制限・サーキットブレーカー・ドローダウン検査

- 監視（Monitoring）
  - run_monitoring.py によるループ監視（MONITOR_POLL_INTERVAL で調整）
  - SQLite / DuckDB を使った監視データ格納（監視は常に本番 sqlite_path を使用）

- データ処理
  - calendar_management：J-Quants を前提とした営業日管理・バッチ更新
  - news_collector：RSS 収集、前処理、安全対策（SSRF・XML 脆弱性対策）など

---

## セットアップ手順（概略）

1. リポジトリをクローン / 展開
2. 仮想環境を作成し依存パッケージをインストール
   - 例（pipenv / venv / poetry 等を使用）:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -r requirements.txt
   - 主要依存（ソースから推測）:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（validate_config が YAML パースを行う場合）
   - 注: requirements.txt が無い場合はプロジェクトで使用しているパッケージを上記からインストールしてください。

3. 環境変数ファイルの準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成
   - 自動ロードの挙動:
     - OS 環境変数 > .env.local > .env の順で読み込まれます
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト用途）

4. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする: python -m kabusys.validate_config --strict

5. データベース初期化（必要に応じて）
   - 監視や注文永続化用の SQLite、分析用 DuckDB の親ディレクトリを作成
   - デフォルト:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
   - スクリプト等で DB テーブル初期化を行ってください（monitoring / orders テーブルなど）

---

## 使い方（主要スクリプト）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup
  - 対話式に各種キー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を入力します。
  - 生成される .env は Git にコミットしないでください（機密情報含む）。

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗扱い（exit code 1）にできます。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は常に settings.sqlite_path を使います（paper_trading でも本番 sqlite を使用）

- 実行（Execution）プロセス起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV によって挙動が変わります:
    - development / paper_trading: MockBrokerClient が使用されます（paper_trading では paper_sqlite_path を使用）
    - live: 実運用用クライアントは未実装（現状は NotImplementedError）
  - 実行は PID / kill flag の仕組みを利用します（data/execution.pid, data/kill.flag, data/stop_requested.flag）

---

## 必要な環境変数（抜粋）

必須（validate_config および Settings で必須扱い）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意・設定可能な環境変数（主なもの）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- KABU_API_BASE_URL: kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番通知用（任意）
- KILL_FLAG_CLEAR_ON_START: 0/1（起動時に kill.flag を自動クリアするか。開発用）

注意:
- validate_config は PyYAML がインストールされていると config/*.yaml の YAML パース検証を行います。未インストール時は警告を出してスキップします。
- KABUSYS_ENV=live の場合は追加の安全チェック（LINE 通知設定、KILL フラグ設定など）があります。

簡単な .env の例（必須キーのみ）:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development

（実運用ではシークレットは適切に保護してください）

---

## 動作上の注意点 / トラブルシューティング

- validate_config を実行してエラーや警告を確認してから実行プロセスを起動してください。
- MONITOR_POLL_INTERVAL は整数で 1 以上が必要です。無効な値はデフォルト（60 秒）にフォールバックします。
- monitoring は常に settings.sqlite_path を使用します。paper_trading 環境でも監視用 DB は別になっていない点に注意してください。
- run_execution は paper_trading 環境では paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離します。
- ExecutionEngine は起動時に PID ファイルを書き、終了時に削除します。kill.flag が存在する場合は起動を拒否する（設定次第でクリア）挙動があります。
- KabuStationClient（実ブローカー API）を使う場合はローカルに kabuステーション® アプリが稼働していることが前提です（API エンドポイントは通常 http://localhost:18080/kabusapi）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要な構成は以下のとおり（src/kabusys をルートとした概略）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数の読み込みと Settings クラス
  - config_setup.py         — .env 対話ウィザード CLI
  - validate_config.py      — 起動前設定検証 CLI
  - run_monitoring.py       — 監視ポーリングループ起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト

  - execution/              — 発注周りの実装
    - __init__.py
    - broker_api.py         — BrokerAPI の Protocol / データモデル / ファクトリ
    - kabu_client.py        — kabu station REST クライアント
    - mock_client.py        — テスト用モッククライアント
    - broker_factory.py     — Settings に基づくクライアント生成
    - execution_engine.py   — ExecutionEngine（セッション制御）
    - order_record.py       — 注文状態モデルと遷移ロジック
    - order_repository.py   — SQLite 永続化（orders テーブル）
    - order_manager.py      — OrderState Machine の外向き API
    - reconciler.py         — 起動時リコンシリエーション
    - risk_manager.py       — 3段階リスクガード

  - monitoring/             — 監視関連（DB 初期化など）
    - monitoring_db.py  (参照：run_monitoring / run_execution が利用)

  - data/                   — データ関連モジュール
    - calendar_management.py — マーケットカレンダー管理（DuckDB/J-Quants 連携）
    - news_collector.py      — RSS ニュース収集（安全対策付き）
    - jquants_client.py      — （想定）J-Quants API ラッパー（参照される）

  - utils/                  — ユーティリティ
    - logging_setup.py       — ロギング初期化
    - process_priority.py    — プロセス優先度設定ユーティリティ

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （validate_config で存在確認／YAML パース検証を行います。無ければ警告が出ます）

- data/
  - *.db / *.duckdb / stop_requested.flag / kill.flag / execution.pid など実行時生成物

---

以上が本リポジトリの概要・セットアップ・利用方法の要約です。詳細な設計・運用上の注記は個別モジュールの docstring を参照してください。その他、README に追記して欲しい項目（セットアップスクリプトの具体例、テスト手順、依存パッケージの正確な一覧など）があれば教えてください。