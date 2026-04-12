# KabuSys — README (日本語)

KabuSys は日本株向けの自動売買・リサーチ・監視ツール群をまとめたパッケージです。本リポジトリには戦略のポートフォリオ構築、ポジションサイジング、ファクター計算、AI を使ったニュースセンチメント評価、Execution / Monitoring の実行エントリポイント、および監視ダッシュボードや検証ツールが含まれています。

以下はコードベースから生成した README です。

---

目次
- プロジェクト概要
- 主な機能一覧
- 事前準備・セットアップ手順
- 実行方法（使い方）
- 監視/運用に関する注意点
- ディレクトリ構成（抜粋）
- SQLite / DuckDB テーブル（監視側）

---

プロジェクト概要
----------------
KabuSys は以下のようなコンポーネントを備えた日本株自動売買システムの基盤です。

- Execution（発注・注文管理、リコンシリエーション、リスク管理）
- Monitoring（システム状態・注文監視・リスク監視・KillSwitch）
- Portfolio（銘柄選定・配分・ポジションサイジング）
- Research（ファクター計算・特徴量解析）
- AI（ニュースセンチメント・市場レジーム判定）
- ユーティリティ（プロセス優先度設定、.env 読み込み等）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針の概要:
- 多くのアルゴリズムは純粋関数（副作用なし）で記述され、テストしやすい。
- 本番データベースと Paper Trading は明確に分離される設計。
- LLM 利用部分（OpenAI）には再試行・検証・クリッピング等のフェイルセーフが組み込まれている。
- Monitoring は軽量な SQLite に永続化し、監視データを収集／可視化する。

---

機能一覧
--------
- Execution
  - OrderManager / OrderRepository による注文生成・送信・同期
  - Reconciler による起動時の自動復旧（OrderSent 照合、ポジション差分照合）
  - RiskManager（制限・レート制限・サーキットブレーカー等、設定あり）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス PID チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文 / 約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション数上限監視、ダッシュボード更新
  - KillSwitch: 条件により ExecutionEngine 停止指示をフラグファイルで出力
  - AlertManager: LINE Push による一方向アラート送信（クールダウンあり）
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio
  - 銘柄候補選定、等配分・スコア配分、リスク調整（セクター制約、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、利用可能現金に対するスケーリング）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 経由で prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）などの統計解析ユーティリティ
- AI
  - news_nlp.score_news: raw_news を LLM（OpenAI）で評価して ai_scores に格納
  - regime_detector.score_regime: ETF の MA 乖離 + マクロニュースで市場レジーム判定
- 運用ツール
  - run_execution.py: ExecutionEngine 起動スクリプト（本番 / paper_trading 分離）
  - run_monitoring.py: SystemMonitor 単体のポーリングスクリプト
  - tools.paper_verification_report: Paper Trading 検証レポート生成ツール
  - monitoring/streamlit_dashboard.py: streamlit で監視ダッシュボードを起動

---

セットアップ手順
--------------
前提:
- Python 3.10+ を想定（型注釈や構文を利用）
- ローカルでの開発は PYTHONPATH=src を使うか pip install -e . でインストール

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要なパッケージ（一例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボードを使う場合)
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （リポジトリに requirements.txt がある場合は pip install -r requirements.txt）

3. 環境変数 / .env
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（既存 OS 環境変数は保護されます）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   推奨される主要環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...          (AI 機能を使う場合)
   - KABUSYS_ENV=development | paper_trading | live
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PAPER_FILL_MODE=instant|partial|never|reject
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - MONITOR_POLL_INTERVAL (※ run_monitoring 用。秒)
   - LOG_LEVEL (DEBUG|INFO|...）

4. データディレクトリ
   - デフォルトで data/ 以下を利用します。必要に応じてディレクトリを作成してください。
   - 例: mkdir -p data

注意: 実際のブローカー接続や口座情報は環境変数で管理し、秘密情報は .env を用いて管理してください。

---

使い方（主要コマンド）
--------------------

パッケージを開発モードで利用する場合:
- PYTHONPATH を src に通す例:
  - PYTHONPATH=src python -m kabusys.run_execution
  - PYTHONPATH=src python -m kabusys.run_monitoring

あるいはパッケージとしてインストール後:
- python -m kabusys.run_execution
- python -m kabusys.run_monitoring

1) Execution（発注エンジン）起動
- デフォルト: 本番 DB を使用
- Paper Trading 環境にするには:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - このとき paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離されます。

2) Monitoring（SystemMonitor の単体起動）
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可（デフォルト 60 秒）
- python -m kabusys.run_monitoring
- 監視は監視用の SQLite（Settings.sqlite_path）に永続化されます（init_monitoring_db によりテーブルを作成）。

3) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- オプション:
  - --from YYYY-MM-DD
  - --to YYYY-MM-DD
  - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）
- 期間を指定して稼働率・注文成功率・レイテンシ等のサマリを出力します。

4) Streamlit 監視ダッシュボード
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- readonly モードで SQLite を開き、Overview / Positions / Orders / System タブを表示します。

5) AI 関連（ニュースセンチメント・レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続と対象日を渡すと ai_scores テーブルへ書き込みます。
  - api_key を渡すか OPENAI_API_KEY を環境変数で設定してください。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジーム判定を行い market_regime テーブルへ冪等書き込みします。

実行上の注意
- Monitoring は常に本番 monitoring DB（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しない）。
- Execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path に切り替わります（本番と分離）。
- run_execution / run_monitoring の前に PID ファイル設定（PID_FILE_PATH）や kill.flag の取り扱いを確認してください。
- MONITOR_POLL_INTERVAL に不正（0 や負数、非数）を指定するとデフォルト（60 秒）にフォールバックします。

---

監視 DB（SQLite）テーブル概要
----------------------------
monitoring_db.init_monitoring_db により以下テーブルとインデックスが作成されます（冪等）。

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs
  - logged_at, event_type (Created/Sent/Filled 等), client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard
  - id (=1), updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

MonitoringDB クラスはこれらの読み書きを行うユーティリティを提供します（log_system_status, log_trade_event, upsert_position, log_risk_event, upsert_dashboard, get_dashboard など）。

---

ディレクトリ構成（抜粋）
----------------------
以下は主要ファイル・モジュールの抜粋です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env 読込 / Settings
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py         — プロセス優先度 / CPU affinity
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                 — ニュースセンチメント（OpenAI）
    - regime_detector.py          — 市場レジーム判定（OpenAI + MA200）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository など)
  - tools/
    - paper_verification_report.py

（上記は抜粋です。実際のリポジトリ内にさらに詳細なモジュールが含まれます。）

---

よくある運用上のポイント / トラブルシューティング
------------------------------------------------
- .env の読み込み:
  - .env, .env.local をプロジェクトルートから自動読み込みします（OS 環境変数優先）。
  - 自動読み込みを無効にしたいときは KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

- Paper Trading と本番 DB:
  - Paper Trading は Settings.is_paper 判定により paper_sqlite_path を使用します。データの混同に注意。

- OpenAI API:
  - API 呼び出しは再試行ロジックと応答検証（JSON 抽出・検証・数値クリップ）を備えていますが、API キー未設定時は機能しません。テスト環境では _call_openai_api をモックしてください。

- プロセス優先度 / CPU affinity:
  - set_process_priority() は OS によって実行結果が異なります。権限不足で設定できない場合は警告が出ますが動作は継続します。

- KillSwitch:
  - KillSwitch は監視側で条件を満たすと kill.flag を書き込みます。ExecutionEngine は起動時に kill.flag を参照・クリアする動作を想定しています（Settings.kill_flag_clear_on_start により制御）。

---

貢献・テスト
--------------
- 各モジュールは純粋関数・副作用分離が意識されているためユニットテストを書きやすい構成です。
- AI 呼び出し部分は外部通信を行うためユニットテストではモック化してください（例: unittest.mock.patch で _call_openai_api を置き換え）。

---

ライセンス / バージョン
-----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（含まれていない場合は適切に追加してください）。

---

最後に
-----
この README はコードベースの現状を元に自動生成的にまとめています。実運用する際は環境（ブローカー接続情報、API キー、DB パスなど）を適切に設定し、まずは Paper Trading モードで十分に検証してから本番環境へ移行してください。質問や追記希望があれば教えてください。