KabuSys — README (日本語)
=======================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ユーティリティ群です。本リポジトリは以下の主要コンポーネントを含みます。

- ExecutionEngine: シグナルを受けてブローカーへ発注するエンジン（本番 / ペーパートレード対応）
- MonitoringEngine: システム稼働状況・注文滞留・リスク（ドローダウン等）を定期監視してログ/アラートを出す
- Research: ファクター計算・特徴量解析・将来リターンやIC計算
- AI ユーティリティ: ニュースの NLP によるセンチメントスコア付与、レジーム判定（OpenAI API を使用）
- Streamlit ベースの監視ダッシュボード

主要機能
--------
- シグナルを取り込み発注（Signal Queue Pull 型）、OrderManager によるクラッシュ耐性ある2相永続化フロー
- 再起動後の自動リコンシリエーション（Reconciler）
- 発注 Gate（信号レベル・実行レベル・ドローダウン監視）による安全性担保
- 監視ログを SQLite に永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- LINE 送信によるアラート（AlertManager）
- ニュース記事を LLM（gpt-4o-mini 等）でスコアリングして ai_scores に書込む（部分失敗耐性、バッチ化、リトライ）
- DuckDB を使った時系列ファクター計算（momentum/volatility/value など）
- Streamlit による監視ダッシュボード表示

要件（主な依存）
----------------
少なくとも以下のパッケージが必要です（バージョンは適宜調整してください）:

- Python 3.9+
- duckdb
- psutil
- requests
- streamlit (ダッシュボード利用時)
- openai (AI 機能利用時)

例:
- pip install duckdb psutil requests streamlit openai

設定（環境変数 / .env）
---------------------
アプリケーションは環境変数（またはプロジェクトルートの .env / .env.local）から設定を読み込みます。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効にできます。

代表的な環境変数（主なもののみ）:
- KABUSYS_ENV: 起動環境。valid: development, paper_trading, live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使用し、paper 用 SQLite（デフォルト data/paper_trading.db）へ分離して記録します
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な箇所で要求される）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須な箇所で要求される）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager の通知に使用（空だと送信はスキップ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: Monitoring 用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper トレード用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: MonitoringEngine のポーリング間隔（秒、デフォルト 60、1 以上の正整数）
- PAPER_FILL_MODE: Paper ブローカーの fill 挙動（instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

簡易 .env 例:
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

セットアップ手順
----------------
1. リポジトリをクローンし、Python 仮想環境を作成・有効化する:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール:
   - pip install duckdb psutil requests streamlit openai

3. 必要に応じて .env をプロジェクトルートに作成（.env.example を参考に）。

4. データディレクトリを作成:
   - mkdir -p data

5. 初回起動時は各スクリプトが必要な DB テーブルを自動作成します（例: init_monitoring_db）。

使い方
-------

- 実行エンジン（ExecutionEngine）の起動
  - 本番/開発/ペーパートレード選択は KABUSYS_ENV による。
  - 実行:
    - python -m kabusys.run_execution
    - または python src/kabusys/run_execution.py
  - 注意:
    - Paper トレード (KABUSYS_ENV=paper_trading) の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離して記録されます。
    - 実行開始時に pid ファイルを書き、終了時に削除します。
    - KillSwitch（data/kill.flag）により外部から停止指示を出せます。

- 監視ループ（MonitoringEngine）の起動
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）。
  - 実行:
    - python -m kabusys.run_monitoring
    - または python src/kabusys/run_monitoring.py

- Streamlit ダッシュボード
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

- AI 関連（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を環境変数に設定して使用します。
  - news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続と日付を与えてスコアを ai_scores テーブルに書き込みます。
  - regime_detector.score_regime(conn, target_date, api_key=None) — market_regime テーブルへ書き込みます。

運用上のポイント / 注意点
-------------------------
- Settings は .env / .env.local をプロジェクトルートから自動読み込みします（CWD ではなく package の位置から .git / pyproject.toml を探索）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL は正の整数でなければデフォルト 60 秒へフォールバックします（0 や負の値は無効）。
- Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用します（監視は常に本番 DB を見る設計）。
- ExecutionEngine は paper_trading モードであれば本番 DB と完全分離された paper_sqlite_path を使用します。
- OpenAI を使う機能は API レスポンスの不確実性を考慮し、429/ネットワーク断/5xx に対するリトライや、解析失敗時のフェイルセーフ（スコア 0 やスキップ）を備えていますが、API キーが未設定だと ValueError を送出する箇所があります。
- AlertManager（LINE）にトークンが未設定の場合は送信をスキップしログに記録します。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / .env 読込・Settings
- run_execution.py                — ExecutionEngine 起動スクリプト
- run_monitoring.py               — SystemMonitor ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py                    — ニュースの LLM スコアリング
  - regime_detector.py             — 市場レジーム判定
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - order_record.py
  - reconciler.py
  - risk_manager.py
  - broker_api.py / broker_factory.py (ブローカー抽象)
- monitoring/
  - monitoring_db.py               — SQLite スキーマと永続層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - process_priority.py

（その他のファイルや実装ファイルはソース内に含まれます）

開発 / テストに関して
---------------------
- DB スキーマ作成は init_monitoring_db() にて冪等に実行されます。実行時に自動で必要テーブルが作成されます。
- unit テスト等で自動 .env ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分は内部で関数を抽象化しており、テスト時にモック差し替えしやすい設計になっています（関数単位で patch 可能）。

サポート / 貢献
----------------
バグ報告や改善提案は Issue を通してください。設計上の意図や挙動（例えばペーパートレード分離、kill flag の動作、DB マイグレーション等）についてはソースドキュメント（各モジュールの docstring）を参照してください。

この README はソースコード（docstring と実装）に基づいて作成されています。動作や設定に関して不明点があれば、該当するモジュールの docstring を確認してください。