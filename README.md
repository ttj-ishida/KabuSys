KabuSys — 日本株自動売買プラットフォーム（README）
=================================

概要
----
KabuSys は日本株向けのデータプラットフォームおよび自動売買支援ライブラリです。  
主に以下を提供します：

- J-Quants API を用いた株価・財務・カレンダーデータの差分 ETL（DuckDB 保存）
- ニュースの収集・前処理・LLM によるニュースセンチメント算出（OpenAI）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM スコアを合成）
- ファクター計算・特徴量探索（モメンタム・ボラティリティ・バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 発注・約定の監査ログ用スキーマ初期化（監査トレーサビリティ）
- 環境変数設定管理（.env の自動読み込み、Settings オブジェクト）

本 README はソース内の実装に基づく使い方、セットアップ、ディレクトリ構成を日本語でまとめたものです。

主な機能
--------
- データ ETL
  - 日次 ETL（run_daily_etl）：市場カレンダー、株価日足、財務データの差分取得・保存・品質チェック
  - J-Quants API クライアント（fetch / save 系関数）とレート制御・リトライ、ID トークン自動リフレッシュ
- ニュース処理 / AI
  - RSS 取得・前処理（news_collector.fetch_rss、preprocess_text 等）
  - 銘柄ごとのニュースセンチメント算出（kabusys.ai.news_nlp.score_news）
  - 市場レジームスコア算出（kabusys.ai.regime_detector.score_regime）
  - OpenAI の JSON Mode を用いた堅牢なレスポンスパース・リトライ制御
- リサーチユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（情報係数）計算、ファクター統計サマリ
  - zscore 正規化ユーティリティ
- データ品質
  - 欠損 / スパイク / 重複 / 日付不整合チェック（run_all_checks）
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 を追跡するテーブル群の DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - settings オブジェクト（kabusys.config.settings）経由で環境変数を統一的に取得
  - 自動 .env ロード（プロジェクトルート検出: .git / pyproject.toml）、無効化フラグあり

セットアップ手順
----------------

1. Python と仮想環境
   - Python 3.9+ を想定（実際の互換性は環境に依存します）
   - 仮想環境作成（任意）:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（最小例）
   - 必要な主なパッケージ：
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   > プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください。
   > 開発インストールを行う場合:
   > pip install -e .

3. 環境変数 (.env) の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な（代表的な）環境変数（例）:

     JQUANTS_REFRESH_TOKEN=（必須: J-Quants リフレッシュトークン）
     OPENAI_API_KEY=（OpenAI API キー: news_nlp / regime_detector に使用）
     KABU_API_PASSWORD=（kabuステーション API パスワード）
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     SLACK_BOT_TOKEN=（Slack 通知用トークン）
     SLACK_CHANNEL_ID=（Slack 通知用チャンネルID）
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PID_FILE_PATH=data/execution.pid
     CPU_THRESHOLD_PCT=90.0
     MEMORY_THRESHOLD_PCT=85.0
     DISK_THRESHOLD_PCT=90.0
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   - settings からはこれらを型変換済みで取得できます（例: settings.duckdb_path は Path 型）。

使い方（基本例）
---------------

以下は主要 API の利用例です。実行前に .env を用意し、DuckDB への書き込み用ディレクトリが存在することを確認してください。

- DuckDB 接続作成と日次 ETL 実行

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントのスコア算出（AI）

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示するか、環境変数 OPENAI_API_KEY を設定しておく
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"scored {count} symbols")

- 市場レジーム判定

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY が使われる

- 監査ログ DB 初期化（監査専用 DB を作る）

  from kabusys.config import settings
  from kabusys.data.audit import init_audit_db

  # settings.duckdb_path を監査用に使うことも可能、別ファイルに分けても良い
  conn = init_audit_db(settings.duckdb_path)  # もしくは init_audit_db("data/audit.duckdb")

- ニュース RSS の取得（保存はアプリ側で raw_news などに INSERT）

  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])

主な注意点
- Look-ahead bias を避ける設計が随所に採用されています（関数は内部で date.today() を直接参照しない等）。
- OpenAI 呼び出しは JSON Mode を期待しており、レスポンスのパースにフォールバック処理やリトライが含まれます。API 失敗時はフェイルセーフとしてゼロスコアにフォールバックする設計箇所があります。
- DuckDB の executemany に空リストを渡すとエラーになる場合があるため、コード各所で空チェックが行われています。
- .env の自動ロードはプロジェクトルート（.git / pyproject.toml）を基準に行われます。自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要ディレクトリ構成
--------------------

（src/kabusys をルートとする抜粋）

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数の取得・検証、自動 .env ロード）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースを銘柄ごとに集約して OpenAI に投げ、ai_scores へ保存するロジック
    - regime_detector.py  — ETF MA とマクロニュース LLM を合成して market_regime を更新する
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch / save / get_id_token 等）
    - pipeline.py         — ETL パイプライン（run_prices_etl/run_financials_etl/run_calendar_etl/run_daily_etl）
    - calendar_management.py — JPX カレンダー管理（営業日判定、next/prev_trading_day など）
    - news_collector.py   — RSS 収集・前処理・安全対策（SSRF 対策等）
    - quality.py          — データ品質チェック群（欠損・スパイク・重複・日付不整合）
    - stats.py            — z-score 正規化などの統計ユーティリティ
    - audit.py            — 監査ログ用スキーマ定義・初期化ユーティリティ
    - etl.py              — ETL 結果型の再エクスポート（ETLResult）
  - research/
    - __init__.py
    - factor_research.py  — momentum / volatility / value のファクター計算
    - feature_exploration.py — forward returns / IC / factor summary 等

開発者向けメモ
---------------
- テスト用に自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI API 呼び出し部分はテストで差し替えやすいように _call_openai_api を関数として定義しており、unittest.mock.patch によるモックが容易です。
- J-Quants API への実装では内部で固定間隔レートリミッターとリトライを行っています。テストでは _request などをモックすると良いでしょう。
- DuckDB のタイムスタンプは UTC に統一する方針です（audit.init_audit_schema では SET TimeZone='UTC' を実行します）。

サポート・拡張
--------------
- 新しいニュースソースを追加する場合は news_collector.DEFAULT_RSS_SOURCES を拡張し、fetch_rss を通して取得後 raw_news に保存するワークフローを作成してください。
- 監視や通知は slack 経由を想定しているため、Slack のトークン / チャンネル設定を環境変数に入れて利用してください（実際の監視モジュールは monitoring パッケージ配下などに実装される想定です）。

最後に
------
この README はコードベースの実装（docstring と関数設計）に基づいてまとめています。実運用時は J-Quants / OpenAI の使用規約、API レート制限、秘密情報の管理（トークンを安全に保管すること）に十分注意してください。ご不明な点や README に追加したい情報があれば教えてください。