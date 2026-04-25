KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム向けライブラリ群です。  
主な機能は次の通りです。

- 実行エンジン（ExecutionEngine）による発注フローの実行（本番 / ペーパートレード対応）
- 監視サブシステム（Monitoring）によるプロセス・データ鮮度・リスク監視と Kill Switch
- ポートフォリオ構築（シグナル選別・重み付け・単元丸め）
- 研究モジュール（ファクター計算、特徴量探索、IC 計算等）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- 各種ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度など）
- Paper Trading 検証レポート生成ツール

注: 本リポジトリはライブラリ／ランチャースクリプト群を含み、実運用には外部 API キーや DB、kabuステーション 等のセットアップが必要です。

主な機能一覧
-------------
- Execution
  - 実エンジン起動スクリプト: run_execution.py
  - paper_trading 環境では MockBrokerClient を使用し、paper DB（data/paper_trading.db）に完全分離して記録
  - リスクマネージャ、OrderManager、Reconciler 等を統合してセッション実行
- Monitoring
  - run_monitoring.py による定期ポーリング監視（デフォルト 60 秒）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine
  - kill.flag による ExecutionEngine 停止シグナル発行（KillSwitch）
  - SQLite ベースの監視 DB 操作層（monitoring_db.py）
- Portfolio
  - 候補選定（select_candidates）
  - 重み算出（等金額 / スコア加重）
  - セクター上限適用、レジーム乗数、ポジションサイズ計算（単元丸め・aggregate cap）
- Research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - DuckDB を用いたオンメモリ SQL 処理
- AI
  - news_nlp: ニュース記事を OpenAI (gpt-4o-mini) でセンチメント化し ai_scores に書き込み
  - regime_detector: ETF MA とマクロニュースセンチメントを混成して日次レジーム判定
- Tools
  - 設定ウィザード: python -m kabusys.config_setup（.env の対話式生成）
  - 設定検証: python -m kabusys.validate_config（起動前チェック）
  - Paper Trading レポート: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------
前提
- Python 3.9+（プロジェクトで明示していない場合も多いですが、型注釈に合わせて 3.9 以上を想定）
- system パッケージ: duckdb, psutil, openai（AI 機能を使う場合）、PyYAML（config YAML 検証を使う場合）

1. リポジトリをクローンし、仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai
   - YAML 検証が必要なら: pip install PyYAML

3. 環境変数（.env）を準備
   - 対話式ウィザードを実行して .env を生成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要なオプション:
     - KABUSYS_ENV: development / paper_trading / live
     - DUCKDB_PATH, SQLITE_PATH
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE（paper_trading 時の約定挙動）
     - PAPER_TRADING_SQLITE_PATH（paper_trading DB を指定したい場合）
   - 生成済 .env を編集して必要な値を設定してください。
   - 注意: .env をリポジトリにコミットしないでください（機密情報含む）

4. 設定検証
   - python -m kabusys.validate_config
   - 本番前は --strict を付けて警告も FAIL として扱う:
     - python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトでは data/ 以下に DB やフラグファイルが置かれます。必要に応じて .env の PATH を変更してください。
   - run_execution/run_monitoring は data ディレクトリへ pid/flag を書きます。

基本的な使い方
--------------
- 実行エンジン起動（本番または paper_trading に応じて動作）
  - 環境変数で KABUSYS_ENV を設定（例: export KABUSYS_ENV=paper_trading）
  - python -m kabusys.run_execution
  - 特記事項:
    - paper_trading 環境では MockBrokerClient を使用し、data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）に記録
    - 起動時に data/stop_requested.flag があれば起動を中止
    - 実行中は data/execution.pid に PID が書かれる

- 監視サブシステム起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用して監視ログを記録する（環境に依存せず本番 DB パスが使われる点に注意）

- Kill Switch（停止信号）
  - KillSwitch は data/kill.flag を作成すると ExecutionEngine に停止を要求します。
  - KillSwitch の評価条件（ドローダウン、ポジション数など）に合致した場合にフラグが書かれます。
  - ExecutionEngine は起動中に stop_requested.flag を検知すると Graceful に停止します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db で別パス指定可。

- AI（ニューススコア / レジーム判定）
  - OpenAI API を利用するために OPENAI_API_KEY を環境変数に設定してください。
  - 使用例（スクリプトや REPL から）:
    - from openai import OpenAI などの準備を行い、DuckDB コネクションを渡して呼び出す:
      - from kabusys.ai.news_nlp import score_news
      - score_news(duckdb_conn, target_date, api_key="...")  # または環境変数で key を指定
    - レジーム:
      - from kabusys.ai.regime_detector import score_regime
      - score_regime(duckdb_conn, target_date, api_key="...")

ライブラリ API（主な公開関数）
----------------------------
- kabusys.config.Settings / settings: 環境変数からアプリ設定を取得
- kabusys.portfolio:
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes
  - apply_sector_cap, calc_regime_multiplier
- kabusys.research:
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.ai:
  - score_news(duckdb_conn, target_date, api_key=None)
  - score_regime(duckdb_conn, target_date, api_key=None)
- kabusys.monitoring:
  - MonitoringDB（低レベル DB API）
  - SystemMonitor / RiskMonitor / MonitoringEngine / KillSwitch
- CLI エントリ:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
  - python -m kabusys.tools.paper_verification_report

動作上の注意点 / 運用上のヒント
------------------------------
- データ鮮度とルックアヘッドバイアス:
  - AI モジュールやレジーム判定はルックアヘッドを避ける設計（target_date 未満データのみ使用）を重視しています。外部で日付を扱う際は同様の慣習に従ってください。
- ログ:
  - 共通の logging 設定ユーティリティ（kabusys.utils.logging_setup.setup_logging）を使用しています。ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びますが、権限不足や OS によっては無視される場合があります。
- Paper Trading:
  - KABUSYS_ENV=paper_trading にすると本番 DB と分離され、専用の paper DB に記録されます。PAPER_FILL_MODE で約定挙動を制御できます（instant / partial / never / reject）。
- Kill Switch / stop flag:
  - kill.flag（強制停止要求）と stop_requested.flag（シャットダウン指示）はそれぞれ違う用途で用いられます。運用時はこれらフラグの取り扱いを十分にドキュメント化してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対して安全にマイグレーション（列追加）を試みます。

ディレクトリ構成（主要ファイル）
-------------------------------
以下はソースツリー（src/kabusys）内の主なファイルとディレクトリです。実際のツリーが若干異なる場合がありますが、主要なモジュールは次の場所にあります。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / Settings
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 起動前検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py        # （トレード監視ロジック）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        # （アラート送信ロジック）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - data/
    - pipeline.py             # データ取得 / prices_last_date 等（prices_daily 供給）
    - stats.py                # zscore_normalize 等
  - tools/                   # 追加 CLI ツール群

ライセンス / 貢献
----------------
- この README に含まれる情報は、ソースコードから抽出した実装意図と使用方法の要約です。  
- 実運用・本番環境への導入前に必ずテストと設定検証を行ってください（python -m kabusys.validate_config）。  
- 機密情報（API キー等）は .env に含めますが、絶対に Git にコミットしないでください。

問い合わせ / 参考
-----------------
- 主要な起動フロー: run_execution.py / run_monitoring.py を参照してください。  
- AI 機能を使う場合は OpenAI の利用規約とレート制限に注意してください。  
- config_setup.py と validate_config.py を利用して設定の初期化と検証を行ってください。

--- 
必要ならば README に「インストール用 requirements.txt の例」「具体的な systemd Unit / cron サンプル」「より詳しい API 使用例」を追加で作成します。どれを追加しますか？