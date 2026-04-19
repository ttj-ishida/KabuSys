KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（実運用 / ペーパートレード）、監視（Monitoring）、LLM を用いたニュース解析／レジーム判定などのモジュールを含みます。  
設計方針としては「モジュール分離」「フェイルセーフ」「ルックアヘッドバイアス回避」を重視しています。

主な機能
--------
- Execution
  - ExecutionEngine による発注処理（実運用 / ペーパートレード切替）
  - BrokerClientFactory によるブローカークライアント生成（paper_trading 用に MockBrokerClient）
  - OrderManager / OrderRepository / Reconciler / RiskManager による注文管理とリスク制御
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス状態の監視
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限の監視
  - KillSwitch: リスクトリガーでの停止フラグ (data/kill.flag) 書き込み
  - MonitoringEngine: 各 Monitor を束ねてポーリング実行
  - monitoring_db: SQLite によるログ永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- Portfolio（ポートフォリオ構築）
  - 銘柄選定（score / rank ベース）、等金額・スコア加重、リスク調整（セクター上限、レジーム乗数）、ポジションサイジング（lot 単位）
- Research（研究用）
  - ファクター計算（モメンタム／ボラティリティ／バリュー）、フォワードリターン、IC 計算、統計サマリ
  - DuckDB 経由で prices_daily / raw_financials 等を参照して純粋関数で計算
- AI（OpenAI 連携）
  - news_nlp: ニュースを LLM でセンチメント解析して ai_scores に書き込み（batch、リトライ、検証あり）
  - regime_detector: MA200 乖離 + マクロニュースセンチメントを合成して日次レジーム判定（market_regime へ書込）
- ツール
  - config_setup: .env の対話式生成ウィザード
  - validate_config: .env / config/*.yaml の起動前検証
  - tools.paper_verification_report: ペーパートレード結果の検証レポート生成

セットアップ
-----------
1. Python 環境（推奨: 3.10+）を用意。仮想環境を作成する例:
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール（プロジェクトに requirements.txt がない場合は下記を参照）:
   - pip install duckdb psutil openai pyyaml

   ※ 実行時に必要なモジュール:
   - duckdb — 分析用 DB
   - psutil — プロセス/リソース計測
   - openai — LLM 呼び出し（AI 機能を使う場合）
   - PyYAML — validate_config の YAML 検証（任意）

3. ディレクトリ準備:
   - data/ および logs/ は通常スクリプトが自動作成しますが、事前に作る場合:
     - mkdir -p data logs

4. 環境変数の設定 (.env)
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - その他主要な環境変数（デフォルト値を持つものもあります）:
     - KABUSYS_ENV: development | paper_trading | live (default: development)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB; default: data/paper_trading.db)
     - OPENAI_API_KEY (AI 機能利用時)
     - LOG_LEVEL (default: INFO)
     - KILL_FLAG_CLEAR_ON_START (0/1)
     - PAPER_FILL_MODE (paper_trading の約定シミュレーション: instant|partial|never|reject)

5. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方（主要な起動コマンド）
----------------------------
- ExecutionEngine を起動（通常は service / systemd 等で管理）:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
    - 起動時に data/stop_requested.flag が存在すると起動を拒否します。
    - 実行中に data/stop_requested.flag を作成するとエンジンが停止します。
    - 実行時に PID は data/execution.pid（デフォルト）に書き出されます。

- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で変更できます（デフォルト: 60）。
  - 監視は本番の sqlite_path を使用（KABUSYS_ENV に依存しない）。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で上書き可能。環境変数 PAPER_TRADING_SQLITE_PATH も参照します。

- AI 機能（プログラムから呼ぶ例）
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
  - どちらも OpenAI API キー（引数または OPENAI_API_KEY 環境変数）を必要とします。

- ログ
  - ログ出力は logs/<app_name>.log に日次ローテーションで出力されます（utils.logging_setup.setup_logging を全スクリプトが使用）。
  - 標準出力にもログが出ます（stdout）。

運用上の注意
------------
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも警告あり）。
- KABUSYS_ENV=live の場合は LINE 通知等、アラート設定を必ず確認してください（validate_config が警告します）。
- Kill Switch（data/kill.flag）はリスクトリガーで実行エンジンを停止するため、KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動でクリアされますが、本番では 0 を推奨します。
- monitoring と execution はそれぞれ別 DB を使う（paper_trading モードでは execution は paper DB を使用）ため、監視ログとペーパートレードログを分離できます。

主要ディレクトリ構成
-------------------
（プロジェクトルートの src/kabusys を基準に抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — レジーム判定
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装により存在)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

（補足）
- DuckDB を分析用に使用。prices_daily / raw_financials / raw_news 等のテーブルを想定。
- monitoring_db.init_monitoring_db() はテーブル作成／マイグレーションを行います（スクリプト起動時に自動実行）。

FAQ / トラブルシューティング
-----------------------------
- 「.env を用意しても validate_config でエラーが出る」
  - 必須環境変数 (JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD) が未設定の可能性があります。.env.example を参照して設定してください。
- OpenAI を使うときに認証エラーが出る
  - OPENAI_API_KEY を .env に設定するか、score_news / score_regime の呼び出し時に api_key を渡してください。
- ログファイルが出力されない
  - logs/ ディレクトリの作成権限や LOG_DIR 環境変数の設定を確認してください。ディレクトリ作成失敗時はコンソール出力のみになります。

ライセンス / バージョン
------------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（執筆時点）。
- ライセンス情報はプロジェクトルートの LICENSE を参照してください（存在する場合）。

問い合わせ
----------
実装や API 仕様についての質問は、プロジェクトの README / ドキュメントまたは開発チームにお問い合わせください。

以上。必要であれば README に含める動作例（systemd ユニット例や docker-compose.yml、requirements.txt の推奨内容など）を追記します。どの情報を追加しますか？