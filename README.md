README
======

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームのコードベースです。  
主な目的はバックテストやリサーチ、Paper Trading、実行（ExecutionEngine）および運用監視を一貫して行うことです。  
（パッケージバージョン: 0.1.0）

主な特徴
--------
- ExecutionEngine（実行系）  
  - ブローカークライアント経由で発注を行う。Paper Trading（KABUSYS_ENV=paper_trading）モードはモックブローカーを使用し、data/paper_trading.db に記録して本番 DB と分離します。
  - リコンシリエーション（再起動後の注文同期）実装あり（Reconciler）。
  - OrderManager / OrderRepository による注文状態管理。

- Portfolio construction（銘柄選定・配分）  
  - 候補選定、等金額・スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算（lot 単位丸め、利用可能現金に応じたスケーリング）を純粋関数として提供。

- Research（ファクター計算・特徴量探索）  
  - Momentum / Volatility / Value 等ファクター計算（DuckDB の prices_daily / raw_financials テーブル参照）。
  - 将来リターン計算、IC（Spearman）や統計サマリー。

- AI モジュール（OpenAI を利用）  
  - news_nlp: ニュース記事を集約して LLM に投げ、銘柄ごとにセンチメント（ai_scores）を保存。
  - regime_detector: ETF 1321 の MA 乖離とマクロ記事の LLM センチメントを合成して日次レジーム判定を行い market_regime テーブルへ永続化。
  - API 呼び出しはリトライ・バックオフやバリデーションを実装（失敗時はフェイルセーフで処理継続）。

- Monitoring（運用監視）  
  - system_monitor, trade_monitor, risk_monitor によるポーリング監視とログ（SQLite）への永続化。
  - KillSwitch による flag ファイル書き込みで ExecutionEngine に停止シグナルを送る仕組み。
  - AlertManager による LINE プッシュ通知（設定されている場合）。
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）で監視情報を可視化。

- ユーティリティ  
  - 環境変数管理（.env / .env.local 自動ロード、Settings クラス）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）
  - Paper Trading の検証レポート生成ツール（kabusys.tools.paper_verification_report）

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 実際の requirements.txt がある場合はそれを使用:
     - pip install -r requirements.txt

4. ディレクトリ作成（必要に応じて）
   - data ディレクトリを作成して DB ファイル置き場を確保:
     - mkdir -p data

5. 環境変数設定（.env / .env.local 推奨）
   - プロジェクトルートに .env を置くと自動読み込みされます（OS 環境変数が優先。読み込みは .git または pyproject.toml の位置から探索）。
   - 重要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: （必須: J-Quants API 用）
     - KABU_API_PASSWORD: （必須: kabuステーション API 用）
     - OPENAI_API_KEY: （AI 機能を使う場合）
     - SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト: data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（任意）
     - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定モード、デフォルト: instant）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
   - 自動ロードを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

注意:
- Settings クラスは環境変数の検証を行います（例えば KABUSYS_ENV の有効値チェックや PAPER_FILL_MODE の検証）。
- Monitoring はコード中の仕様どおり「環境にかかわらず（paper_trading であっても）本番 sqlite_path を使う」実装になっている箇所があります（run_monitoring.py のコメント参照）。

使い方（主要なコマンド例）
------------------------
- 実行エンジン（ExecutionEngine）の起動
  - python -m kabusys.run_execution
  - Paper Trading モード:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で別 DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 系のバッチ処理（プログラムから呼び出す場合）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ※ api_key を None にすると環境変数 OPENAI_API_KEY を参照します。未設定の場合は例外になります。

運用メモ / 実装上の注意
---------------------
- run_execution.py と run_monitoring.py は起動時にプロセス優先度を "high" に設定しようとします（psutil が必要、権限によって失敗する場合は警告でスキップ）。
- run_execution.py は paper_trading のときに専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離します。
- run_monitoring.py は実装上、環境にかかわらず Settings.sqlite_path を使用するというコメントがあります。運用での注意点として確認してください。
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止指示を与えます。ExecutionEngine 側はこのフラグを監視している想定です。
- .env のパースは簡易ながら quoted strings や export プレフィックス、コメントをサポートしています。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py               — パッケージ定義（バージョン等）
- config.py                 — 環境変数/.env のロードと Settings クラス
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ / モジュール:
- execution/
  - order_manager.py
  - reconciler.py
  - ...（OrderRepository 等、実行系ロジック）
- monitoring/
  - monitoring_db.py         — SQLite ベースの監視ログ永続化レイヤ
  - system_monitor.py        — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py         — 注文滞留・約定異常検出
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - kill_switch.py           — flag ファイル経由で Execution 停止
  - alert_manager.py         — LINE への通知
  - monitoring_engine.py     — 各 monitor を束ねる（Polling）
  - streamlit_dashboard.py   — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py     — 候補選定・配分ロジック
  - position_sizing.py       — 発注株数計算・スケーリング
  - risk_adjustment.py       — セクター制限・レジーム乗数
- research/
  - factor_research.py       — ファクター計算（momentum/value/volatility）
  - feature_exploration.py   — 将来リターン / IC /統計
- ai/
  - news_nlp.py              — ニュース集約 → OpenAI で銘柄別スコア化
  - regime_detector.py       — マクロ + ma200 乖離でレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
- utils/
  - process_priority.py      — プロセス優先度・CPU affinity 設定ユーティリティ

データファイル（デフォルト）
- data/monitoring.db         — 監視ログ SQLite（デフォルト）
- data/paper_trading.db      — Paper Trading 用 SQLite（paper_trading 時）
- data/kabusys.duckdb        — DuckDB（prices_daily / raw_financials 等を格納）

追加ドキュメント
---------------
- コード内コメント・docstring に挙げられている設計方針や参照ドキュメント（例: PortfolioConstruction.md, StrategyModel.md）が存在する場合、それらも参照してください。

ライセンス / 貢献
-----------------
- この README ではライセンス情報は省略しています。リポジトリの LICENSE を確認してください。Issue / Pull Request による改善歓迎です。

お問い合わせ
------------
- 問題点や質問はリポジトリの Issue に投稿してください。