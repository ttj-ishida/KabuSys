KabuSys — 日本株自動売買プラットフォーム
====================================

概要
----
KabuSys は日本株向けのデータプラットフォームおよび自動売買支援ライブラリです。  
主に以下を目的としたモジュール群を提供します。

- J-Quants API を用いたデータ ETL（株価・財務・マーケットカレンダー）
- ニュース収集・NLP による銘柄センチメント付与（OpenAI）
- 市場レジーム判定（ETF とマクロニュースを統合）
- ファクター計算・特徴量探索（リサーチ用途）
- データ品質チェック・監査ログ（トレーサビリティ）
- DuckDB を用いたローカルデータストア

機能一覧
--------
主な機能（モジュール単位）

- kabusys.config
  - .env（および .env.local）自動読み込み（プロジェクトルート検出）
  - settings オブジェクトによる環境変数アクセスと検証
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 + DuckDB 保存）
  - pipeline: ETL パイプライン（run_daily_etl, run_prices_etl 等）
  - news_collector: RSS 取得・前処理・raw_news 保存
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: 市場カレンダー管理・営業日判定
  - audit: 監査ログテーブルの初期化 / DB 作成ユーティリティ
  - stats: 汎用統計ユーティリティ（zscore_normalize 等）
- kabusys.ai
  - news_nlp.score_news: ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.score_regime: ETF とマクロニュースを組み合わせて market_regime を算出
- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリュー の自動計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリ 등

前提・依存
----------
（代表的なもの）

- Python 3.10+
- duckdb
- openai (OpenAI の公式クライアント)
- defusedxml

インストール例（開発）
--------------------
1. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install duckdb openai defusedxml
   - （プロジェクトを editable にする場合）pip install -e .

環境変数（.env）
----------------
プロジェクトは .env/.env.local（プロジェクトルート）を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。主に使う変数の例:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用。
- OPENAI_API_KEY (必須 for AI 機能)
  - OpenAI の API キー（news_nlp / regime_detector で使用）。
- KABU_API_PASSWORD
  - kabuステーション API を使う場合のパスワード。
- KABU_API_BASE_URL
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- LOG_LEVEL
  - ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_ENV
  - 環境（development / paper_trading / live）

設定は kabusys.config.settings からプロパティとして参照できます。

セットアップ手順（実践）
---------------------
1. リポジトリをクローンして依存をインストール。
2. プロジェクトルートに .env を作成（.env.example を参考に）。
3. DuckDB ファイルの親ディレクトリを作成しておく（save 関数が自動で作る場合もある）。
4. OpenAI を利用する場合は OPENAI_API_KEY を設定。
5. J-Quants を利用する場合は JQUANTS_REFRESH_TOKEN を設定。

基本的な使い方（コード例）
------------------------

- DuckDB 接続を用意する:
  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（market calendar, prices, financials, quality checks）:
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースの NLP スコアリング（ai_scores へ書き込み）:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"scored {written} codes")

- 市場レジーム判定（market_regime テーブルへ書き込み）:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB の初期化:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/monitoring.duckdb")

- 監査スキーマを既存 conn に追加:
  from kabusys.data.audit import init_audit_schema
  from kabusys.data import audit
  audit.init_audit_schema(conn, transactional=True)

注意点 / 動作方針
------------------
- ルックアヘッドバイアス対策: 多くの関数は datetime.today()/date.today() を内部で直接参照せず、外部から target_date を渡す設計です。バックテスト時は必ず適切な target_date を渡してください。
- OpenAI 呼び出し: API の失敗時は堅牢性を優先してフォールバック（0.0 やスキップ）する実装が多くあります。ログを確認してください。
- .env 読み込み: プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して決定します。CWD に依存しません。
- 自動 .env ロードを無効化したい場合:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数で指定してください（テスト時に便利）。

ディレクトリ構成
----------------
主要なソースツリー（src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + 保存関数
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - news_collector.py             — RSS 収集・前処理
    - calendar_management.py        — マーケットカレンダー管理・営業日ロジック
    - quality.py                    — データ品質チェック
    - stats.py                      — 汎用統計ユーティリティ
    - audit.py                      — 監査ログスキーマ初期化 / DB ユーティリティ
    - etl.py                        — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/ボラティリティ/バリュー
    - feature_exploration.py        — 将来リターン / IC / summary

ログと監視
----------
- ログレベルは環境変数 LOG_LEVEL で制御できます（デフォルト INFO）。
- 実行監視用の PID/KILL フラグやリソース閾値（CPU/Memory/Disk）は settings 経由で設定可能です（PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT 等）。

開発・テストに関するヒント
--------------------------
- OpenAI／J-Quants の API 呼び出しは外部依存があるため、ユニットテストでは各モジュール内の API 呼び出し関数を patch/mocking することを推奨します（コード内にもモック差し替えを想定した hook が記載されています）。
- news_collector や jquants_client はネットワークを含むため、CI ではモックレスポンスを用意してテストしてください。
- DuckDB にはインメモリ接続（":memory:"）が使用可能です。テストで簡単に DB を用意できます。

ライセンス
----------
（この README では省略しています。プロジェクトの LICENSE を参照してください。）

最後に
------
本 README はソースコードの注釈・ドキュメント文字列を元にまとめています。実際に運用する際は .env.example を用意し、秘密情報（API キー等）は安全に管理してください。ご不明点があれば個別のモジュールや具体的なユースケースについて質問してください。