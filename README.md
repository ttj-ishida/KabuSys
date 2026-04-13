KabuSys — 日本株自動売買システム（README）
=======================================

概要
----
KabuSys は日本株向けの自動売買システム向けライブラリ／ツール群です。取引エンジン（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築・リサーチ・AI（ニュース NLP / レジーム判定）など、実運用を意識したコンポーネントが含まれます。  
本リポジトリは純粋関数的なポートフォリオ構築ロジック、DuckDB を使ったファクター計算、SQLite を使った監視ログ永続化、OpenAI を使ったニュースセンチメント評価などを提供します。

主な機能
--------
- Execution
  - ExecutionEngine 起動スクリプト（run_execution） — 本番 / paper_trading モード対応
  - ブローカーファクトリ（BrokerClientFactory）により実ブローカー／モック切替
  - OrderManager / Reconciler による注文管理・起動時リコンシリエーション
  - RiskManager による各種リスク制御（上限・サーキットブレーカー等）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite による監視ログ永続化（monitoring_db.init_monitoring_db）
  - Streamlit ベースの監視ダッシュボード起動スクリプト
  - KillSwitch（flag ファイル書き込みで ExecutionEngine を停止させる仕組み）
  - AlertManager（LINE Push による一方向通知とクールダウン管理）
- Portfolio
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア重み）
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイジング（calc_position_sizes）
- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - DuckDB 接続を受ける形で prices_daily / raw_financials を利用
- AI
  - ニュースセンチメント評価（kabusys.ai.score_news） — OpenAI（gpt-4o-mini）を利用
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime） — ETF MA とニュースを合成
- ユーティリティ
  - 環境設定管理（kabusys.config.Settings）: .env 自動ロード（プロジェクトルート検出）
  - プロセス優先度・CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）
  - Paper Trading 向けの検証レポート生成ツール（kabusys.tools.paper_verification_report）

セットアップ
----------
前提
- Python 3.10 以上（型アノテーション: X | Y を使用しているため）
- SQLite（組み込み）
- システムに依存するパッケージを利用（duckdb, psutil, requests, openai, streamlit など）

推奨手順（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - ※プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用

3. 環境変数設定
   - プロジェクトルートに .env を作成すると自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 重要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須の場面のみ）
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
     - PAPER_FILL_MODE: paper_trading 時の fill モード（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: Monitoring SQLite（デフォルト data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（監視・停止制御）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）
   - 例 .env（必要な値のみ）:
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     JQUANTS_REFRESH_TOKEN=...

注意:
- Settings は .env / .env.local をプロジェクトルート（.git や pyproject.toml によって検出）から自動読み込みします。
- 開発環境で .env の自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（主要スクリプト・API）
----------------------------

1) 監視ループ（SystemMonitor の単独起動）
- 実行:
  - python -m kabusys.run_monitoring
- オプション:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
- 特記事項:
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。
  - 起動時にプロセス優先度を "high" に設定します。

2) ExecutionEngine（取引実行）
- 実行:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録して本番 DB と分離します。
  - 起動時にプロセス優先度を "high" に設定します。
  - ExecutionEngine は Reconciler による起動時復旧や RiskManager、OrderManager 等を組み立ててセッションを実行します。

3) Paper Trading 検証レポート
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 指定 DB を使う: --db path/to/db.sqlite または環境変数 PAPER_TRADING_SQLITE_PATH を設定
- 出力:
  - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などのレポートと PASS/FAIL 判定

4) Streamlit 監視ダッシュボード
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 概要:
  - Positions / Orders / System / Overview タブで監視情報を表示。DB は読み取り専用で開くことを推奨。

5) AI（ニューススコア / レジーム判定） — Python API
- 例（ニューススコア）:
  from openai import OpenAI
  import duckdb
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  from kabusys.ai.news_nlp import score_news
  score_news(conn, date(2026,4,1), api_key="sk-...")
- 例（レジーム判定）:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026,4,1), api_key="sk-...")
- 注意:
  - API キーが未設定だと例外が出ます（引数で渡すか環境変数 OPENAI_API_KEY を設定）。

ライブラリ API（簡単な参照）
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes
  - apply_sector_cap, calc_regime_multiplier
- kabusys.research
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.ai
  - score_news
  - (regime_detector はモジュール内公開関数 score_regime を利用)
- kabusys.monitoring
  - MonitoringDB, init_monitoring_db, SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, AlertManager, KillSwitch

運用上の注意
-------------
- KillSwitch: kill.flag（デフォルト data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送ります。KillSwitch は RiskMonitor の判定に基づいてファイル作成を行います。
- PID ファイル: ExecutionEngine の PID を pid_file に書く設計になっており、SystemMonitor は PID ファイルを監視します。古い PID が存在してプロセスが死んでいる場合は stale PID と見なして削除します。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等にテーブルとインデックスを作成し、既存 DB に対して必要なカラムがない場合は ALTER TABLE による簡易マイグレーションを行います（peak_value、latency_ms など）。
- Paper Trading: KABUSYS_ENV=paper_trading を使うと paper 用 SQLite（data/paper_trading.db など）に完全に分離して記録されます。実運用時は本番 DB と分離することを強く推奨します。
- 環境変数ロード: Settings モジュールはプロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env / .env.local を読み込みます。OS 環境変数が優先されます。

ディレクトリ構成（重要ファイルのみ）
-----------------------------------
src/kabusys/
- __init__.py                 — パッケージ定義（バージョンなど）
- config.py                   — 環境変数/設定管理（Settings）
- run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
- run_execution.py            — ExecutionEngine 起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- portfolio/
  - portfolio_builder.py       — 候補選定・重み計算
  - position_sizing.py         — 発注株数計算・単元丸め・集約キャップ
  - risk_adjustment.py         — セクター上限・レジーム乗数
  - __init__.py
- research/
  - factor_research.py         — Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - feature_exploration.py     — 将来リターン・IC・統計サマリー
  - __init__.py
- ai/
  - news_nlp.py                — ニュースを LLM でスコアリングして ai_scores に書き込み
  - regime_detector.py         — マクロ + MA200 によるレジーム判定
  - __init__.py
- monitoring/
  - monitoring_db.py           — SQLite テーブル定義・MonitoringDB クラス
  - system_monitor.py          — CPU/Memory/Disk/データ鮮度/プロセス監視
  - trade_monitor.py           — 滞留注文・約定異常監視
  - risk_monitor.py            — ドローダウン・ポジション上限監視
  - alert_manager.py           — LINE 通知
  - kill_switch.py             — flag ファイル制御
  - monitoring_engine.py       — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py     — Streamlit 監視 UI
  - __init__.py
- execution/
  - order_manager.py
  - reconciler.py
  - (その他: broker_factory, order_repository, order_record, execution_engine 等 — 実装は一部あります)
- utils/
  - process_priority.py        — プロセス優先度・CPU affinity ユーティリティ
  - __init__.py
- (その他)
  - data/* / または prices_daily / raw_financials を使う DuckDB スキーマが前提

ライセンス・貢献
----------------
- 本 README はコードベースから記述しています。実運用する場合は環境変数・API キー・手数料・スリッページ等を十分に確認し、安全なテスト（paper_trading）での検証を行ってください。  
- 貢献や不具合報告はリポジトリの Issue / PR でお願いします。

付録: よく使うコマンド例
-----------------------
- 監視起動:
  python -m kabusys.run_monitoring
- Execution 起動:
  python -m kabusys.run_execution
- Paper レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

以上。必要なら README に追記すべき内容（サンプル .env、依存パッケージの固定バージョン、より詳しい起動例など）を教えてください。