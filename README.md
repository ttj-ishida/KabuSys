KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株自動売買システム「KabuSys」のコアライブラリ群です。
トレード実行・監視・ポートフォリオ構築・リサーチ・ニュースNLP 等の機能を
モジュール化して提供します。本 README はリポジトリ内の主要コンポーネントと
セットアップ／基本的な使い方を説明します。

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件
- セットアップ手順
- 環境変数（主なもの）
- 実行例（使い方）
- ディレクトリ構成（抜粋）
- 補足（運用上の注意）

プロジェクト概要
----------------
KabuSys は以下の責務を持つモジュール群で構成された自動売買基盤です。

- Execution（ExecutionEngine）: ブローカーへの発注、オーダー管理、リスク制御、復旧（reconciler）
- Monitoring: システム健全性、注文異常、リスク監視、LINE 通知、kill flag による停止制御
- Portfolio: 候補選定、配分重量計算、ポジションサイズ計算、セクター制限・レジーム調整
- Research: DuckDB 上の価格・財務データからファクター計算・将来リターン・IC など
- AI: ニュースのセンチメント（OpenAI）によるスコアリング、レジーム判定
- Tools: 検証レポート生成（Paper Trading 向け）や Streamlit ダッシュボード

主な機能一覧
-------------
- 実行エンジン起動スクリプト（run_execution）
  - 本番 / Paper Trading 切替（KABUSYS_ENV）
  - Broker クライアント生成（本番は実ブローカー、paper_trading は Mock を使用）
  - リスク管理（max position %, utilization, circuit breaker 等）
  - リコンシリエーション（起動時の自動復旧）
- 監視ループ起動（run_monitoring）
  - システム状態（CPU/Memory/Disk/プロセス PID）を定期記録
  - 注文滞留・約定異常の検出
  - ドローダウン・ポジション上限の監視 → KillSwitch により停止指示可能
  - LINE 通知（AlertManager）
  - Streamlit ダッシュボード（監視 DB を表示）
- ポートフォリオ構築ユーティリティ
  - 候補選定（score / rank / top-N）
  - 等金額・スコア重み配分
  - risk-based（許容リスクから株数算出）および aggregate cap のスケール調整
  - セクター上限やレジームに応じた乗数適用
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB SQL を利用）
  - 将来リターン、IC、統計サマリー
- AI（OpenAI）
  - ニュース記事を LLM でセンチメント評価し ai_scores に書込
  - ETF ベースの MA 乖離 + マクロニュースセンチメントで市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB を解析して PASS/FAIL レポートを出力
  - streamlit_dashboard: 監視 DB を可視化するダッシュボード

必要条件
--------
- Python 3.10 以上（型アノテーションの構文等のため）
- 必要なライブラリ（主なもの）
  - duckdb
  - psutil
  - requests
  - openai（OpenAI SDK）
  - streamlit（ダッシュボード起動時）
- SQLite（ファイル DB を利用。Python 標準 sqlite3 を使用）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は上の必要ライブラリを個別にインストール）
     例: pip install duckdb psutil requests openai streamlit

4. 環境変数 / .env の準備
   - プロジェクトルートに .env（または .env.local）を置くと自動読み込みされます。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 初期データディレクトリ作成
   - data/ フォルダを作成。デフォルト DB パス:
     - data/monitoring.db（監視用 SQLite）
     - data/paper_trading.db（paper trading 用）
     - data/kabusys.duckdb（DuckDB）
   - 必要に応じて DuckDB に prices_daily/raw_financials/raw_news 等のテーブルを用意してください。

主要な環境変数（抜粋）
--------------------
- KABUSYS_ENV
  - 値: development / paper_trading / live
  - 動作モード（paper_trading のとき発注はモックブローカーで行われ DB は分離されます）
- JQUANTS_REFRESH_TOKEN
  - J-Quants API 用トークン（必須）
- KABU_API_PASSWORD
  - kabuステーション API のパスワード（必須）
- OPENAI_API_KEY
  - OpenAI API キー（AI モジュール使用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
  - AlertManager（LINE 通知）に必要（未設定でも動作は継続、通知はスキップされます）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の約定動作: instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒、デフォルト 60）。0/負値は無効扱いでデフォルトにフォールバック。

使い方（実行例）
----------------

- 監視ループの起動（監視 DB に定期記録）
  - python -m kabusys.run_monitoring
  - 環境変数で間隔上書き: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン（ExecutionEngine）の起動
  - 本番（デフォルト: KABUSYS_ENV=development）
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（Mock ブローカー、別 DB に書き込む）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - Execution 起動時、プロセス優先度を high に設定し、SQLite/DuckDB へ接続して処理を開始します。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI（ニューススコアリング / レジーム判定）
  - プログラムから呼び出す:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")
  - OpenAI API キーが環境変数にある場合 api_key 引数は省略可能。

注意点・運用上のポイント
------------------------
- Paper Trading モードは実ブローカーとは完全に分離された SQLite（PAPER_TRADING_SQLITE_PATH）を使います。
- .env 読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に行われます。
- Settings クラスは環境変数の検証を行うため、主要な必須変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）が未設定だと起動時に ValueError を投げます。
- run_monitoring は MONITOR_POLL_INTERVAL で指定した秒数だけ time.sleep します（最小 1 秒）。不正値は 60 秒にフォールバックします。
- OpenAI 呼び出しはリトライやエラー処理を含んでいますが、API キー未設定時は例外となります（AI 機能を使用する際は OPENAI_API_KEY をセットしてください）。
- kill.flag: RiskMonitor 等で危険検知時に data/kill.flag が書かれると ExecutionEngine 側で検出して安全停止する設計です。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START を使ってクリアする設定があります。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                        — 環境変数 / Settings
- run_monitoring.py                — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py                 — ExecutionEngine 起動スクリプト

modules:
- ai/
  - news_nlp.py                     — ニュースセンチメント取得（OpenAI）
  - regime_detector.py              — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py                — SQLite スキーマ + MonitoringDB ラッパー
  - system_monitor.py               — CPU/Mem/Disk/データ鮮度/プロセス監視
  - trade_monitor.py                — 注文滞留・約定異常検出
  - risk_monitor.py                 — ドローダウン・ポジション上限監視
  - kill_switch.py                  — kill.flag 書き込み管理
  - alert_manager.py                — LINE 通知
  - monitoring_engine.py            — Monitor を束ねるエンジン
  - streamlit_dashboard.py          — Streamlit ダッシュボード
- execution/
  - reconciler.py                   — 起動時リコンシリエーション
  - order_manager.py                — 発注フロー管理
  - (その他: broker_factory, order_repository など)
- portfolio/
  - portfolio_builder.py            — 候補選定・重み計算
  - risk_adjustment.py              — セクター制限・レジーム乗数
  - position_sizing.py              — 株数算出・aggregate cap
- research/
  - factor_research.py              — Momentum/Volatility/Value の計算（DuckDB）
  - feature_exploration.py          — 将来リターン、IC、統計サマリー
- tools/
  - paper_verification_report.py    — Paper Trading 検証レポート生成スクリプト
- utils/
  - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ

補足
----
- 各モジュールはドメインロジックと DB/外部 API 呼び出しを比較的明確に分離しています（純粋関数 vs 接続を受け取る関数など）。
- 本 README はリポジトリ内のソースからの抜粋を元に作成しています。実際の運用前に各設定や Broker 実装・テーブル構成（DuckDB 内の prices_daily/raw_financials/raw_news 等）を整備してください。

問題や追加したい説明があれば教えてください。README の例 .env や systemd ユニット例、運用手順（バックアップ・監視）なども追記できます。