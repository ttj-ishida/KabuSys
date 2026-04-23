KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買（Execution）・監視（Monitoring）・データ取り込み（Data）を目的とした小規模なシステム群です。  
設計方針としては「DB による永続化」「再起動時の自動復旧（Reconciliation）」「本番とペーパートレードの分離」「複数段階のリスクガード」を重視しています。

主な特徴
--------
- 環境設定ウィザード（.env 生成）と起動前設定検証 CLI
- ExecutionEngine：Signal Queue ベースの発注エンジン（シグナル処理 + WebSocket push ドレイン）
- Broker クライアント抽象化（MockBrokerClient を用いたペーパートレード対応）
- 注文状態管理（OrderRecord の状態遷移制御）および SQLite 永続化（OrderRepository）
- 起動時リコンシリエーション（Reconciler）で OrderSent 状態の同期・ポジション差分検出
- RiskManager：Gate1/2/3 による余力・重複・レート制限・サーキットブレーカー・ドローダウン保護
- Monitoring：監視ループ（SQLite / DuckDB を使用）
- Data：マーケットカレンダー管理、RSS ニュース収集などのユーティリティ

動作前提（主な環境変数）
-----------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
- PAPER_FILL_MODE — paper_trading 時のモック約定動作（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1、デフォルト 0）

セットアップ手順
---------------
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール（プロジェクトに requirements.txt がある場合はそれを使用）
   - 主要に使用されるライブラリ（例）:
     - duckdb
     - httpx
     - websocket-client
     - pyyaml (config 検証用、任意)
     - defusedxml (RSS パーサで使用)
   - 例:
     pip install duckdb httpx websocket-client pyyaml defusedxml

3. .env の用意
   - 対話式ウィザードで .env を作成:
     python -m kabusys.config_setup
   - ウィザードで必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を入力してください。

4. 設定検証（起動前確認）
   - 登録した .env の妥当性と config/*.yaml の存在/パースをチェック:
     python -m kabusys.validate_config
   - 警告も FAIL として扱う場合:
     python -m kabusys.validate_config --strict

使い方（起動例）
----------------
- ExecutionEngine（発注エンジン）を起動:
  - ペーパートレードで実行（例）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行中の停止要求:
    data/stop_requested.flag ファイルを作成するとエンジンはグレースフルに停止します。
  - kill.flag によるキルスイッチ:
    data/kill.flag を配置すると ExecutionEngine は kill_switch を参照して全 active 注文をキャンセルします。
    KILL_FLAG_CLEAR_ON_START=1 が設定されている場合、起動時に kill.flag を自動でクリアします（注意: 本番では 0 推奨）。

- Monitoring（監視ループ）を起動:
  python -m kabusys.run_monitoring
  - ポーリング間隔を変更:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 設定ウィザード（.env の作成・更新）:
  python -m kabusys.config_setup

- 設定検証（起動前）:
  python -m kabusys.validate_config
  --strict オプションで警告も失敗扱いにできます。

設計上のポイント・注意点
-----------------------
- 本番接続（KABUSYS_ENV=live）は保守的に取り扱われ、現状では Live broker client は未実装で NotImplementedError が投げられる設計です。開発・検証は paper_trading / development を利用してください。
- Paper trading は MockBrokerClient を使い、実際の発注は行われません。本番 DB と分離して paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録する設計です。
- 発注フローはクラッシュ耐性を考慮した二相的永続化（OrderSent 状態の永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 更新）を採用しています。起動時の Reconciler により OrderSent の同期を行います。
- リスク管理は 3 段階（Gate1: シグナルレベル、Gate2: エグゼキューションレベル、Gate3: 約定後メトリクス）で保護します。サーキットブレーカーやレート制限、ドローダウン監視が組み込まれています。
- DB ファイルや PID ファイルの親ディレクトリが存在しない場合、起動時に自動作成される箇所がありますが、事前に data ディレクトリ等を用意しておくと安全です。

ディレクトリ構成（主要ファイル）
--------------------------------
プロジェクトルート（抜粋）:
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/  (データベース・フラグ・PID ファイル等を格納する想定ディレクトリ)
- src/kabusys/
  - __init__.py
  - config.py                (環境変数ロード / Settings)
  - config_setup.py          (.env 対話式ウィザード)
  - validate_config.py       (設定検証 CLI)
  - run_execution.py         (Execution 起動スクリプト)
  - run_monitoring.py       (Monitoring 起動スクリプト)
  - execution/
    - __init__.py
    - broker_api.py          (Protocol / データモデル / ファクトリ)
    - kabu_client.py         (kabu station REST 実装)
    - mock_client.py         (テスト用モック)
    - broker_factory.py      (Settings からクライアント生成)
    - order_record.py        (注文状態モデル・遷移)
    - order_repository.py    (SQLite 永続化)
    - order_manager.py       (注文フロー制御)
    - execution_engine.py    (ExecutionEngine 本体)
    - reconciler.py          (起動時リコンシリエーション)
    - risk_manager.py        (Gate1/2/3 リスクガード)
    - ...（その他モジュール）
  - data/
    - calendar_management.py (マーケットカレンダー管理）
    - news_collector.py      (RSS ニュース収集）
    - jquants_client.py      (J-Quants API クライアント) — 利用想定
  - monitoring/
    - monitoring_db.py      (監視 DB 初期化/ログ)
    - system_monitor.py     (システム監視ロジック)
  - utils/
    - logging_setup.py      (ログ設定)
    - process_priority.py   (プロセス優先度設定)
  - strategy/ (戦略関連のコード置き場を想定)

よく使うコマンドまとめ
---------------------
- .env ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動:
  python -m kabusys.run_monitoring

補足
----
- config/*.yaml の内容検証には PyYAML が必要です。インストールされていない場合、validate_config は YAML 内容検証をスキップして警告を出します。
- ネットワーク接続や外部 API（kabu station / J-Quants）を利用するため、実稼働環境では接続先の準備と認証情報管理に注意してください。
- 本 README はコードベースから読み取れる動作と意図を要約したものです。詳細な設定項目・チューニングは該当モジュールのドキュメント／ソースコメントを参照してください。

以上。必要に応じて「起動手順をシェルスクリプト化する」「requirements.txt を追加する」「config/*.yaml のテンプレート生成方法」を追記できます。どの情報を優先して詳細化しますか？