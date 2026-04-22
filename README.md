# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README。  
このドキュメントはプロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

概要
---
KabuSys は日本株向けの自動売買フレームワークです。  
主な目的は以下です：

- シグナルに基づく発注処理（ExecutionEngine）
- 発注の状態管理と永続化（SQLite）
- 発注・ポジションのリコンシリエーション（再起動後の自動復旧）
- 監視コンポーネントによるプロセス・システムメトリクスの記録
- テスト用の Mock ブローカー（paper_trading / development 向け）

設計上、API クライアント層は kabuステーション（KabuStation）向けの実装とモック実装を提供し、ExecutionEngine は BrokerAPIProtocol に依存することでテスト容易性を保っています。

主な機能
---
- 環境設定ウィザード（.env の対話的作成・更新）
  - python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の起動前チェック）
  - python -m kabusys.validate_config [--strict]
- 実行エンジン（ExecutionEngine）の起動スクリプト
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は Mock ブローカーを使用
- 監視ループ（SystemMonitor）起動スクリプト
  - python -m kabusys.run_monitoring
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- ブローカー API 抽象化（BrokerAPIProtocol）
  - MockBrokerClient / KabuStationClient（将来的に Live 実装）
- リスク管理（3 段階ガード: Gate1/2/3）
- カレンダー管理（J-Quants 由来のマーケットカレンダーを利用）
- ニュース収集（RSS を収集・前処理して DB に保存）

セットアップ手順
---
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb httpx websocket-client defusedxml
   - （開発／オプション）
     - PyYAML（config/*.yaml の構文チェックを有効化する場合）
       - pip install pyyaml

   必要な主なパッケージ（一覧）
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML（任意、validate_config の YAML 検証用）
   - その他、環境や用途に応じて追加パッケージが必要になる場合があります。

4. 環境変数（.env）を準備
   - 対話式ウィザードで作成（推奨）:
     - python -m kabusys.config_setup
   - または .env を手動作成（プロジェクトルートに配置）
   - .env は Git にコミットしないでください（README とウィザードでも注意喚起あり）。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

オプション / よく使う環境変数
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABU_API_BASE_URL — kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時の kill.flag 自動クリア（0/1）

注意:
- 自動で .env を読み込む挙動は、OS 環境変数 > .env.local > .env の優先順です。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用途など）。

使い方（主要コマンド）
---
1. 設定ウィザード（.env の作成・更新）
   - python -m kabusys.config_setup
   - 対話的に入力して .env を生成します。

2. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）になります。
   - PyYAML がインストールされている場合、config/*.yaml の構文チェックも実行します。
   - 返却コード:
     - 0: OK
     - 1: エラー（または strict で警告あり）

3. 実行エンジン起動（本番／ペーパートレード）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 SQLite を使用して本番 DB と分離します。
   - 停止方法:
     - プロセス外から data/stop_requested.flag を作成するとループが検出して停止します。
     - また kill.flag（settings.kill_flag_path）により起動拒否や kill switch が発動します。

4. 監視プロセス起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
   - 監視は KABUSYS_ENV に依存せず、本番 sqlite を使用します。

5. テスト／開発
   - 設定で KABUSYS_ENV=development または paper_trading を選ぶと MockBrokerClient が利用され、kabu station 実体は不要です。
   - MockBrokerClient は fill_mode により instant/partial/never/reject を模擬できます（settings.paper_fill_mode）。

動作の注意点
- PID / フラグファイル:
  - PID: data/execution.pid（Execution は起動時に PID を書き出します）
  - stop フラグ: data/stop_requested.flag（存在で監視/実行ループを終了）
  - kill フラグ: settings.kill_flag_path（デフォルト data/kill.flag）
- .env を絶対にリポジトリにコミットしないでください（秘密情報が含まれる）。
- validate_config は起動前に潜在的な設定ミスを検出するために便利です。
- KABUSYS_ENV=live を使う場合は本番リスクを十分認識し LINE 通知などの設定を確認してください（validate_config で警告されます）。

ディレクトリ構成
---
（プロジェクトルートの src/kabusys を抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                   — 環境変数読み込みと Settings
    - config_setup.py             — .env 対話式ウィザード CLI
    - validate_config.py          — 起動前設定検証 CLI
    - run_execution.py            — ExecutionEngine 起動スクリプト
    - run_monitoring.py           — SystemMonitor 起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py             — Broker 抽象、データモデル、ファクトリ
      - broker_factory.py         — Settings に基づくクライアント生成
      - kabu_client.py            — kabu station 実装（HTTP/WebSocket）
      - mock_client.py            — MockBrokerClient（テスト用）
      - order_record.py           — 注文状態モデルと遷移ロジック
      - order_repository.py       — SQLite 永続化（orders テーブル）
      - order_manager.py          — 発注フロー制御（作成・送信・同期・取消）
      - execution_engine.py       — セッション制御・シグナル処理・push drain
      - reconciler.py             — 起動時リコンシリエーション
      - risk_manager.py           — Gate1/2/3 のリスク統制
    - data/
      - calendar_management.py    — マーケットカレンダー管理
      - news_collector.py         — RSS ニュース収集（raw_news 保存）
      - jquants_client.py         — （別ファイル想定）J-Quants API クライアント
    - monitoring/
      - monitoring_db.py         — 監視 DB 初期化とログ記録
      - system_monitor.py        — システムメトリクス監視ロジック
    - utils/
      - logging_setup.py         — ロギング初期化ユーティリティ
      - process_priority.py      — プロセス優先度設定ユーティリティ
    - config/                    — YAML 設定ファイル群（system/data/strategy/...）
      - system_config.yaml
      - data_config.yaml
      - strategy_config.yaml
      - risk_config.yaml
      - execution_config.yaml
      - monitoring_config.yaml
- data/                         — 実行時に生成される DB / フラグ / PID など（既定）

補足（よくある質問）
---
- Q: validate_config の --strict は何をする？  
  A: 警告（WARNING）を FAIL 扱いにして exit code 1 で終了します。CI 等で厳密にチェックしたい場合に有用です。

- Q: .env 自動読み込みの挙動は？  
  A: OS 環境変数が最優先で、次に .env.local（上書き可能）、最後に .env（未上書き）を読み込みます。テスト等で自動ロードを停止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Q: 本番接続（Live）での実装はある？  
  A: 現在、KabuStationClient は実装されていますが、BrokerClientFactory.create は live の場合 NotImplementedError を投げます。live 運用をする際は実装と十分な検証が必要です。

- Q: DB の初期化は必要？  
  A: run_execution / run_monitoring は起動時に必要なテーブル作成関数（init_monitoring_db、init_orders_db 等）を呼び出す部分がありますが、初回起動前に data ディレクトリを作成しておくことを推奨します（スクリプトで自動作成される箇所もあります）。

ライセンス・貢献
---
（ここにプロジェクト固有のライセンスや貢献に関する説明を追加してください）

---

この README はコードベース（src/kabusys/*）を参照して作成されています。実行や運用前に必ず validate_config で設定を検証し、.env の秘密情報は安全に管理してください。必要であればこの README を README.md としてプロジェクトルートに配置してください。