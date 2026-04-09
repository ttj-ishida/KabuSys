# KabuSys

日本株向けのデータプラットフォーム兼自動売買ライブラリ（簡易版）。  
DuckDB をデータ保存に使い、J-Quants / RSS / OpenAI を組み合わせてデータ収集・品質チェック・ニュースNLP・市場レジーム判定・研究用ファクター計算・監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の用途を想定した内部ライブラリ / ツール群です。

- J-Quants API から株価 / 財務 / 市場カレンダーを差分取得して DuckDB に保存する ETL
- RSS ベースのニュース収集と前処理 -> raw_news テーブル保存
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_scores, 市場マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの組合せ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- リサーチ用のファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 発注・約定に関する監査ログスキーマの初期化・管理

設計上の特徴:
- Look-ahead バイアス防止を重視（target_date ベース、datetime.today() を直接参照しない設計が多い）
- DuckDB を中心に SQL＋Python で処理（外部依存を最小化）
- API 呼び出しはリトライ・レート制御などの安全策を実装
- ETL と品質チェックは個別にエラーハンドリングして継続可能

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - news_collector（RSS 取得・前処理）
  - calendar_management（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - quality（データ品質チェック）
  - audit（監査ログスキーマ初期化 / init_audit_db）
  - stats（zscore_normalize 等）
- ai
  - news_nlp.score_news（銘柄ごとのニュースセンチメント算出・ai_scores 書き込み）
  - regime_detector.score_regime（マクロ + MA200 で市場レジーム判定）
- research
  - factor_research（calc_momentum / calc_value / calc_volatility）
  - feature_exploration（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数読み込みと Settings オブジェクト（settings）による一元管理
  - .env / .env.local 自動ロード（プロジェクトルート検出）※無効化可能

---

## 前提・必要環境

- Python 3.10+（型ヒントに union types を使用）
- 推奨パッケージ（主にライブラリで参照されているもの）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API / OpenAI / RSS）
- J-Quants のリフレッシュトークン、（必要に応じて）OpenAI API キー 等の環境変数

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれを使用してください）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env を置くか、OS 環境変数を設定します。
   - 自動ロードは kabusys.config がプロジェクトルート（.git または pyproject.toml）を検出して .env / .env.local を読み込みます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の主な環境変数（Settings 参照）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_FILL_MODE — paper_trading 時の挙動（instant/partial/never/reject）
- その他（LINE 等は任意）:
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

ヒント:
- .env 形式はシェルの export KEY=val 形式 / quoted values / inline コメント等に対応しています。
- .env.example を作成して管理すると初期設定が楽です。

---

## 使い方（主要な例）

以下は各主要機能を呼び出す際の最小例です。適切な DB 接続（duckdb.connect）と環境変数設定が前提です。

- DuckDB 接続を作る
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- ETL（日次パイプライン）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- 単体 ETL（株価のみ）
  - from kabusys.data.pipeline import run_prices_etl
  - fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))

- ニュースセンチメント（銘柄別）
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
  - n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")  # api_key を引数でも渡せる

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査ログ DB 初期化（監査用 DuckDB を新規に作る）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/monitoring_audit.duckdb")

- ニュース RSS 取得（単体）
  - from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  - articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")

- 研究用ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    from datetime import date
  - mom = calc_momentum(conn, target_date=date(2026, 3, 20))

- 設定参照
  - from kabusys.config import settings
  - print(settings.duckdb_path, settings.env)

エラーハンドリングやトランザクションはモジュール側で多く対処されていますが、上位でのログ記録や再試行戦略は利用ケースに応じて実装してください。

---

## よく使う注意点 / 運用メモ

- OpenAI を使う処理（news_nlp / regime_detector）は API の呼び出し回数・レスポンス形式に依存します。テスト時は内部の _call_openai_api をモックできます。
- J-Quants API はレート制限があるため、jquants_client はモジュール内で固定間隔スロットリングを行います。
- run_daily_etl はカレンダー取得→株価→財務→品質チェックの順で実行します。品質チェックで error が出ても ETL 自体は部分的に継続します（結果オブジェクトで検査できます）。
- DuckDB の executemany に空配列を渡すと問題になるバージョンがあるため、内部で空チェックがあります。
- news_collector は SSRF 対策、XML 安全パーサ（defusedxml）等の安全策を実装しています。RSS ソースは信頼できるもののみ登録してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

主要ファイルの役割:
- config.py: 環境変数読み取りと Settings オブジェクト
- data/jquants_client.py: J-Quants API の取得・保存ロジック
- data/pipeline.py: ETL のオーケストレーション
- data/news_collector.py: RSS 収集と前処理
- ai/news_nlp.py: 銘柄別ニューススコアリング（OpenAI）
- ai/regime_detector.py: 市場レジーム判定（MA200 + マクロニュース）
- research/*: ファクター計算と探索用ユーティリティ
- data/audit.py: 監査ログ用スキーマ・初期化ユーティリティ

---

## 開発・テストメモ

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。テストで環境を壊したくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自前で環境変数を渡してください。
- OpenAI 呼び出しや外部 HTTP はユニットテストでモックすることを想定しています（モジュール内で _call_openai_api や _urlopen などを差し替え可能）。
- DuckDB を使う処理はインメモリ ":memory:" でテスト可能です（init_audit_db などは ":memory:" を受け付けます）。

---

必要であれば、README にサンプル .env.example、起動スクリプト、systemd / Docker 運用例、または各モジュールの詳細な API リファレンス（引数と戻り値の表）を追加します。どの情報を優先して追加しますか？