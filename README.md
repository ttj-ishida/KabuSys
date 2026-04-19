KabuSys
=======

日本株向けの自動売買 / 研究フレームワーク（モジュール群）。  
本リポジトリは取引実行エンジン、監視、ポートフォリオ構築、リサーチ（DuckDBベース）、AIによるニュース解析などの機能を提供します。

主な特徴
--------
- 実行エンジンと監視プロセスの分離（run_execution / run_monitoring）
- 本番（live）／ペーパー（paper_trading）／開発（development）の環境切替
- Paper Trading 用に実取引DBと完全分離された専用SQLiteを利用
- DuckDB を用いたファクター計算・研究モジュール（prices_daily / raw_financials を参照）
- ニュースを LLM（OpenAI）で評価して銘柄別スコアを作成（ai.news_nlp）
- 市場レジーム判定（ai.regime_detector）
- 監視（System / Trade / Risk）と Kill Switch による自動停止・アラート
- ロギング設定ユーティリティ（コンソール + 日次ローテートファイル）
- 設定ウィザード（.env 作成）と設定検証ツール

主な機能一覧
-------------
- 実行関連
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV によるモード切替。paper_trading 時は MockBrokerClient を利用し、data/paper_trading.db を使用）
- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
  - monitoring_engine: System/Trade/Risk モニターをまとめた運用ループ
  - monitoring_db: 監視用 SQLite テーブル定義と永続化 API
  - kill_switch: リスク基準到達時に data/kill.flag を書き込み ExecutionEngine 停止をトリガー
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定・重み計算
  - portfolio.position_sizing: 株数算出（lot 単位丸め、リスク/資金制約対応）
  - portfolio.risk_adjustment: セクター上限やレジーム乗数
- 研究（DuckDB）
  - research.factor_research: Momentum / Volatility / Value 等ファクター計算
  - research.feature_exploration: 将来リターン計算・IC（情報係数）・統計サマリー
- AI（OpenAI）
  - ai.news_nlp: ニュースを LLM でセンチメント化し ai_scores に書込
  - ai.regime_detector: MA200 とマクロニュースの LLM 評価を組み合わせて市場レジーム判定
- ユーティリティ
  - utils.logging_setup: 統一的なログ設定（stdout + 日次ローテート）
  - utils.process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプト
- 設定関連
  - config_setup.py: .env を対話的に作成・更新するウィザード
  - validate_config.py: 起動前に .env / config/*.yaml の不備を検出する CLI

セットアップ手順（概略）
---------------------
前提:
- 推奨 Python バージョン: 3.10+
- SQLite は標準ライブラリで利用
- 推奨インストールパッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の検証を行う場合）

例:
1. 仮想環境の作成と有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. .env の初期作成（対話ウィザード）
   - python -m kabusys.config_setup
   - 指示に従って J-Quants トークン、kabu API パスワード等を入力してください。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合は --strict を付けます。

環境変数（主なもの）
-------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DB / ログパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト: data/paper_trading.db）
  - LOG_DIR（デフォルト: logs/）
- ログレベル
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- Paper Trading 固有
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- OpenAI
  - OPENAI_API_KEY: ai.news_nlp / ai.regime_detector で使用
- 監視（MONITOR_POLL_INTERVAL）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- Kill / Stop フラグ
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - stop_requested.flag（手動停止用ファイル = data/stop_requested.flag）

使い方（主要なコマンド）
-----------------------
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 注意: 起動前に data/stop_requested.flag が存在すると起動しません。
  - 停止: data/stop_requested.flag を作成すると安全に終了します。kill_switch により data/kill.flag が書き込まれると ExecutionEngine は停止されます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH または PAPER_TRADING_SQLITE_PATH 環境変数

- AI スコア付与（プログラム的に呼ぶ）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、ai_scores / market_regime などのテーブルへ書き込みます。
  - OpenAI API キーは引数 または OPENAI_API_KEY 環境変数で与えてください。

停止・Kill の仕組み
-------------------
- 手動停止（run_* スクリプト共通）
  - data/stop_requested.flag が存在すると run_execution/run_monitoring のループを終了します。

- 自動 Kill Switch
  - RiskMonitor が条件（ドローダウン超過やポジション上限超過）を満たすと KillSwitch が data/kill.flag を作成します。ExecutionEngine はこのフラグの存在を検出して停止動作を行います。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ログ
---
- デフォルトのログ先: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション・30日保持）
- コンソールは stdout に出力されます。ログレベルは LOG_LEVEL または setup_logging の引数で制御できます。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - execution/                — 実行エンジン関連（BrokerFactory, Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマと永続化 API
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
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + MA200）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

注意事項 / 運用上のヒント
------------------------
- 本番環境（KABUSYS_ENV=live）では kill.flag 自動クリア設定は危険です。KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- Paper Trading（paper_trading）モードは本番DBと完全分離して動作します（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を利用する機能は API コストとレイテンシを考慮して運用してください。APIキーは安全に管理してください。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）は想定されるスキーマで事前に準備する必要があります（データ投入処理は別モジュール / スクリプト想定）。
- ローカルでの開発は KABUSYS_ENV=development を推奨。発注処理が無効化される等の挙動は実装に依存します。

ライセンス・貢献
----------------
- この README はリポジトリ内のコードから自動生成された説明を含みます。実際のライセンスはプロジェクトルートの LICENSE を参照してください。  
- バグ修正や機能追加の際はまず validate_config や単体テストを実行してから PR を投げてください。

最後に
------
動作確認やデータ投入、運用フローの整備（バックアップ、ログローテーション監視、API レート制御など）は個別環境に合わせて設定してください。必要であれば、各モジュールの詳細なドキュメント（関数引数・戻り値・例外など）を別途生成します。