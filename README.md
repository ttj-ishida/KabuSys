README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群です。  
主な機能は注文発行（ExecutionEngine）・監視（MonitoringEngine）・ポートフォリオ構築・ファクター計算・ニュースの NLP スコアリングなどを含み、ローカル DB（SQLite / DuckDB）を使って状態を永続化・集計します。設計方針として「外部 API 呼び出しは明示的に行う」「ルックアヘッドバイアスを避ける」「本番と paper_trading を分離する」等が採られています。

主な特徴・機能
----------------
- Execution
  - ExecutionEngine による発注管理（ブローカー抽象化、リコンシリエーション、リスク管理）
  - paper_trading モードでは MockBroker を使用し、本番 DB と分離して data/paper_trading.db に記録
  - 再起動時の自動復旧（Reconciler）

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク、実行プロセス PID、データ鮮度を監視して monitoring DB に記録
  - TradeMonitor: 滞留注文（stale orders）や約定価格の異常を検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とリスクイベント記録
  - KillSwitch: 条件を満たしたら data/kill.flag に停止理由を書き込み ExecutionEngine に停止シグナルを送る
  - AlertManager: LINE Messaging API を使った通知（クールダウン管理）

- Research / Portfolio
  - factor_research: Momentum / Volatility / Value などのファクター計算（DuckDB を利用）
  - feature_exploration: 将来リターン、IC（Information Coefficient）、統計サマリー
  - portfolio: 候補選定、等重・スコア重み付け、ポジションサイズ計算、セクター制約・レジーム乗数

- AI
  - news_nlp: OpenAI（gpt-4o-mini）を使ったニュース記事の銘柄別センチメントスコアリング（ai_scores へ格納）
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定（market_regime に保存）

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit ベースの監視ダッシュボード（読み取り専用）

セットアップ手順
----------------
1. リポジトリを取得
   - git clone ... （リポジトリ URL）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - 追加で必要なパッケージがあれば適宜インストールしてください（sqlite3 は標準ライブラリ）

   ※ requirements.txt がある場合は pip install -r requirements.txt を利用してください。

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートの .env または .env.local を使って設定できます（config.py が自動ロードします）。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須（または重要）な環境変数（代表）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API を使う機能で必須
- KABUSYS_ENV — 起動環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading のマネキン約定挙動（instant|partial|never|reject）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

詳細な Settings は src/kabusys/config.py を参照してください。

使い方
------
一般的な実行例:

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用して MockBroker を使います。
    - 起動時に data/stop_requested.flag があると起動を行いません。
    - 実行中は data/execution.pid に PID を書きます。実行停止は stop flag または kill.flag により行われます。

- Monitoring（ポーリング）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を常に使用（KABUSYS_ENV に依らず）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で monitoring DB に接続します（読み取り専用 URI を使用）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数の代替）

- AI / レジーム判定・ニューススコアリング（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - これらは DuckDB 接続（duckdb.connect(...).cursor/connection）を渡して呼び出します。OPENAI_API_KEY が必要です。

停止・フラグ操作
- 実行中の ExecutionEngine や Monitoring を外部から停止したい場合:
  - data/stop_requested.flag を作成（任意の内容を書き込めます）。run_* スクリプトはループ検出時に終了します。
- システム停止トリガー（Kill Switch）
  - KillSwitch は条件を満たした場合 data/kill.flag に理由を書き込みます。ExecutionEngine は kill.flag の存在を検出して停止シグナルとして扱う設計です。
- kill.flag を手動で解除する場合:
  - ファイルを削除すると再度運用再開できます（KillSwitch.clear() を使用する API もあります）。

注意・トラブルシューティング
- OpenAI API を使う機能は OPENAI_API_KEY が必須（例外や ValueError が発生します）。
- DuckDB / SQLite ファイルが存在しない場合、該当機能はエラーになります（streamlit の場合は読み取り専用オープンに失敗して警告表示）。
- psutil を用いたプロセス優先度設定や CPU affinity 設定は権限や OS に依存します。AccessDenied の場合は警告ログを出してスキップします。
- monitoring_db.init_monitoring_db は既存 DB に対して簡単なマイグレーションを行います（カラム追加など）。ただし大規模なスキーマ変更はサポートしません。

ディレクトリ構成
----------------
（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（OpenAI）による銘柄センチメント
    - regime_detector.py         — マーケットレジーム判定（MA200 + マクロセンチメント）

  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite ベースの監視ログ永続化 layer
    - system_monitor.py          — システム状態・データ鮮度監視
    - trade_monitor.py           — 注文滞留・約定異常監視
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — kill.flag 書き込みユーティリティ
    - alert_manager.py           — LINE 通知
    - monitoring_engine.py       — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py     — Streamlit ダッシュボード

  - execution/
    - reconciler.py              — 起動時リコンシリエーション
    - order_manager.py           — 発注ワークフロー管理（OrderState 準拠）
    - order_repository.py        — （存在）OrderRepository（SQLite） — DBアクセス層
    - order_record.py            — OrderRecord / OrderState 定義
    - execution_engine.py        — ExecutionEngine（起動 / run_session 等）
    - broker_factory.py          — Broker クライアント生成（実運用 / mock 切替）
    - broker_api.py              — ブローカー API インターフェイス定義

  - portfolio/
    - portfolio_builder.py       — 候補選定・重み付け
    - position_sizing.py         — 株数決定・単元丸め・資金割当
    - risk_adjustment.py         — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py         — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py     — 将来リターン / IC / 統計
    - __init__.py

  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI

  - utils/
    - __init__.py
    - process_priority.py        — プロセス優先度・CPU affinity 設定ユーティリティ

補足
----
- 設定の自動ロード: config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動的に読み込みます（必要に応じて無効化可）。
- DB（DuckDB/SQLite）設計は、研究系（prices_daily / raw_financials / raw_news 等）と監視系（monitoring.db）が分離されています。
- テストや開発目的で paper_trading モードを使えば本番 DB/ブローカーへ影響を与えず検証できます。

ライセンス・貢献
----------------
（必要に応じてプロジェクトのライセンスや貢献方法をここに記載してください）

以上。必要であれば各コマンドの具体的な例（.env.example のテンプレート、systemd / supervisor 用のユニット例、Dockerfile など）を追記します。どの情報がさらに必要か教えてください。