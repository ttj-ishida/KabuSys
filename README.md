KabuSys — 日本株自動売買システム（README）
=================================

概要
----
KabuSys は日本株向けの自動売買／研究／監視ユーティリティのコレクションです。本コードベースは以下の主要機能を含みます。

- 注文発行・状態管理・リコンシリエーションを行う ExecutionEngine
- システム稼働状況・注文滞留・リスク監視を行う Monitoring コンポーネント群（監視ログは SQLite に永続化）
- ポートフォリオ構築（候補選定・配分・ポジションサイズ計算・セクターキャップ等）
- ファクター計算・特徴量探索（DuckDB を用いたオンチェーン分析）
- ニュースを LLM でスコアリングする AI モジュール（OpenAI を利用）
- 各種ユーティリティ（プロセス優先度、Streamlit ダッシュボード、検証レポート等）

主な特徴
--------
- モジュール化された設計（execution / monitoring / portfolio / research / ai / utils）
- DuckDB を利用したデータ解析（prices_daily / raw_financials 等）
- SQLite による監視ログ（system_status / trade_logs / risk_logs / positions / dashboard）
- Paper Trading モードの完全分離（paper_trading 環境では専用 SQLite を使用）
- OpenAI を使ったニュースセンチメント・レジーム判定機能（再試行・フォールバック実装あり）
- Streamlit による監視ダッシュボード、紙取引検証レポート生成ツール

セットアップ
-----------
1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

2. 依存パッケージのインストール（requirements.txt を用意している前提）
   - pip install -r requirements.txt

   主要依存例:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit

3. 環境変数 / .env
   プロジェクトルートの .env / .env.local を自動で読み込みます（OS 環境変数が優先）。
   自動ロードを無効化する場合:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   重要な環境変数:
   - KABUSYS_ENV: one of "development" | "paper_trading" | "live"（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
   - KABU_API_PASSWORD: kabuステーション API 用（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信用
   - SQLITE_PATH: 監視 DB のパス（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading の約定モード（"instant"|"partial"|"never"|"reject"、デフォルト: "instant"）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, MONITOR_POLL_INTERVAL, LOG_LEVEL 等

使い方（主要スクリプト / モジュール）
------------------------------

実行時の共通
- パッケージ化されているため python -m kabusys.<module> で起動可能です（src 配下を PYTHONPATH に含めてください）。

1) 監視ループの起動
- 目的: SystemMonitor（CPU/メモリ/ディスク/プロセス/データ鮮度）をポーリングして監視ログを保存
- 実行:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
- 注意:
  - Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番監視 DB）を使用します。

2) ExecutionEngine の起動
- 目的: ブローカークライアントを使った発注セッションを実行
- 実行:
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - paper_trading モードでは MockBrokerClient を使用しデータは PAPER_TRADING_SQLITE_PATH（data/paper_trading.db デフォルト）へ保存され、本番 DB と完全に分離されます。

3) Streamlit 監視ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only モードで SQLite を開き、ダッシュボード（Overview / Positions / Orders / System）を表示します。

4) Paper Trading 検証レポート生成
- コマンドラインツール:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）
- 出力: 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ 等を集計し PASS/FAIL 判定を表示します。

5) AI 系関数の利用（ライブラリ呼び出し）
- 例（ニューススコアリング）:
  from kabusys.ai.news_nlp import score_news
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026,4,10), api_key="sk-...")

- 例（レジーム判定）:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")

運用上の注意・設計ポリシー
-----------------------
- 環境設定は Settings クラス（kabusys.config）を通じて読み込まれます。.env のパースは堅牢に実装されています（export 形式、クォートやコメント対応）。
- Monitoring 側は常に本番の monitoring DB (SQLITE_PATH) を使います。ExecutionEngine は KABUSYS_ENV が paper_trading の場合に専用 DB を使うことで安全性を確保します。
- プロセス優先度設定: 起動時に set_process_priority("high") が呼ばれます（psutil による OS 差分吸収）。権限不足時は警告でスキップします。
- Kill Switch: kill.flag ファイルを書き込むことで ExecutionEngine 停止シグナルを送ります（KillSwitch クラス）。
- AI 呼び出しはリトライやフェイルセーフを備え、API キー未設定時は ValueError を送出します。また、LLM レスポンスのバリデーションを行い不正時はスキップします。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数 / .env の読み込みと Settings クラス
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading での分離に対応）

サブパッケージ（主な機能）
- monitoring/
  - monitoring_db.py  — SQLite スキーマ初期化・読み書きラッパー（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py  — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py   — 注文滞留・約定異常の検出
  - risk_monitor.py    — ドローダウン・ポジション上限チェック
  - kill_switch.py     — フラグファイルを使った停止シグナル処理
  - alert_manager.py   — LINE push 通知（クールダウン管理）
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード

- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory 等
  - 注文の状態遷移、ブローカー API 抽象化、再帰的なリコンシリエーションを実装

- portfolio/
  - portfolio_builder.py — 候補選定・スコアソート
  - position_sizing.py — 株数決定・スケーリング・単元丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - feature_exploration.py — 将来リターン、IC 計算、ファクター統計

- ai/
  - news_nlp.py        — ニュースを LLM でスコアリングして ai_scores に書込む
  - regime_detector.py — マクロセンチメント＋ETF MA 乖離で市場レジーム判定

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

- utils/
  - process_priority.py — psutil を使った優先度・CPU affinity 設定ユーティリティ

補足（よくある質問）
-------------------
Q: Paper Trading と本番の DB は分離されていますか？
A: はい。ExecutionEngine は KABUSYS_ENV=paper_trading の場合 PAPER_TRADING_SQLITE_PATH を使います（data/paper_trading.db がデフォルト）。ただし Monitoring は本番の monitoring.db を参照します（意図的設計）。

Q: .env の自動読み込みを無効にできますか？
A: はい。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: OpenAI を使う場合の注意は？
A: OPENAI_API_KEY が必要です。AI モジュールは 429 / タイムアウト / 5xx をエクスポネンシャルバックオフでリトライし、最終的には安全側へフォールバックします（失敗時は部分的にスキップ）。

Q: 監視 DB の初期化は自動ですか？
A: init_monitoring_db(conn) を呼ぶことで必要なテーブルとインデックスを冪等的に作成します（run_* スクリプトで呼ばれます）。

開発・貢献
---------
- ローカル開発では DuckDB にテスト用の prices_daily / raw_financials / raw_news 等を用意すると research / ai 機能をローカルで検証できます。
- テスト用に OPENAI 呼び出しのラッパー（_call_openai_api）をモックすることでネットワークに依存しない単体テストが可能です。

以上が主要な README 内容です。必要であればサンプル .env.example、Dockerfile、requirements.txt、もしくは具体的な起動スクリプト（systemd ユニット / Supervisor 例）や運用手順を追加で作成できます。どの情報を優先して追加しますか？