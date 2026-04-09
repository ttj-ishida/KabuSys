KabuSys — 日本株自動売買ライブラリ
=================================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視に関するコアロジック群を提供する Python ライブラリです。  
主に以下の責務を持つモジュール群で構成されています。

- ファクター計算・リサーチ（DuckDB ベース）
- ポートフォリオ構築（候補選定・重み付け・株数算出・セクター制限）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- 発注エンジン周り（Order 管理、Broker API 抽象、リコンシリエーション）
- 監視（システム・注文・リスク監視、LINE 通知、Streamlit ダッシュボード）
- 環境変数 / 設定管理（.env 自動ロード）

主な機能
--------
- research:
  - momentum / volatility / value ファクターの計算（DuckDB を使用）
  - 将来リターン・IC（Information Coefficient）計算、特徴量サマリー
- portfolio:
  - BUY シグナルから候補選定、等重／スコア重み、リスク調整（セクター上限、レジーム乗数）
  - 株数決定（リスクベース／等配分／スコア配分）、単元丸め、投下資金のスケーリング
- ai:
  - ニュース記事を LLM（OpenAI）でセンチメント評価して ai_scores テーブルへ保存
  - マクロニュース + ETF (1321) MA200 を組み合わせた市場レジーム判定
- execution:
  - OrderManager / ExecutionEngine：注文のライフサイクル管理、送信、同期、キャンセル
  - Reconciler：再起動後の自動復旧（OrderSent の突合）
  - Broker API 用の Protocol/データモデルと例外定義
- monitoring:
  - MonitoringDB（SQLite）による永続化層
  - System / Trade / Risk モニタ、Kill Switch、AlertManager（LINE Push）
  - Streamlit ベースの簡易監視ダッシュボード

セットアップ手順
----------------
1. 必要な Python バージョン
   - Python >= 3.10 を想定（PEP 604 の型記法等を使用）

2. 依存パッケージ（最小例）
   pip install duckdb openai requests psutil streamlit

   （プロジェクトに requirements.txt があればそれを使ってください）

3. 環境変数 / .env
   - 設定は環境変数またはプロジェクトルートに置いた .env / .env.local から自動読み込みされます。
     自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。
   - 優先順位: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 主な環境変数（代表例）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須で呼ばれる箇所あり）
     - KABU_API_PASSWORD: kabuステーション API 用
     - OPENAI_API_KEY: OpenAI（ニュース NLP / レジーム判定）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE 通知）
     - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: 各種 DB パス
     - PID_FILE_PATH / KILL_FLAG_PATH など監視用パス
     - PAPER_FILL_MODE（paper_trading 用挙動）
   - .env のパースは quotes/escape/inline-comment をある程度考慮した自前実装です。

使い方（簡単な例）
-----------------

1) 設定値の参照
   from kabusys.config import settings
   token = settings.jquants_refresh_token
   openai_key = os.environ.get("OPENAI_API_KEY")  # または settings 経由で取得する実装を追加

2) DuckDB を使ったファクター計算
   import duckdb
   from datetime import date
   from kabusys.research import calc_momentum, calc_volatility, calc_value

   conn = duckdb.connect("data/prices.duckdb")
   result = calc_momentum(conn, date(2026, 3, 20))
   # result は {"date","code","mom_1m","mom_3m","mom_6m","ma200_dev"} の dict のリスト

3) ニュース NLP スコアリング（OpenAI 必須）
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   # api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
   written = score_news(conn, date(2026, 3, 20), api_key="sk-xxxx")
   print(f"written scores: {written}")

4) 市場レジーム判定
   from kabusys.ai.regime_detector import score_regime
   score_regime(conn, date(2026, 3, 20), api_key="sk-xxxx")

5) 監視 DB 初期化（SQLite）
   import sqlite3
   from kabusys.monitoring import init_monitoring_db

   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)

6) Streamlit ダッシュボード起動
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

7) ExecutionEngine / OrderManager 等
   - 実行環境では BrokerAPIProtocol を実装したクライアント、OrderRepository（SQLite 実装）、
     RiskManager、OrderManager などの具象オブジェクトを用意して ExecutionEngine を組み立てます。
   - テスト用途では一部の外部呼び出し（OpenAI / broker）をモック化して単体テストが可能です。

注意点 / テスト向け設定
---------------------
- 自動 .env 読み込みはプロジェクトルートが見つからない場合スキップされます（パッケージ配布後の安全策）。
- テスト時に .env の自動読み込みを止めたい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは内部で再試行・バックオフ処理があり、エラー時はフェイルセーフ（スコア 0.0 で継続等）設計です。
- 複雑な本番起動（ExecutionEngine 等）はプロセス監視、PID / kill.flag の運用ルールに注意してください。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py                  — パッケージ定義、バージョン
- config.py                    — 環境変数 / .env 自動読み込み、Settings クラス
- ai/
  - __init__.py
  - news_nlp.py                — ニュース記事の LLM センチメント評価、ai_scores 書込
  - regime_detector.py         — 市場レジーム判定（ETF MA + マクロセンチメント）
- research/
  - __init__.py
  - factor_research.py         — momentum / volatility / value 等の計算
  - feature_exploration.py     — 将来リターン、IC、統計サマリ
- portfolio/
  - __init__.py
  - portfolio_builder.py       — 候補選定・重み計算
  - position_sizing.py         — 株数算出、資金スケーリング
  - risk_adjustment.py         — セクター上限・レジーム乗数
- execution/
  - broker_api.py              — Broker API のデータモデル・Protocol・例外
  - order_manager.py           — 注文状態遷移と broker 送信ロジック
  - reconciler.py              — 再起動時の照合・自動復旧
  - execution_engine.py        — Signal Queue Pull 型エンジン（セッション管理）
  - ...（OrderRepository 等、他モジュールと連携）
- monitoring/
  - __init__.py
  - monitoring_db.py           — SQLite 永続化層（schema + helper）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py           — LINE Push 通知
  - kill_switch.py
  - streamlit_dashboard.py     — Streamlit ダッシュボード
- portfolio/, research/, ai/ の各モジュールは純粋関数で DB 参照や副作用を抑えた設計になっています。

ライセンス / 貢献
----------------
この README ではライセンス情報は含めていません。プロジェクトの LICENSE ファイルや貢献ガイドラインに従ってください。

最後に
------
実運用には Broker 実装、OrderRepository の具体実装、リスクパラメータの調整、テスト（差分検証）が必要です。本 README はコードベースの主要機能と運用上の概要をまとめたものです。必要があれば特定モジュールの詳細ドキュメント（API サンプル、DB スキーマ例、運用手順）を追加で作成します。