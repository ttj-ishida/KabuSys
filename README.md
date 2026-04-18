KabuSys
=======

日本株向け自動売買システムのライブラリ / 起動スクリプト群です。  
このリポジトリは、発注エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI（ニュースNLP / レジーム判定）などを含むモジュール群を収めています。

概要
----
- Pythonパッケージとして各コンポーネント（execution / monitoring / portfolio / research / ai / utils 等）を提供します。
- 実運用を想定した設計（本番 / ペーパートレード分離、Kill Switch、監視ログ、ログローテーション等）を備えています。
- DuckDB / SQLite を用いたデータ分析・永続化、OpenAI を利用したニュースセンチメントなどの補助機能を提供します。

主な機能
--------
- ExecutionEngine（発注エンジン）起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB に記録して本番 DB と分離
  - プロセス優先度の設定、PID ファイル管理、停止フラグ対応
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine と個別モニタ
  - 監視ログを SQLite（デフォルト data/monitoring.db）へ永続化
  - KillSwitch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止）
- Portfolio（銘柄選定・配分・ポジションサイズ算出）
  - 候補選定、等金額／スコア加重配分、リスク調整（セクターキャップ・レジーム乗数）、株数算出（単元丸め）
- Research（ファクター計算・特徴量探索）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続で SQL を実行）
  - 将来リターン計算、IC（情報係数）、統計サマリ等
- AI
  - news_nlp: raw_news を OpenAI へ送り銘柄ごとのセンチメントを ai_scoresへ書き込む
  - regime_detector: ETF の MA乖離 と マクロニュースセンチメントを合成して market_regime を算出・永続化
- ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前設定検証 CLI
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成

前提・依存
-----------
- Python 3.10+（type union 演算子 `|` を使用しているため）
- 外部ライブラリ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の内容検証は任意。インストールされていない場合は警告）
- 必要な環境変数（詳細は下記参照）

セットアップ手順
--------------
1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai
   - （検証時に YAML を読みたい場合）pip install pyyaml

   ※ requirements.txt がある場合はそれを使用してください（本リポジトリには付属していない想定）。

3. .env を用意する
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（下に最低限の例を示します）。

4. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告も致命的扱いにしたい場合は --strict を付与

5. データディレクトリの確認
   - デフォルトの DB / ファイルパスは data/ 配下や logs/ などになります。必要に応じて .env で上書きしてください。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- OPENAI_API_KEY — AI 機能を使う場合に必要
- PAPER_FILL_MODE (paper_trading 用): instant | partial | never | reject (デフォルト "instant")
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: デフォルト data/paper_trading.db
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- LOG_DIR: ログ出力先（デフォルト logs/）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（1=クリアする。production では通常 0）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

.example .env（抜粋）
-------------------
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

使い方
------
- 環境構築（.env 作成）
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 sqlite（PAPER_TRADING_SQLITE_PATH）を使用
    - 起動時に data/execution.pid を書き、停止は data/stop_requested.flag（もしくは監視側の kill.flag）で指示可能

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を秒で上書き可能（デフォルト 60 秒）
  - 監視は常に（KABUSYS_ENV にかかわらず）本番 sqlite_path を使用して監視ログを一元管理

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する場合:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能（プログラム的利用）
  - ニュースセンチメント評価:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn=duckdb_conn, target_date=date(2026,4,1), api_key=os.environ.get("OPENAI_API_KEY"))
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn=duckdb_conn, target_date=date(2026,4,1))

- ログ
  - ログは logs/<app_name>.log に日次ローテートで出力されます（app_name は "execution"/"monitoring" 等）。
  - コンソール出力は stdout に出ます。

停止・Kill Switch
-----------------
- 手動停止フラグ:
  - data/stop_requested.flag を作成すると run_execution と run_monitoring のループはそれを検知して停止（run_execution は起動時に既に存在するとエンジンを起動しません）。
- Kill Switch:
  - 監視が条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine に対する停止シグナルの発行やアラート送信が行われます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ディレクトリ構成（主要ファイル）
-------------------------------
（src 以下をパッケージ化している想定。実際のツリーはプロジェクトルートに src/ を含む）

- src/kabusys/
  - __init__.py              — パッケージ定義（バージョン等）
  - config.py                — 環境変数読み込み・Settings 定義（自動 .env ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - execution/               — 発注エンジン関連（Engine, OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - ... その他ユーティリティ

注意事項 / 運用上のヒント
------------------------
- KABUSYS_ENV により DB の扱いが変わる（paper_trading では paper_trading 用 DB を使い本番と分離）。
- OpenAI API を利用する機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライ・フェイルセーフ設計になっていますが、キー未設定ならエラーになります。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数（秒）で周期を変更できます。不正値（0 や負数、非数）は無視されデフォルト 60 秒となります。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（FileHandler のみ無効化されます）。
- プロセス優先度設定はプラットフォーム依存で、権限不足時は警告になり設定がスキップされます。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

貢献 / 拡張ポイント
-------------------
- Broker クライアント実装や実際の ExecutionEngine ロジックの増補
- 銘柄毎の lot_size マスタ追加（position_sizing の拡張）
- AI プロンプト・バッチ戦略の改善、モデル選択のパラメタ化
- テストカバレッジ増強（ユニット / 統合テスト）

問い合わせ
----------
- 質問や不具合報告はリポジトリの Issue へお願いします。README の追記・改善提案も歓迎です。

以上。README に載せてほしい追加のコマンド例や、特定モジュール（たとえば ExecutionEngine の起動オプションの詳細など）があれば教えてください。必要に応じてサンプル .env ファイルや起動スクリプトの systemd ユニット例も作成します。