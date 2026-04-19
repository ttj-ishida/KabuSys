KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。銘柄選定・配分・発注・監視・レポーティング・リサーチ用の機能群を含み、実運用（live）／ペーパートレード（paper_trading）／開発（development）を切り替えて使えます。

主要な設計方針（抜粋）
- DB 層: 分析用に DuckDB、監視・発注ログに SQLite を利用
- 環境管理: .env を用いた環境変数経由の設定（config_setup で対話的作成可）
- 監視: Monitoring コンポーネントが稼働状況・データ鮮度・リスク監視を実施
- 安全策: Kill Switch（データ駆動で ExecutionEngine を停止）や stop フラグでプロセス停止
- AI: ニュースセンチメントや市場レジーム判定に OpenAI（gpt-4o-mini）を利用可能（APIキー必須）
- ペーパートレード: KABUSYS_ENV=paper_trading 時は本番 DB から完全分離（data/paper_trading.db）

機能一覧
---------
- 実行エンジン（ExecutionEngine）
  - ブローカークライアントを介した発注管理、リスク管理、注文リコンサイル
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使用し paper_trading DB へ記録
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・実行プロセス検出
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限監視
  - MonitoringEngine: 各 Monitor を統合しポーリング、アラート送信・Kill Switch 制御
- 環境設定支援
  - 対話式ウィザード (.env 作成): python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- ポートフォリオ構築（純関数群）
  - 銘柄候補選定、重み算出、ポジションサイジング、セクターキャップ、レジーム乗数
- リサーチ / ファクター計算
  - Momentum / Volatility / Value の計算。DuckDB 接続を受けて SQL ベースで算出
  - 将来リターン・IC（Information Coefficient）計算など
- AI 支援
  - news_nlp: raw_news をまとめて LLM に送り銘柄別センチメントを ai_scores に保存
  - regime_detector: ETF（1321）MA とマクロニュースを合わせて市場レジームを判定
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

前提・依存
-----------
推奨 Python バージョン: 3.10+
主な依存パッケージ:
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の検証を行う場合に任意）
その他: sqlite3（標準ライブラリ）

セットアップ手順
-----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd repo

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話で必要な環境変数を作成します（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）

5. 設定検証
   - python -m kabusys.validate_config
   - 本番前に --strict を付けて警告も失敗扱いにできます:
     - python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
----------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意/設定項目:
- KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリア、0=しない。production では 0 推奨）

使い方（起動・停止・ツール）
-----------------------------

1) ExecutionEngine を起動（実行エンジン）
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB に記録
  - 起動時に data/execution.pid（デフォルト）へ PID を書く仕組みあり
  - 停止方法:
    - 外部から停止フラグを立てる (プロジェクトルート/data/stop_requested.flag を作成) -> 起動スレッドが検知して停止
    - または監視側の Kill Switch（data/kill.flag）を監視してエンジン停止

2) Monitoring を起動（常時監視プロセス）
- python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用する点に注意
  - 停止方法:
    - data/stop_requested.flag を作成すると監視ループが終了する

3) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB: data/paper_trading.db。環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能

4) 環境設定ウィザード / 検証
- 環境設定作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]

ログ
----
- ログ設定ユーティリティ: kabusys.utils.logging_setup
  - デフォルトは logs/<app_name>.log（日次ローテーション、30日保持）と stdout 出力
  - LOG_DIR 環境変数でログ保存先を変更可
  - 各起動スクリプトは setup_logging(app_name=...) を呼び出しているため、logs/execution.log / logs/monitoring.log 等が生成される

監視・停止フラグ
----------------
- 停止フラグ（stop_requested.flag）
  - run_execution.py / run_monitoring.py がチェックするフラグ: <project_root>/data/stop_requested.flag
  - 存在するとループを終了してプロセスを落とす（安全なシャットダウン）

- Kill Switch（kill.flag）
  - RiskMonitor / KillSwitch により data/kill.flag が書き込まれると ExecutionEngine に停止シグナルを送る仕組み
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリア（production では 0 推奨）

AI 機能について
----------------
- news_nlp / regime_detector は OpenAI API（gpt-4o-mini）を利用
  - OPENAI_API_KEY を環境変数または関数引数で指定してください
  - API 呼び出しはリトライ・エラー耐性あり（429 / ネットワーク断 / 5xx 等に対してエクスポネンシャルバックオフ）
  - 失敗時は安全側にフォールバックして処理を継続する設計

データベース（デフォルトパス）
-----------------------------
- DuckDB: data/kabusys.duckdb
- SQLite（監視）: data/monitoring.db
- SQLite（paper trading）: data/paper_trading.db

主要ディレクトリ構成
--------------------
（src/kabusys 以下の主要ファイル/ディレクトリを抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込み・Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - execution/ (発注関連: BrokerClient, Engine, OrderManager など)
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限チェック
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 各 Monitor を束ねる
    - (その他: trade_monitor, alert_manager 等)
  - portfolio/
    - portfolio_builder.py   — 銘柄選定、重み付け
    - position_sizing.py     — 株数計算・上限・丸め
    - risk_adjustment.py     — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py     — Momentum/Value/Volatility 計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

運用上の注意
-------------
- 本番運用時は KABUSYS_ENV=live を設定し、設定値（API トークン・LINE 通知等）を十分に確認してください。
- Kill Switch / kill.flag の設定（KILL_FLAG_CLEAR_ON_START）は本番では慎重に扱ってください（デフォルト 0 推奨）。
- Monitoring は常に本番用の monitoring DB（SQLITE_PATH）を使用します。テスト用 DB と混同しないでください。
- AI 機能を使用すると API コストが発生します。利用範囲・頻度に注意してください。

よくあるコマンド早見表
---------------------
- .env 作成（対話式）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動:
  - python -m kabusys.run_execution

- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 拡張
----------------
- 新しいブローカープラグインや戦略を追加する場合は execution/ と strategy/（未表示）を拡張してください。
- DuckDB のテーブルスキーマや config/*.yaml の仕様はプロジェクト内ドキュメント（PortfolioConstruction.md 等）に準拠してください。

ライセンス・バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ で参照できます（現状: 0.1.0）
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

―――
この README はコードベース（src/kabusys 以下）を元に作成しています。補足的な運用手順やデプロイ手順（systemd / container / supervisor）を追加する場合は運用環境に合わせたドキュメントを別途用意してください。