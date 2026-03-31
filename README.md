KabuSys — 日本株自動売買 / データプラットフォーム
=================================

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買ユーティリティ群を提供する Python パッケージです。J-Quants API からのデータ取得・ETL、ニュース収集・NLP（OpenAI）によるセンチメント評価、ファクター計算、監査ログ（オーダー / 約定トレース）など、バックテスト・運用のための基盤機能を含みます。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を参照しない実装が基本）
- DuckDB を使ったローカルデータベース（ETL / 分析）
- 冪等性を重視（ON CONFLICT などで重複上書き）
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備える
- テスト容易性のため一部内部呼び出しは差し替え可能（モックしやすい）

機能一覧
--------
- データ取得 / ETL
  - J-Quants から株価日足、財務データ、上場情報、マーケットカレンダーを取得（jquants_client）
  - run_daily_etl による日次 ETL（差分取得、品質チェック、カレンダー先読み 等）
- データ品質チェック（data.quality）
  - 欠損、重複、スパイク、日付不整合を検出
- カレンダー管理（data.calendar_management）
  - 営業日判定、前後営業日取得、期間内営業日列挙、カレンダー更新ジョブ
- ニュース収集（data.news_collector）
  - RSS 収集、URL 正規化、前処理、raw_news への冪等保存補助
- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント評価（ai_scores へ保存）
- 市場レジーム判定（ai.regime_detector）
  - ETF（1321）の MA200 乖離とマクロニュース LLM スコアを合成して market_regime を生成
- リサーチ / ファクター計算（research）
  - Momentum / Volatility / Value 等のファクター計算、将来リターン、IC、統計サマリー
- 監査（audit）
  - signal_events / order_requests / executions テーブルの初期化と監査DBユーティリティ

セットアップ手順
--------------
前提
- Python 3.10 以上（型 | 演算子、型注釈の仕様に依存）
- インターネット接続（J-Quants / OpenAI を使用する場合）
- DuckDB をローカルで利用可能

インストール（例）
- 仮想環境を作成・有効化してから：
  - pip install duckdb openai defusedxml

必要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client が使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（execution 関連）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知（monitoring 等）
- OPENAI_API_KEY: OpenAI 呼び出し（ai.news_nlp / ai.regime_detector）
- DUCKDB_PATH: デフォルトの DuckDB パス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（例: data/monitoring.db）
- KABUSYS_ENV: 開発環境指定（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

.env サポート
- プロジェクトルート（.git または pyproject.toml を探索）にある .env と .env.local を自動で読み込みます（OS 環境変数 > .env.local > .env の優先順）。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須の値がない場合、Settings プロパティ（kabusys.config.settings）が ValueError を投げます。

簡単な .env 例
- .env.example を参考に用意してください。主要項目の例:
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - OPENAI_API_KEY=your_openai_key
  - DUCKDB_PATH=./data/kabusys.duckdb
  - KABUSYS_ENV=development
  - LOG_LEVEL=INFO

使い方（代表的な使用例）
----------------------

パッケージのインポート
- Python REPL / スクリプトから:
  - import duckdb
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
  - from kabusys.data.audit import init_audit_db

ETL（日次パイプライン）を実行する
- 例:
  - conn = duckdb.connect(str(Path("data/kabusys.duckdb")))
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=some_date)  # some_date は datetime.date オブジェクト
  - print(result.to_dict())

ニュース NLP（銘柄センチメント評価）
- 例:
  - from kabusys.ai.news_nlp import score_news
  - count = score_news(conn, target_date=some_date, api_key="YOUR_OPENAI_API_KEY")
  - # ai_scores テーブルへ書き込まれた銘柄数が返る

市場レジーム判定
- 例:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=some_date, api_key="YOUR_OPENAI_API_KEY")
  - # market_regime テーブルに日次のレジームが保存される

監査 DB 初期化
- 例:
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db("data/audit.duckdb")
  - # signal_events / order_requests / executions テーブルが作成される

ニュース RSS 取得（単体ユーティリティ）
- 例:
  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")

注意点 / 運用メモ
- OpenAI への API 呼び出しはリトライやフェイルセーフ（スコア0.0）を持つが、API キーは必須です（関数はキー未設定時に ValueError を投げます）。
- J-Quants API 呼び出しは内部でレート制御を行いますが、ID トークン（JQUANTS_REFRESH_TOKEN）は必須です。
- DuckDB の executemany は空リストを受け付けないバージョンがあるため、空チェックを行ってから実行しています。
- テスト時は内部の _call_openai_api や HTTP 呼び出しを patch してモックする設計です。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py               — 環境変数と設定管理（.env 自動読み込みロジック）
- ai/
  - __init__.py
  - news_nlp.py           — ニュースセンチメント（OpenAI 呼び出し、ai_scores 書き込み）
  - regime_detector.py    — 市場レジーム判定（MA200 + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py     — J-Quants API クライアント・保存ロジック
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - etl.py                — ETL の公開インターフェース（ETLResult 再エクスポート）
  - quality.py            — データ品質チェック
  - stats.py              — 統計ユーティリティ（zscore_normalize 等）
  - news_collector.py     — RSS 収集・前処理
  - calendar_management.py— マーケットカレンダー管理
  - audit.py              — 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py    — Momentum/Value/Volatility 等の計算
  - feature_exploration.py— 将来リターン・IC・統計サマリ
- research/* other helper modules...
- その他（strategy / execution / monitoring 等はパッケージ化の想定）

依存関係（主なもの）
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- 標準ライブラリ（urllib, json, datetime, logging, math, hashlib など）

ライセンス / 貢献
-----------------
- 本 README ではライセンス情報は含まれていません。実際のプロジェクトでは LICENSE を追加してください。
- コントリビュートする場合は issue / PR ルールやコードスタイルを明記してください。

最後に
------
この README はコードベースからの主要機能と使い方を要約したものです。各モジュールの詳細な挙動・パラメータや戻り値についてはソース内の docstring を参照してください。質問や特定機能の使い方（例: ETL の細かいオプション、OpenAI のプロンプト調整、監査スキーマの拡張等）が必要であればお知らせください。