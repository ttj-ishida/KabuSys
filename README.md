# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、kabuステーションや J-Quants を使った自動売買フローの基盤コンポーネントを含みます。実行用のエンジン、監視ループ、環境設定ウィザード、設定検証ツールなどが含まれています。

注意: 本 README はコードベース（src/kabusys 以下）に基づいて作成しています。実運用は十分な理解と十分なテストを行った上で行ってください。

## 主要機能

- 環境設定ウィザード（.env を対話的に作成 / 更新）
  - python -m kabusys.config_setup
- 設定検証ツール（.env と config/*.yaml のチェック）
  - python -m kabusys.validate_config [--strict]
- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV に応じて MockBrokerClient（paper_trading / development）を使用
- 監視ループ（SystemMonitor をポーリング）
  - python -m kabusys.run_monitoring
- ブローカー抽象化層（BrokerAPIProtocol / factory）
  - 実装: MockBrokerClient（テスト用）、KabuStationClient（kabuステーション API ）
- 注文状態管理（OrderRecord の状態遷移検証、OrderManager、OrderRepository）
- リスク管理（3段階ガード: Gate1/Gate2/Gate3、サーキットブレーカー、レート制限）
- リコンシリエーション（再起動時の OrderSent 状態の突合・回復）
- データ周り: DuckDB / SQLite を用いたカレンダー・シグナル・ポジション管理、RSS ニュース収集（安全対策付き）

## 動作要件

- Python 3.10 以上（型注釈に `|` を使用）
- 推奨パッケージ（機能に応じて必要）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml のパース検証用、未インストール時は検証をスキップ）
- 標準ライブラリ: sqlite3, logging, threading, datetime など

（実際の環境では requirements.txt を用意し pip でインストールしてください。）

## セットアップ手順（開発 / テスト向け）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone <リポジトリURL>
   - cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml PyYAML

   （プロダクション用に requirements.txt を用意している場合はそれを使用してください）

4. .env の作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に `.env` をプロジェクトルートに置く

   自動ロード:
   - .env はプロジェクトルート（.git または pyproject.toml があるディレクトリ）から自動ロードされます。
   - .env.local があれば .env の値を上書きします。
   - オートロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 設定検証（必須）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

6. DB 用ディレクトリの作成（必要に応じて）
   - デフォルトのパスは `data/kabusys.duckdb` と `data/monitoring.db`
   - 必要であれば環境変数 DUCKDB_PATH / SQLITE_PATH で変更可能

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env の作成 / 更新）
  - python -m kabusys.config_setup
  - 対話的に入力し、最終確認で `y` を選択すると .env が保存されます。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit(1) の失敗扱いになります

- 実行エンジン（1セッションを実行）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV が paper_trading または development の場合は MockBrokerClient が使われます（デフォルト）。
    - KABUSYS_ENV=live の実動作クライアントは未実装（BrokerClientFactory は NotImplementedError を投げます）。
    - 停止フラグ: プロジェクトの data/stop_requested.flag を作成するとループを終了します。
    - PID ファイル: data/execution.pid（デフォルト）。KILL フラグや PID の挙動に注意してください。

- 監視ループ（SystemMonitor の定期実行）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は sqlite（settings.sqlite_path）および duckdb（settings.duckdb_path）を使用します。

- テスト用の Mock クライアント
  - create_broker_api(mock=True, fill_mode=...) で MockBrokerClient を生成可能
  - paper_trading の場合は Settings.paper_fill_mode（instant|partial|never|reject）で挙動が変わります

## 主要環境変数

- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- よく使う任意 / デフォルトあり:
  - KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite（監視DB）パス（デフォルト: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定（本番で必須と推奨）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1、デフォルト 0）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

- .env 読み込みの優先順位:
  - OS 環境変数 > .env.local > .env
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

## ディレクトリ構成（src/kabusys の主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env 自動ロード、Settings クラス
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — .env / config/*.yaml 検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - data/
    - calendar_management.py
    - news_collector.py
    - (jquants_client など外部連携モジュールを想定)
  - execution/
    - broker_api.py         — Protocol / データモデル / 例外 / factory
    - broker_factory.py     — Settings に応じたクライアント生成
    - kabu_client.py        — kabu station 実装（httpx + websocket）
    - mock_client.py        — テスト用モック
    - order_record.py       — 注文状態のビジネスロジック
    - order_repository.py   — SQLite 永続化
    - order_manager.py      — 発注フロー（create/send/sync/cancel）
    - execution_engine.py   — セッション制御・シグナル処理・push ドレイン
    - reconciler.py         — リコンシリエーション / 再起動復旧
    - risk_manager.py       — Gate1/2/3 のリスクガード
  - monitoring/
    - monitoring_db.py      — 監視用 SQLite スキーマ / ログ書き込み
    - system_monitor.py     — 監視ロジック（リソース閾値等）
  - utils/
    - logging_setup.py      — ロギング初期化
    - process_priority.py   — プロセス優先度設定
  - config/                 — 設定ファイル群（system_config.yaml 等）
    - system_config.yaml
    - data_config.yaml
    - strategy_config.yaml
    - risk_config.yaml
    - execution_config.yaml
    - monitoring_config.yaml

実際のリポジトリでは上記以外にも補助スクリプト（scripts/generate_config.py 等）が存在する可能性があります。validate_config は config/*.yaml の存在と YAML パースを確認し、PyYAML が無い場合はパース検証をスキップします。

## 実行上の注意点 / 運用メモ

- KABUSYS_ENV=live を設定すると本番モードになります。validate_config は live のときに LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告を出します。本番での起動前には必ず設定検証を実行してください。
- kill.flag（デフォルト: data/kill.flag）の存在は ExecutionEngine の起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合のみ起動時に自動クリアされます）。
- stop_requested.flag（data/stop_requested.flag）は run_execution / run_monitoring のランタイム停止トリガーとして利用されます。
- Order 管理はデータベース（SQLite）で永続化され、クラッシュ耐性を考慮した二相的な永続化ロジックが組まれています（OrderSent 状態の扱いなど）。リコンシリエーション機能でクラッシュ後に状態回復を試みます。
- MockBrokerClient を使ったテストがしやすく設計されています。paper_trading モードで実行すると実取引を行わず専用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます（本番DBと分離可能）。

## よくあるコマンドまとめ

- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring

---

質問や README の補足（例: .env の具体的なサンプル、requirements.txt の生成、運用手順の自動化）をご希望であれば教えてください。必要に応じて README を追記・修正します。