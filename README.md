KabuSys — 日本株自動売買システム
================================

この README はリポジトリ内の主要なモジュール・スクリプトの使い方、セットアップ、ディレクトリ構成をまとめたドキュメントです。コードベースは自動売買エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースNLP / レジーム判定）等のコンポーネントで構成されています。

要点
----
- Python 3.10+ が必要（型ヒントの union 演算子などを使用）。
- 永続化: SQLite（監視ログ / ペーパートレード用）＋ DuckDB（時系列価格・ファクター集計）。
- 外部 API: Kabuステーション相当 API、J-Quants、OpenAI（任意。ニュースNLP / レジーム判定で使用）。
- プロセス優先度や CPU affinity を設定するユーティリティを備え、監視ループや実行エンジンは高優先度で実行されます。

主な機能
--------
- ExecutionEngine: ブローカーへ発注、リスク管理、注文管理、再起動時のリコンシリエーション。
- Monitoring: システム状態（CPU/メモリ/ディスク/プロセス）、注文滞留、約定異常、ドローダウンやポジション上限の監視、LINEへアラート送信。
- Portfolio construction: シグナルの候補選定、等配分／スコア配分、ポジションサイズ算出、セクター上限やレジーム乗数の適用。
- Research: DuckDB 上の価格・財務データからモメンタム／ボラティリティ／バリュー等のファクター計算、特徴量解析（IC等）。
- AI: ニュース記事のセンチメントを OpenAI でスコアリング（ai.news_nlp.score_news）、マクロセンチメント + ETF MA200乖離による市場レジーム判定（ai.regime_detector.score_regime）。
- ツール: Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）、Streamlit ダッシュボード（監視ビュー）。

セットアップ手順
----------------
1. Python と仮想環境
   - Python 3.10 以上を用意。
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - requirements.txt がある想定で:
     - pip install -r requirements.txt
   - 最低必要なパッケージ（主なもの）:
     - duckdb, psutil, requests, openai, streamlit

   ※ リポジトリに requirements.txt が無い場合は上記パッケージを個別にインストールしてください。

3. 環境変数と .env
   - プロジェクトルート（.git または pyproject.toml のある場所）に .env / .env.local を置くと自動で読み込まれます（テスト時に自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 必須（実行に必要な場合）:
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
     - KABU_API_PASSWORD — Kabu API パスワード
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - 任意の設定（デフォルト値があるもの）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject、デフォルト: instant）
     - OPENAI_API_KEY（AI 機能を有効にする場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_/MEMORY_/DISK_THRESHOLD_PCT 等

使い方（主要コマンド）
--------------------

- 監視ループ起動（Monitoring）
  - src/kabusys/run_monitoring.py を実行すると SystemMonitor が定期ポーリングして監視ログに書き込みます。
  - コマンド例:
    - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。1 未満または不正値は無視されデフォルトへフォールバック。
  - 補足: 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は本番 DB を参照）。

- 実行エンジン起動（Execution）
  - src/kabusys/run_execution.py が ExecutionEngine を起動します。
  - コマンド例:
    - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、 paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
  - 起動時にプロセス優先度を "high" に設定します（プラットフォーム依存で成功しない場合は警告を出します）。

- Paper Trading 検証レポート
  - ツール: src/kabusys/tools/paper_verification_report.py
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH: SQLite DB パス（PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルト data/paper_trading.db）

- Streamlit ダッシュボード（監視画面）
  - ファイル: src/kabusys/monitoring/streamlit_dashboard.py
  - 実行例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite DB に接続し、Positions / Orders / System / Overview を表示します。

- AI 機能（ニュース NLP / レジーム判定）
  - ニューススコアリング（ai.news_nlp.score_news）
    - 関数を Python から呼ぶ、または実行スクリプト化して日次で実行します。OpenAI API キーが必要です。
  - レジーム判定（ai.regime_detector.score_regime）
    - DuckDB にある price/raw_news をもとに判定し market_regime テーブルへ書き込みます。OpenAI API が無い場合はマクロスコアを 0.0 固定で継続します。
  - いずれも API の呼び出しはリトライやフォールバックを持ちます（フェイルセーフ設計）。

設定・環境変数（主要）
--------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト instant）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（ニュース/レジーム機能で必須）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用（必須とされる箇所あり）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE通知（任意）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 実行制御用
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値

注意点・設計上のポイント
-----------------------
- .env の読み込みはプロジェクトルートを自動検出して行われます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading は本番 DB と分離され、PAPER_TRADING_SQLITE_PATH に記録されます。
- OpenAI の呼び出しは冗長性を加味したリトライ戦略・JSON バリデーションを実装しており、API 失敗時は安全側フォールバックを行います（例: macro_sentiment=0.0）。
- MonitoringDB（SQLite）は冪等で初期化します。既存 DB に後方互換性のためのマイグレーション（カラム追加等）も含まれます。
- プロセス優先度・CPU affinity の設定は psutil を使って OS ごとに差分を吸収します。権限不足等で設定できない場合はログが出ますが実行自体は続行します。

ディレクトリ構成（抜粋）
-----------------------
- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - data/                      — （想定）DuckDB/データロード関連（コード本体は省略）
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py      — 実行エンジン（主要ロジック）
    - broker_factory.py
    - broker_api.py
    - ...                      — 注文関連ロジック
  - monitoring/
    - monitoring_db.py         — SQLite テーブル定義・CRUD
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py     — 複数モニタの束ね
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py
  - その他、モジュール群...

開発・運用のヒント
------------------
- ローカル検証:
  - KABUSYS_ENV=paper_trading を使えば実際のブローカーに接続せず paper DB で動作確認できます。
- デバッグログ:
  - Settings.log_level を LOG_LEVEL 環境変数で変更できます（"DEBUG","INFO",...）。
- kill.flag:
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。必要に応じて起動時に KILL_FLAG_CLEAR_ON_START=1 を設定してフラグをクリアしてください。
- マイグレーション:
  - monitoring_db.init_monitoring_db は安全に何度でも呼べる設計です。起動時に必ず呼び出すことでテーブル存在を保証します。

問い合わせ・拡張
----------------
- 新しい外部 API やブローカーを追加する場合は execution/broker_* の抽象（BrokerAPIProtocol）を実装してください。
- AI モジュールやファクター設計は外部に依存しないように DuckDB のクエリ + Python ロジックで実装されています。データパイプラインを整備して prices_daily / raw_financials / raw_news 等を投入してください。

以上がプロジェクトの概要と使い方です。必要であれば各モジュールの詳細な API ドキュメント（関数の引数・戻り値、エラー条件など）も作成できます。どの部分を詳しく説明すればよいか教えてください。