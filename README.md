KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買基盤ライブラリ／実行スクリプト群です。  
主にシグナルに基づく発注エンジン（ExecutionEngine）、起動時のリコンシリエーション、監視（SystemMonitor）、および環境設定ウィザード／検証ツールを備えます。  
設計上、データ層（DuckDB / SQLite）とブローカークライアント（実ブローカー／モック）を分離し、ペーパートレード運用をサポートします。

主な機能
--------
- 環境設定ウィザード（.env の対話式作成 / 更新）
  - python -m kabusys.config_setup
- 起動前設定検証ツール（.env と config/*.yaml の存在と内容チェック）
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗扱い
- 実行エンジン（ExecutionEngine）
  - シグナルプル → Gate1/Gate2 リスクチェック → 発注 → リスク記録／監視
  - WebSocket プッシュのドレイン（push 通知で状態同期）
  - ペーパートレード時は MockBrokerClient を使用（本番ブローカーは未実装）
  - python -m kabusys.run_execution
- 監視ループ（SystemMonitor のポーリング）
  - MONITOR_POLL_INTERVAL 環境変数で間隔指定（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
- ブローカー抽象化層（BrokerAPIProtocol）
  - 実装: MockBrokerClient（テスト用）および KabuStationClient（kabuステーション向け）
- 発注状態管理（OrderRecord / OrderManager / OrderRepository）
  - DB永続化（SQLite）と状態遷移の検証
- リスク管理（RiskManager）
  - Gate1: シグナルレベル（余力・重複・ポジション上限）
  - Gate2: レート制限・サーキットブレーカー
  - Gate3: ドローダウン監視（発注後）

前提 / 推奨環境
--------------
- Python 3.10+
  - （コードで PEP 604 記法（|）等を使用しているため）
- 必須ライブラリ（実行に応じて）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml をパースして検証する場合に推奨）
- 標準ライブラリ: sqlite3, logging など

セットアップ手順（簡易）
---------------------
1. リポジトリをクローン:
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール（例）:
   - pip install duckdb httpx websocket-client defusedxml PyYAML

   実際のプロジェクトでは requirements.txt / pyproject.toml を用意しているはずです。ない場合は上記パッケージを適宜追加してください。

4. .env を作成:
   - 推奨: ウィザードで対話的に作成
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成（後述の必須環境変数を設定）

5. 設定を検証:
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合:
     - python -m kabusys.validate_config --strict

必須 / 主要な環境変数
--------------------
最低限セットする必要がある値:
- JQUANTS_REFRESH_TOKEN  — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD      — kabuステーション API パスワード（必須）

その他よく使う環境変数:
- KABUSYS_ENV            — 実行環境: development / paper_trading / live
  - paper_trading: MockBroker を利用（本番 API へは発注しない）
  - live: 本番（注意喚起あり。現状 Live broker client は未実装の箇所あり）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite DB（デフォルト data/monitoring.db）
- LOG_LEVEL              — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABU_API_BASE_URL      — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（任意）

.env 自動読み込みの挙動
----------------------
- 起動時、OS 環境変数 > .env.local > .env の優先順位で自動ロードが行われます。
- 自動ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください（テスト用など）。

主要コマンド / 使い方
--------------------
- 環境設定ウィザード（対話式 .env 作成）:
  - python -m kabusys.config_setup
  - オプション: --env-file PATH（保存先の .env を指定）

- 設定検証（起動前チェック）:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit code 1）扱いになります

- 実行エンジンを起動（1 セッション実行）:
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV が paper_trading または development の場合は MockBrokerClient を使います。live は未実装の可能性があります。

- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）

運用上の注意
------------
- .env は秘密情報を含むため絶対に Git にコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。
- KABUSYS_ENV=live を設定すると本番動作になるため、LINE 通知設定や KILL_FLAG 等を十分に確認してください。validate_config は live の場合に追加チェックを行います。
- Paper trading は MockBroker により本番 DB と分離して動作します（paper_trading 用の SQLite は PAPER_TRADING_SQLITE_PATH／デフォルト data/paper_trading.db）。
- kill flag（デフォルト data/kill.flag）や pid ファイル（data/execution.pid）を利用して安全に停止・起動できます。KILL_FLAG_CLEAR_ON_START=1 に注意（本番では 0 推奨）。

ディレクトリ構成（抜粋）
---------------------
プロジェクトの主要ファイルとモジュール（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み／Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングスクリプト
  - execution/
    - broker_api.py          — BrokerAPI プロトコル / データモデル / ファクトリ
    - kabu_client.py         — kabuステーション向け実装（HTTP/WebSocket）
    - mock_client.py         — テスト用モック実装
    - broker_factory.py      — Settings に基づくブローカー生成
    - order_record.py        — 注文状態と遷移ロジック（純粋ビジネスロジック）
    - order_repository.py    — SQLite 永続化層
    - order_manager.py       — 発注フロー（create/send/sync/cancel）
    - execution_engine.py    — 実行エンジン本体（シグナル処理／push ドレイン）
    - reconciler.py          — 起動時リコンシリエーション
    - risk_manager.py        — Gate1/2/3 リスク管理
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集
  - monitoring/
    - monitoring_db.py       — 監視 DB 初期化・操作（SQLite）
    - system_monitor.py      — システム監視ロジック
  - utils/
    - logging_setup.py       — ロギング初期化
    - process_priority.py    — プロセス優先度設定

補足 / 将来の実装メモ
-------------------
- Live ブローカー実装（KabuStationClient の本番向け検証・完全実装）が未実装／要確認の箇所があります。現在の設計は paper_trading（モック）を第一にサポートしています。
- config/*.yaml（system_config.yaml 等）はプロジェクト設定用です。validate_config は PyYAML があれば YAML をパースして検証します。config ファイル生成スクリプト（scripts/generate_config.py）への言及がコード中にあります。必要に応じて生成してください。

ライセンス／貢献
----------------
（ここにプロジェクトのライセンスや貢献方法を記載してください）

以上。初期セットアップとしては config_setup を実行して .env を作成 → validate_config でチェック → run_execution/run_monitoring を起動、が典型的な流れです。必要があれば README にインストール済みの依存バージョンや example .env のテンプレートを追加できます。