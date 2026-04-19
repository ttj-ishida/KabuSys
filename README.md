KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコードベースです。  
主な目的は以下です。

- 戦略開発（ファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、株数決定）
- 発注エンジン（本番 / ペーパートレード分離）
- 監視・アラート（システム状態、注文・リスク監視、Kill Switch）
- ニュース NLP を使った AI スコアリング / レジーム判定
- 付随ツール（ペーパートレード検証レポート生成など）

主要な設計方針:
- DB（分析用: DuckDB / 運用用: SQLite）を利用したオフライン計算・ログ保管
- 本番とペーパートレードの DB 分離
- 外部 API（OpenAI など）は明示的にキーを渡すか環境変数で管理
- 自動化されたログ設定・プロセス優先度制御・停止フラグによる安全停止

主な機能
-------
- strategy / research
  - ファクター計算（momentum, volatility, value 等）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
- portfolio
  - 候補選定、等配分・スコア配分、ポジションサイズ計算（単元丸め、集約上限）
  - セクターキャップ適用、レジームに応じた乗数
- execution
  - ExecutionEngine（本番 / paper_trading 切替）
  - BrokerClientFactory（本番とモックの切替）
  - OrderManager / RiskManager / Reconciler
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - MonitoringDB: SQLite に監視ログを永続化
  - KillSwitch: 条件により data/kill.flag を書き込んで ExecutionEngine を止める
  - run_monitoring: ポーリングループによる常時監視スクリプト
- ai
  - news_nlp: OpenAI でニュースをスコアリングし ai_scores に書き込み
  - regime_detector: ETF MA とマクロニュースで日次レジーム判定（market_regime テーブル）
- utils
  - ログ設定（stdout + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定
- tools
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL レポートを生成

前提・必要パッケージ
--------------------
必須（概略）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定ファイル検証を行う場合）
- sqlite3（標準ライブラリ）

インストール例（推奨は仮想環境を利用）:
    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil openai pyyaml

（requirements.txt がある場合はそれを利用してください。）

セットアップ手順
----------------

1. リポジトリをクローン
    git clone <repo>
    cd <repo>

2. 仮想環境作成・依存ライブラリをインストール
    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil openai pyyaml

3. 初期設定（.env）を対話式で作成
    python -m kabusys.config_setup

   - J-Quants や kabuAPI のシークレットはここで入力します。
   - .env は Git にコミットしないでください。

   例（.env の主要項目）:
       KABUSYS_ENV=development            # development | paper_trading | live
       JQUANTS_REFRESH_TOKEN=your_token
       KABU_API_PASSWORD=your_password
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       LOG_LEVEL=INFO
       KILL_FLAG_CLEAR_ON_START=0         # 本番では 0 を推奨

4. 設定検証（起動前チェック）
    python -m kabusys.validate_config
    # 警告もエラー扱いにする場合:
    python -m kabusys.validate_config --strict

5. ディレクトリ作成（ログ / DB 保存先）
   スクリプトは自動で作成する場面もありますが、手動で作ることを推奨します。
       mkdir -p data logs

使い方
------

環境変数（代表例）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
  - ExecutionEngine は paper_trading のとき専用のペーパートレード DB を使います（data/paper_trading.db）。
- OPENAI_API_KEY: OpenAI を使う場合に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

起動スクリプト
- 監視ループ（Monitoring）
    python -m kabusys.run_monitoring

    特記事項:
    - MONITOR_POLL_INTERVAL 環境変数で間隔を上書きできます（秒）。
    - run_monitoring は data/stop_requested.flag の検出で終了します。
    - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を参照します（環境に依らず）。

- 実行エンジン（ExecutionEngine）
    python -m kabusys.run_execution

    特記事項:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient が使用され、ペーパートレード DB（PAPER_TRADING_SQLITE_PATH / デフォルト data/paper_trading.db）に記録されます。
    - run_execution は data/stop_requested.flag の検出で Engine を停止・終了します。
    - ExecutionEngine は pid ファイル（data/execution.pid 等）を出力します。

- ペーパートレード検証レポート
    python -m kabusys.tools.paper_verification_report
    # 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    # DB 指定:
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

AI 機能（プログラムから呼び出す場合）
- ニュース NLP スコアリング:
    from kabusys.ai.news_nlp import score_news
    # DuckDB 接続の準備
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,12), api_key="...")

- レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,12), api_key="...")

注意:
- OpenAI の API キーは引数または環境変数 OPENAI_API_KEY で提供してください。
- AI 呼び出しはレート制限・ネットワーク失敗に対してリトライ/フォールバック実装がありますが、API コストに注意してください。

停止・Kill Switch
- 常駐スクリプトの外部停止:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のポーリングループが検出して安全に終了します。
- Kill Switch:
  - KillSwitch は基準に達したら data/kill.flag（Settings.kill_flag_path）を書き込み、ExecutionEngine 停止を促します。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ログ
----
- 共通ログ設定は kabusys.utils.logging_setup.setup_logging で行います。
- ログは stdout（コンソール）と日次ローテーションファイル（logs/<app_name>.log）に出力されます。
- LOG_DIR 環境変数でログディレクトリを変更可能。

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理、自動 .env ロード
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 起動前設定検証ツール
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

kabusys/ai/
- news_nlp.py              — ニュース NLP（OpenAI）による銘柄スコアリング
- regime_detector.py       — マクロ + MA によるレジーム判定

kabusys/monitoring/
- monitoring_db.py         — SQLite ベースの監視ログ永続化
- system_monitor.py        — システム状態・データ鮮度監視
- trade_monitor.py         — 注文関連監視（滞留注文・約定異常など）  ※実装あり
- risk_monitor.py          — ドローダウン・ポジション上限監視
- kill_switch.py           — Kill Switch 制御
- monitoring_engine.py     — 各 Monitor を束ねる

kabusys/execution/
- execution_engine.py      — ExecutionEngine（セッション管理）
- broker_factory.py        — Broker クライアントの生成（実ブローカ / Mock 切替）
- order_manager.py
- order_repository.py
- reconciler.py
- risk_manager.py

kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py

kabusys/research/
- factor_research.py
- feature_exploration.py

kabusys/tools/
- paper_verification_report.py

kabusys/utils/
- logging_setup.py
- process_priority.py

補足・運用上の注意
------------------
- 本番環境（KABUSYS_ENV=live）では .env のシークレットや通知先（LINE）等を十分に確認してください。validate_config で本番用の警告チェックが行われます。
- paper_trading 環境は本番 DB と完全分離するよう設計されています（PAPER_TRADING_SQLITE_PATH）。
- AI を使用する機能は OpenAI の料金・利用規約に従って運用してください。
- DB マイグレーション（monitoring_db.init_monitoring_db）は冪等で、既存カラムの追加処理も含まれていますが、運用時はバックアップを取ってください。

貢献・拡張
-----------
- 新しいファクターや戦略を research に追加し、portfolio モジュールと組み合わせてください。
- BrokerClientFactory を拡張すると新しいブローカに対応できます。
- monitoring のアラート連携（LINE など）は AlertManager を通じて実装できます（AlertManager の実装を追加してください）。

問い合わせ
--------
コード内の docstring や関数コメント（日本語）を参照してください。動作や API に関する質問は Issue を立ててください。

---  
README はコードベースの概要と運用の基本をまとめたものです。実際のデプロイ／運用前に必ず validate_config を実行し、.env の内容を確認してください。