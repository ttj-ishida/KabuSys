KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python ベースの小型フレームワークです。  
主な機能は以下の通りです。

- 自動売買の実行エンジン（ExecutionEngine、OrderManager、Reconciler 等）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- ポートフォリオ構築ロジック（候補選定、重み算出、ポジションサイジング、セクター制限 等）
- リサーチ用ファクター計算（Momentum / Volatility / Value 等）
- ニュースを用いた AI（OpenAI）によるセンチメントスコアリングと市場レジーム判定
- Paper Trading 検証ツール（レポート生成）
- Streamlit ベースの監視ダッシュボード

機能一覧
--------
- Execution
  - ブローカー抽象化（本番/モック対応）
  - OrderManager による注文作成・状態管理
  - Reconciler による起動時リコンシリエーション（注文・ポジション整合）
  - Risk Manager（発注前チェック：ポジション上限・資金利用率 等）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス監視、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定の価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクイベント記録
  - KillSwitch / AlertManager: 異常時に停止フラグ作成・LINE通知
  - Monitoring DB（SQLite）への永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - Streamlit ダッシュボード（read-only）
- Portfolio
  - 候補選定（スコア順）、等配分 / スコア加重配分
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- Research
  - DuckDB を使ったファクター計算（momentum/value/volatility）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュースセンチメント（OpenAI）→ ai_scores テーブルへ書込
  - 市場レジーム判定（ma200 + マクロセンチメント合成）
- Tools
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
1. リポジトリをクローン／配置
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - 代表的な依存：duckdb, psutil, requests, streamlit, openai
   - 例:
     - pip install duckdb psutil requests streamlit openai
   - （プロジェクトに requirements.txt がある場合はそれを使ってください）
4. データディレクトリ作成
   - mkdir -p data
5. 環境変数を設定（.env または .env.local をプロジェクトルートに配置可能）
   - 必須（実行する機能により異なる）
     - JQUANTS_REFRESH_TOKEN — J-Quants API を使う場合
     - KABU_API_PASSWORD — kabuステーション接続に必須
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - 推奨／設定例:
     - KABUSYS_ENV=development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject
     - LOG_LEVEL=INFO
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、監視プロセスで使用）
6. DB 初期化
   - monitoring 用の SQLite テーブルは起動時に自動で作成されます（init_monitoring_db）。
   - 必要に応じて DuckDB ファイルに prices_daily / raw_financials 等のテーブルを用意してください。

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading の場合は MockBroker を使用し、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に分離。
- OPENAI_API_KEY: OpenAI 呼び出しに使用
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant, partial, never, reject）
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: DB ファイルパス
- PID_FILE_PATH / KILL_FLAG_PATH: プロセス制御用ファイル

使い方（実行例）
----------------

- Execution Engine を起動する
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB を使い MockBrokerClient を利用します。
  - 停止の仕組み:
    - data/stop_requested.flag が存在すると起動を中止 / 実行中は停止します（run_execution.py 内のチェック）。
    - KillSwitch（監視側）が異常検出時に data/kill.flag を作成し、外部から停止要求を出せます。
- Monitoring を起動する（ポーリング監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒、デフォルト 60）。
  - 監視は常に本番用 sqlite_path を使用する設計です（環境にかかわらず）。
- Streamlit ダッシュボード（監視の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードはデータベースを read-only で開きます。監視プロセスがログを書き込んでいることが前提です。
- Paper Trading 検証レポートを作る
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db オプションで別パス指定可能。
- AI 周り（コードとして呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  — ニュースセンチメントを ai_scores に書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — market_regime に書き込む
  - これらは DuckDB 接続（duckdb.connect(...)）を引数に受け取ります。
- ライブラリ・ユーティリティの利用例（Python から）
  - ポートフォリオ構築
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - リサーチ機能
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

注意・運用上のポイント
--------------------
- Paper Trading と本番 DB は分離されています（PAPER_TRADING_SQLITE_PATH）。paper_trading 環境では MockBroker を使用し、本番 DB を弄りません。
- 自動で .env を読み込む仕組みが有効（プロジェクトルートに .env/.env.local）。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- データ鮮度チェックは DuckDB 上の prices_daily を参照し、最新日が許容範囲内か確認します（SystemMonitor）。
- プロセス優先度や CPU affinity は utils.process_priority の set_process_priority / set_cpu_affinity で制御します。権限により設定できない場合は警告が出ますが処理は継続されます。
- OpenAI 呼び出しはレート制限・ネットワーク障害等を考慮してリトライ処理を行い、失敗時はフェイルセーフ（スコア 0 や処理スキップ）にフォールバックします。

ディレクトリ構成（主要ファイル）
-------------------------------
（src/kabusys/ 以下を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / .env ロード / Settings クラス
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト
- src/kabusys/execution/
  - execution_engine.py               — 実行エンジン（EngineConfig / run_session 等）
  - order_manager.py                  — 注文作成 / 状態遷移管理
  - order_repository.py               — Orders DB アクセス
  - reconciler.py                     — 再起動時の自動復旧・突合せ
  - broker_factory.py                 — Broker クライアント生成（本番 / モック）
  - broker_api.py                     — ブローカー API 抽象
  - order_record.py                   — 注文レコード / 状態列挙
- src/kabusys/monitoring/
  - monitoring_db.py                  — SQLite 永続化層（テーブル初期化・CRUD）
  - system_monitor.py                 — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py                  — 注文滞留・約定異常検出
  - risk_monitor.py                   — ドローダウン / ポジション上限検出
  - kill_switch.py                    — kill.flag 管理（停止シグナル）
  - alert_manager.py                  — LINE push 通知
  - monitoring_engine.py              — 各監視を束ねるランナー
  - streamlit_dashboard.py            — Streamlit ダッシュボード
- src/kabusys/portfolio/
  - portfolio_builder.py              — 候補選定・重み計算
  - position_sizing.py                — 株数決定・丸め・cap
  - risk_adjustment.py                — セクター制限・レジーム乗数
- src/kabusys/research/
  - factor_research.py                — momentum / volatility / value
  - feature_exploration.py            — 将来リターン・IC・統計
- src/kabusys/ai/
  - news_nlp.py                       — ニュース→センチメント（OpenAI）
  - regime_detector.py                — ma200 + マクロセンチメントによるレジーム判定
- src/kabusys/tools/
  - paper_verification_report.py      — Paper Trading 検証レポート生成ツール
- src/kabusys/utils/
  - process_priority.py               — プロセス優先度 / CPU affinity ユーティリティ

よくある運用コマンドまとめ
------------------------
- Execution 起動
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Python からモジュール利用
  - from kabusys.portfolio import calc_position_sizes
  - from kabusys.ai import score_news

サポート・拡張ポイント
--------------------
- Broker 実装の追加（kabusys.execution.broker_factory）
- DuckDB のデータ投入スクリプト（prices_daily / raw_financials 等）
- 手数料・スリッページモデルを position_sizing に反映
- モニタリング条件・閾値のチューニング（Settings 経由で環境変数により変更可能）
- AlertManager の通知先（LINE 以外）追加

最後に
------
本 README はコードベースの主要機能・運用手順をまとめたものです。実運用前に必ずテストネット（paper_trading）で動作確認を行い、env / DB / ブローカー設定を正しく切り分けてください。必要であれば README をプロジェクトの要件に合わせて追記してください。