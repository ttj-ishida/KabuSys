KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージ群です。本リポジトリは取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算 / 特徴量探索）、およびニュースに基づく AI スコアリング等の機能を含みます。設計方針としては以下を重視しています：

- 本番と Paper Trading の明確な分離（DB 等）
- ルックアヘッドバイアス回避（日時参照の扱いに注意）
- フェイルセーフ（API 失敗時のフォールバック）
- 単体関数ベースでテストしやすい実装

主な機能
--------
- Execution
  - ExecutionEngine を用いた注文管理、リコンシリエーション（再起動後の復旧処理）
  - OrderManager / OrderRepository による注文状態遷移管理
  - Broker クライアント抽象化（本番 / モック対応）
- Monitoring
  - SystemMonitor: CPU/MEM/DISK, プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - AlertManager: LINE Push による通知（クールダウン管理）
  - KillSwitch: フラグファイルによる ExecutionEngine 停止シグナル
  - Streamlit ダッシュボードによる可視化（read-only）
- Portfolio construction
  - 銘柄選定、等金額 / スコア加重配分、リスクベースのポジション決定
  - セクター上限適用、レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Spearman）や統計サマリ
- AI
  - ニュース NLP（OpenAI）を用いた銘柄別センチメントスコア化（ai_scores への書き込み）
  - 市場レジーム判定（ETF MA + マクロセンチメントの合成）
- ツール
  - paper_verification_report: Paper Trading DB を解析して検証レポートを出力

セットアップ
-----------
前提
- Python >= 3.10（型記法: X | Y を使用）
- SQLite（Python 標準ライブラリ）
- システムによっては psutil の一部機能に権限が必要

推奨手順（開発環境）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   例: pip install -r requirements.txt
   代表的な依存パッケージ:
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit
   （requirements.txt が無い場合は上記を個別に pip install してください）

3. 環境変数 / .env
   - プロジェクトルートに .env または .env.local を置くことで自動読み込みされます（OS 環境変数が優先）。
   - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - KABUSYS_ENV：development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE：instant | partial | never | reject（Paper Trading の約定挙動）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - SQLITE_PATH（監視用 DB、デフォルト data/monitoring.db）
     - DUCKDB_PATH（時系列等の分析 DB、デフォルト data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、デフォルト 60）

使い方
------
コマンドライン起動（主なエントリポイント）

- 実行エンジン（ExecutionEngine）
  - 本番 / Paper Trading のどちらも環境変数 KABUSYS_ENV により動作が切り替わります。
  - Paper Trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）に記録されます。
  - 起動:
    - python -m kabusys.run_execution

- 監視ループ（SystemMonitor を含む単独プロセス）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点に注意。
  - 起動:
    - python -m kabusys.run_monitoring
  - 監視は PID ファイル (デフォルト data/execution.pid) をチェックします。kill.flag (デフォルト data/kill.flag) は ExecutionEngine 停止のために書き込まれます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

- Streamlit ダッシュボード（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で DB を開きます（URI ?mode=ro）。

プログラム API（ライブラリ利用）
- パッケージとして import して各機能をプログラムから呼び出せます。主な公開関数 / クラス:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary
  - kabusys.portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes / apply_sector_cap / calc_regime_multiplier
  - kabusys.monitoring.MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / AlertManager / KillSwitch
  - kabusys.monitoring.MonitoringDB — SQLite 上の読み書きユーティリティ

重要な運用上の注意
- KABUSYS_ENV の値: development | paper_trading | live。値が不正な場合は例外が発生します。
- Monitoring は本番 sqlite_path を使用するため、Paper Trading と分離したい場合は設計上の注意が必要です（run_execution は is_paper を見て paper_sqlite_path を使います）。
- process priority 設定：run_* スクリプトは起動時に set_process_priority("high") を試みます（psutil を使用）。権限不足で失敗することがありますが警告でスキップされます。
- OpenAI API の呼び出しは外部 API に依存します。キーがない場合、AI 機能はエラーになるかフォールバック（多くは 0.0）します。OPENAI_API_KEY を設定してください。
- DB マイグレーション：monitoring_db.init_monitoring_db() は既存 DB にカラム追加の簡易マイグレーションを行います（peak_value, latency_ms など）。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / .env 読み込みと Settings
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- ai/
  - __init__.py
  - news_nlp.py                  — ニュース NLP スコアリング（OpenAI 連携）
  - regime_detector.py           — 市場レジーム判定（ETF MA + マクロセンチメント）
- monitoring/
  - __init__.py
  - monitoring_db.py             — SQLite 永続化層（schema/migrations）
  - monitoring_engine.py         — 各 Monitor を束ねる
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py
- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- execution/
  - (order_manager.py, reconciler.py, order_repository.py 等 — 注文・ブローカー周り)
- utils/
  - __init__.py
  - process_priority.py         — プロセス優先度 / CPU affinity 設定ユーティリティ
- data/ (参照される想定のデータディレクトリ)
  - kabusys.duckdb (デフォルト: data/kabusys.duckdb)
  - monitoring.db  (デフォルト: data/monitoring.db)
  - paper_trading.db (Paper Trading 用 DB: data/paper_trading.db)

設定例 (.env)
-------------
例: .env ファイル（プロジェクトルートに配置）
    KABUSYS_ENV=development
    JQUANTS_REFRESH_TOKEN=your_jquants_token
    KABU_API_PASSWORD=your_kabu_password
    OPENAI_API_KEY=sk-...
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
    LINE_CHANNEL_ACCESS_TOKEN=...
    LINE_USER_ID=...
    MONITOR_POLL_INTERVAL=60
    PAPER_FILL_MODE=instant

開発 / テストのヒント
- 環境変数の自動読み込みは .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から探して行われます。テスト時に自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI 呼び出し部分は外部 API に依存するため、ユニットテストでは _call_openai_api をパッチしてモックレスポンスを返すことでテスト可能です。
- DuckDB や SQLite の読み取り専用接続（Streamlit ダッシュボード等）では URI に ?mode=ro を付けて開くことで安全に参照できます。

ライセンス / 貢献
----------------
（ここにライセンス情報や貢献方法を追記してください）

補足
----
この README はソース内の docstring / 設計コメントを基に作成しています。実行時の詳細な設定や BrokerClient の実装、order_repository のスキーマ等は該当ソースを参照してください。質問や追加のドキュメント化が必要であれば具体的に教えてください。