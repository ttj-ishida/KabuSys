KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視モジュール群を含む小規模なトレーディング基盤です。  
主な機能は以下の通りです。

主な特徴（機能一覧）
------------------
- Execution（発注系）
  - ExecutionEngine を起動してブローカーとやり取りし注文を管理（run_execution.py）
  - 再起動時のリコンシリエーション（Reconciler）で OrderSent 状態を整合
  - OrderManager / OrderRepository による状態管理と永続化
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
  - リスク管理（RiskManager）と発注制御（rate limit / circuit breaker 等）

- Monitoring（監視系）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）
  - システム資源（CPU / メモリ / ディスク）やプロセス生存、データ鮮度を監視
  - 注文の滞留や約定価格異常を検出してリスクログへ記録
  - KillSwitch：所定条件で ExecutionEngine 停止用のフラグ（data/kill.flag）を生成
  - AlertManager：LINE Messaging API を使ったプッシュ通知（クールダウン管理あり）
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）

- Portfolio / Research
  - 銘柄選定・重み計算、ポジションサイズ計算、セクター制約、レジーム乗数などの純関数群（kabusys.portfolio）
  - DuckDB を用いたファクター計算、将来リターン計算、IC 計算、ファクター統計（kabusys.research）

- AI（LLM 統合）
  - ニュースを LLM（OpenAI）でセンチメント評価し ai_scores に保存（kabusys.ai.news_nlp）
  - マクロニュース + 1321（ETF）の MA200 乖離を合成して市場レジーム判定（kabusys.ai.regime_detector）
  - OpenAI API 呼び出しは堅牢化（リトライ・JSON 検証・スコアクリップ）

セットアップ手順
----------------

前提
- Python 3.9+（型注釈の一部やモジュール互換性に応じて調整）
- SQLite（標準ライブラリ）
- DuckDB（duckdb パッケージ）
- psutil（プロセス優先度 / CPU affinity）
- requests（LINE API）
- openai（OpenAI クライアント）
- streamlit（ダッシュボードを使う場合）

推奨インストール例（仮想環境）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージ（例）
   - pip install duckdb psutil requests openai streamlit

環境変数 / .env
- プロジェクトは起動時にプロジェクトルート（.git または pyproject.toml がある場所）から .env / .env.local を自動読み込みします（OS 環境変数が優先）。
- 自動読み込みを無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（一部・デフォルト値含む）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）
- KABU_API_PASSWORD: （必須）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- PAPER_FILL_MODE: instant|partial|never|reject（デフォルト instant）
- PID_FILE_PATH: data/execution.pid（デフォルト）
- KILL_FLAG_PATH: data/kill.flag（デフォルト）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（起動 / コマンド）
-----------------------

ExecutionEngine（発注エンジン）
- 本番/開発/ペーパートレードの設定に応じて動作:
  - 本番: KABUSYS_ENV=live
  - ペーパートレード: KABUSYS_ENV=paper_trading（MockBroker を使用）
- 起動:
  - python -m kabusys.run_execution
  - 注意: 起動時に Settings に基づき SQLite / DuckDB に接続し、Broker が初期化されます。

Monitoring（監視）
- run_monitoring.py は SystemMonitor のポーリングループを起動します。
- 起動:
  - python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書きできます（例: export MONITOR_POLL_INTERVAL=30）
- 実行開始時にプロセス優先度を "high" に設定しようとします（プラットフォーム依存・権限により失敗してスキップされます）。

Streamlit ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- デフォルトは data/monitoring.db（読み取り専用モードで開くため MonitoringEngine を先に起動してください）。

Paper Trading 検証レポート
- レポート生成スクリプト:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db /path/to/paper_trading.db
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）

AI 機能（ニュース NLP / レジーム判定）
- OPENAI_API_KEY を環境変数に設定するか、各関数に api_key 引数を渡してください。
- 例（ライブラリ呼び出し）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key="sk-...")

プロセス制御・停止
- ExecutionEngine の外部停止トリガーとして data/kill.flag を書き込む KillSwitch を利用します（Monitoring が評価し条件を満たすとファイルが作られます）。
- kill.flag 存在時は ExecutionEngine は起動側でフラグ読み取りを実装してシャットダウンする設計です（実装箇所を確認してください）。
- PID ファイル（Settings.pid_file_path）でプロセス生存チェックを行い stale PID の場合は削除してアラートを上げます。

注意事項 / 実装上のポイント
- Settings は .env ファイルを安全にパースして環境変数を設定します。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- Paper Trading は本番 DB と完全に分離された SQLite を使用（PAPER_TRADING_SQLITE_PATH）。
- OpenAI 呼び出しはリトライやレスポンス検証を行い、失敗時はフェイルセーフ（スコア 0.0 やスキップ）で継続する設計です。
- 一部関数（ポジション計算・ファクター計算など）は副作用のない純粋関数として実装されています（単体テストしやすい）。

主なディレクトリ構成
--------------------

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / 設定管理（.env ロード）
    - run_monitoring.py               — SystemMonitor ポーリングループ起動
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading レポート生成ツール
    - ai/
      - __init__.py
      - news_nlp.py                   — ニュース NLP / OpenAI 統合
      - regime_detector.py            — マクロセンチメント + MA200 によるレジーム判定
    - monitoring/
      - __init__.py
      - monitoring_db.py              — SQLite スキーマと永続化ヘルパ
      - system_monitor.py             — CPU/メモリ/ディスク / データ鮮度 / PID チェック
      - trade_monitor.py              — 注文滞留 / 約定異常監視
      - risk_monitor.py               — ドローダウン / ポジション数監視
      - monitoring_engine.py          — 各モニタを束ねるエンジン
      - kill_switch.py                — kill.flag 管理
      - alert_manager.py              — LINE 通知（クールダウン）
      - streamlit_dashboard.py        — Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他: broker_factory, execution_engine, order_repository 等が存在)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ
      - __init__.py

例: よく使うコマンド
-------------------
- 監視を開始（バックグラウンドで動かす場合はプロセスマネージャを利用）
  - python -m kabusys.run_monitoring

- エンジンを起動（ペーパートレード）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ライセンス / 貢献
-----------------
本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください。  
バグ報告・改善提案は Issue を立ててください。

附記（実装上のメモ）
-------------------
- デフォルトの DB パスは data 以下に置かれます。実運用では適切なディレクトリとバックアップ戦略を用いてください。
- process priority / cpu affinity の設定はプラットフォーム依存・権限依存です。権限が不足する場合は警告ログを出してスキップします。
- OpenAI / LINE API のキーは外部に漏れないよう注意して管理してください。

必要であれば、README にサンプル .env.example や起動スクリプトの systemd サービス例、Dockerfile、テスト手順などの追記を行います。どの項目を追加したいか教えてください。