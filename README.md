# KabuSys

日本株自動売買システム（簡易版） — このリポジトリは発注エンジン、リスクガード、監視、環境設定ユーティリティを含むモジュール群を提供します。

注意: README は提供されたコードベースに基づく概要ドキュメントです。実行前に .env を作成し、設定検証を行ってください。

## 概要

KabuSys は以下の主要機能を備えた自動売買基盤のプロトタイプです。

- シグナルに基づく発注エンジン（ExecutionEngine）
- 注文状態管理（OrderRecord / OrderManager）
- ブローカークライアント抽象化（Mock / kabu station クライアント）
- 起動時リコンシリエーション（Reconciler）
- 3段階リスクガード（Gate1/Gate2/Gate3）
- 監視ループ（SystemMonitor をポーリング）
- 環境設定ウィザード（.env 作成支援）と設定検証 CLI
- マーケットカレンダー管理、RSS ニュース収集などのデータ処理ユーティリティ

設計方針として DB（SQLite / DuckDB）は発注履歴・監視・分析に利用され、MockBrokerClient により kabuステーションがなくてもペーパートレードが可能です。

## 主な機能一覧

- config_setup.py: 対話式ウィザードで .env を生成・更新
- validate_config.py: .env と config/*.yaml の起動前検証（--strict で警告も失敗扱い）
- run_execution.py: ExecutionEngine の起動スクリプト（ペーパートレード / 開発モードで MockBroker を使用）
- run_monitoring.py: SystemMonitor を定期ポーリングして監視データを記録
- execution パッケージ:
  - 注文のライフサイクル（OrderRecord / OrderRepository / OrderManager）
  - Broker API 抽象（BrokerAPIProtocol / create_broker_api）
  - KabuStationClient（実際の kabu station API 呼び出し実装）
  - MockBrokerClient（テスト用）
  - リスク管理（RiskManager）
  - リコンシリエーション（Reconciler）
  - ExecutionEngine（シグナル読み込み・発注・push ドレイン・kill switch）
- data パッケージ:
  - calendar_management: 営業日判定、next_trading_day 等
  - news_collector: RSS 収集と前処理（SSRF 対策、トラッキング除去、記事ID生成）
- config モジュール: .env 自動ロード（.env, .env.local）・Settings クラス
- ログ設定、プロセス優先度設定ユーティリティ等

## セットアップ手順（開発環境想定）

1. リポジトリをクローンして依存をインストールします（実行環境に合わせて適宜調整してください）。

   例（pip）:
   pip install -r requirements.txt

   依存（主なもの）
   - python >=3.9
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML（config の YAML 検証に必要。必須ではない）
   - その他: sqlite3 は標準ライブラリ

   （注）requirements.txt が無い場合は上記パッケージを個別にインストールしてください。

2. プロジェクトルートに移動して .env を作成します。

   対話式ウィザードを使う:
   python -m kabusys.config_setup

   ウィザードは既存の .env を読み込み、デフォルト・既存値を表示します。保存した .env は Git にコミットしないでください。

3. 設定を検証する:
   python -m kabusys.validate_config
   警告も失敗扱いにする:
   python -m kabusys.validate_config --strict

   validate_config は .env の必須環境変数未設定や config/*.yaml の欠落・YAML パースエラーなどをチェックします。PyYAML がない場合は YAML 内容の検証をスキップします。

4. データディレクトリ（デフォルト: data/）を作成します（自動作成される場合もありますが念のため）:
   mkdir -p data

5. 実行（ペーパートレード / 開発）:
   python -m kabusys.run_execution

   監視ループ:
   python -m kabusys.run_monitoring

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  python -m kabusys.config_setup
  オプション:
    --env-file /path/to/.env  （デフォルトはプロジェクト直下の .env）

- 設定検証
  python -m kabusys.validate_config
  オプション:
    --strict  （警告も exit 1）

- 実行エンジン起動
  python -m kabusys.run_execution
  補足:
    - KABUSYS_ENV によって動作が変わる:
      - development / paper_trading: MockBrokerClient を使用（paper_trading は paper DB を使用）
      - live: 現状 Live broker client は未実装（BrokerClientFactory が NotImplementedError を投げます）
    - 起動中は data/execution.pid（デフォルト）に PID を書き出します
    - 停止: data/stop_requested.flag を作成すると安全に停止できます
    - kill スイッチ: settings.kill_flag_path（デフォルト data/kill.flag）が存在すると起動を拒否または発動 (KILL_FLAG_CLEAR_ON_START による挙動差あり)

- 監視ループ起動
  python -m kabusys.run_monitoring
  補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60）
    - 監視は設定にかかわらず「本番 sqlite_path」を使用します（監視データは常に指定された sqlite path に格納）

## 主要環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨（例）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- KABU_API_BASE_URL: kabu station API の base URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知用（本番では設定推奨）
- KILL_FLAG_CLEAR_ON_START: 0（デフォルト）|1（起動時に kill.flag を自動クリア）
- MONITOR_POLL_INTERVAL: 監視ループの間隔（秒）

特記事項:
- .env の読み込み順: OS 環境変数 > .env.local > .env（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
- PAPER_FILL_MODE: ペーパートレード用の約定モード（instant | partial | never | reject）

例 (.env の抜粋)
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

（.env.example を参考に実際の値を設定してください。プレースホルダは validate_config で警告されます）

## 停止・安全機構

- stop flag: data/stop_requested.flag を作成すると run_execution / run_monitoring 中のメインループが検出して終了します。
- kill flag: settings.kill_flag_path（デフォルト data/kill.flag）が存在すると、ExecutionEngine は起動を拒否するか（clear_on_start=0）、kill スイッチを発動します。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアして起動します（本番では 0 を推奨）。
- PID ファイル: 実行時に PID が書かれます（実行中の二重起動防止等に利用可能）。

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイル・パッケージです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 — .env 自動読み込みと Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングスクリプト
  - execution/
    - __init__.py
    - broker_api.py           — BrokerAPIProtocol / データモデル / ファクトリ
    - broker_factory.py       — Settings に基づいて Broker クライアント生成
    - kabu_client.py          — kabu station HTTP/WebSocket 実装
    - mock_client.py          — MockBrokerClient（テスト用）
    - order_record.py         — OrderRecord（状態遷移ロジック）
    - order_repository.py     — SQLite 永続化ロジック
    - order_manager.py        — 発注フロー（create/send/sync/cancel）
    - execution_engine.py     — セッション実行ロジック（シグナル処理・push drain）
    - reconciler.py           — リコンシリエーション
    - risk_manager.py         — 3段階リスクガード（Gate1/2/3）
  - data/
    - calendar_management.py  — 営業日管理・calendar 更新ジョブ
    - news_collector.py       — RSS 収集と前処理
  - monitoring/                — 監視関連（監視DB 初期化, SystemMonitor 等） ※一部省略
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ（起動スクリプトで使用）
    - process_priority.py     — プロセス優先度設定ユーティリティ

（実際のリポジトリでは上記以外にも補助モジュールが存在する可能性があります）

## 実行上の注意事項・制限

- Live broker client（本番の kabu station を直接操作するクライアント）は現状未実装です。KABUSYS_ENV=live を指定すると NotImplementedError が発生します。
- config/*.yaml の検証には PyYAML が必要です。未インストール時は validate_config が YAML の検証をスキップして警告を出します。
- ExecutionEngine の時間帯ロジック（シグナル送信時間 / 市場終了時間）は EngineConfig で設定可能です（デフォルト 8:50–9:10 / 15:30 終了）。
- データベースファイル（DuckDB / SQLite）はデフォルトで data/ 配下に作成されます。パスは環境変数で変更できます。
- .env は秘匿情報を含むため Git にコミットしないでください（config_setup.py も同様に注意喚起あり）。

## 開発・デバッグのヒント

- MockBrokerClient を使えば外部の kabu station が不要で単体テストやローカル実行が可能です。PAPER_FILL_MODE によって約定挙動（即時/部分/保留/拒否）を切替可能です。
- validate_config.py の --strict を CI に組み込むことで設定の品質チェックを自動化できます。
- run_execution.py および run_monitoring.py は stop flag / kill flag に反応するため、自動停止・安全シャットダウンのテストが容易です。
- Reconciler は起動時に OrderSent（不確定）状態の注文をブローカーと照合して自動回復を試みます。リコンシリエーションは安全に運用を再開するために重要です。

---

この README はコードベースの要点をまとめたものです。より詳細な内部設計や API 仕様、運用手順は各モジュールの docstring とコードコメントを参照してください。必要であれば、追加のドキュメント（設計図、運用手順、デプロイ手順）を作成します。