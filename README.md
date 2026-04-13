README
======

概要
----
KabuSys は日本株の自動売買システム向けに設計された Python パッケージです。本リポジトリは取引実行エンジン、監視／アラート、ポートフォリオ構築、リサーチ（ファクター計算）およびニュース NLP を用いた補助機能を含みます。設計方針として「本番/ペーパートレードの分離」「ルックアヘッドバイアス防止」「外部 API 呼び出しの失敗は安全にフォールバックする」などが採用されています。

主な機能
--------
- ExecutionEngine（発注エンジン）
  - ブローカークライアント（本番 / paper_trading の切替）
  - リコンシリエーション（再起動後の注文/ポジション突合）
  - リスク管理（ポジション比率・利用率など）
- Monitoring（監視）
  - システム状態（CPU/メモリ/ディスク/プロセス）監視
  - 注文滞留・約定異常検出
  - ドローダウン・ポジション上限監視
  - kill.flag による ExecutionEngine 停止シグナル
  - LINE へのプッシュ通知（AlertManager）
  - Streamlit ダッシュボード（監視 UI）
- Portfolio モジュール（銘柄選定・重み計算・株数決定）
  - 候補選定（スコア順）
  - 等金額 / スコア加重 / リスクベースのポジションサイズ計算
  - セクター制限、レジーム乗数
- Research（ファクター計算、特徴量解析）
  - Momentum / Volatility / Value ファクターの計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini 想定）でニュースをスコアリングし ai_scores に格納
  - マクロニュース + ETF MA200 乖離で市場レジーム判定
- ユーティリティ
  - 環境変数読み込み（.env / .env.local の自動ロード）
  - プロセス優先度設定、CPU affinity ユーティリティ
  - Monitoring 用 SQLite 初期化ユーティリティ

前提条件
--------
- Python 3.10 以上（X | None のタイプヒントを使用）
- 必須パッケージ（一部の機能で必須）
  - duckdb
  - psutil
  - requests
- AI 機能を使う場合
  - openai（OpenAI SDK）
- Streamlit ダッシュボードを使う場合
  - streamlit

インストール（例）
-----------------
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests
   - AI 機能を使う場合: pip install openai
   - ダッシュボードを使う場合: pip install streamlit

環境変数・設定 (.env)
--------------------
Settings クラスは環境変数から設定を読み込みます。プロジェクトルート（.git または pyproject.toml がある場所）に .env/.env.local を置くと自動で読み込みます。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

主要な環境変数（代表例）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject）
- PID_FILE_PATH, KILL_FLAG_PATH: PID/kill flag ファイルのパス
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）

セットアップ手順
---------------
1. データディレクトリを作成
   - mkdir -p data

2. 環境変数を準備
   - プロジェクトルートに .env を作成し必要なキーを設定
   - 例:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development

3. 必要であれば DuckDB / SQLite の初期テーブルを用意（多くの起動スクリプトで自動作成されます）
   - 監視 DB は init_monitoring_db() により起動時に作成されます（冪等）
   - Streamlit は読み取り専用 URI で接続できます

起動と使い方
------------

ExecutionEngine（実戦 / ペーパー）
- 本番または開発用起動:
  - python -m kabusys.run_execution
- ペーパートレードで起動（本番 DB と分離。PAPER_TRADING_SQLITE_PATH を設定するかデフォルトを使用）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を使うと MockBrokerClient（実装による）と data/paper_trading.db が使用されます。
- 起動時にプロセス優先度を "high" に設定します（psutil により platform ごとに設定を試みます）。

Monitoring（監視ループ）
- 標準起動:
  - python -m kabusys.run_monitoring
- ポーリング間隔を変更する:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 無効な値や 0 以下はデフォルト（60秒）にフォールバックします
- 監視は常に Settings.sqlite_path（本番の monitoring.db）を使用し、.env の KABUSYS_ENV に依存せず本番 DB を参照します。

Streamlit ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine を先に起動して監視ログを生成してください。

Paper Trading 検証レポート
- 検証レポートを生成（標準出力）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
- レポートは uptime, fill_rate, send_rate, latency 等の指標を算出し PASS/FAIL を出力します。

AI（ニューススコア / レジーム判定）
- ニューススコアリングはライブラリ関数として提供（例: kabusys.ai.score_news）。OpenAI API キーが必要です（OPENAI_API_KEY または引数で渡す）。
- レジーム判定は kabusys.ai.regime_detector.score_regime を呼ぶことで market_regime テーブルに書き込みます。

プロセス管理 / kill flag
- ExecutionEngine は Settings.pid_file_path に PID を書きます（起動時に PID を書く実装がある前提）。
- KillSwitch（監視側）は Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込むことで ExecutionEngine に停止シグナルを送ります。KillSwitch は冪等で既存ファイルを再書込しません。
- Settings.kill_flag_clear_on_start を 1 に設定して、起動時に既存の kill.flag をクリアする運用も可能です（関連処理が実装されている場合に有効）。

デバッグ / ローカル開発メモ
- Settings モジュールはプロジェクトルートから .env/.env.local を自動読み込みしますが、テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- openai や外部 API 呼び出しは失敗時に安全にフォールバックするよう設計されています。ユニットテストでは _call_openai_api 等をモックすることを想定しています。

主要ファイル・ディレクトリ構成
----------------------------
（抜粋、主要モジュールのみ）

- src/kabusys/
  - __init__.py            — パッケージメタ情報
  - config.py              — 環境変数 / Settings
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py     — SQLite 監視 DB 初期化 + 永続化 API
    - system_monitor.py    — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py     — 注文滞留・約定異常監視
    - risk_monitor.py      — ドローダウン / ポジション上限監視
    - kill_switch.py       — kill.flag 管理
    - alert_manager.py     — LINE 通知クライアント
    - monitoring_engine.py — 監視モジュール束ね処理 / ループ
    - streamlit_dashboard.py — Streamlit ベースの監視 UI
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - order_record.py
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/
    - pipeline.py (価格データ取得補助等, ※一部参照)
    - stats.py (zscore 等ユーティリティ)
  - utils/
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ

補足
----
- 多くのコンポーネントは「DB 参照なしの純粋関数」または副作用を最小化する設計が採られており、単体テストが書きやすくなっています。
- DuckDB はリサーチ / ファクター計算用に使用され、prices_daily / raw_financials / raw_news 等のテーブルを前提とします。データ取り込みパイプラインは別途実装される想定です。
- 実際のブローカークライアント（kabuステーション等）の実装部分は broker_api / broker_factory を介して差し替え可能です。paper_trading 用のモックは settings.is_paper を基に分離されています。

ライセンス・貢献
----------------
（ここにプロジェクト固有のライセンスや貢献ルールを記載してください）

お問い合わせ
------------
不明点・バグ報告・提案はリポジトリの Issue を通じてお願いします。