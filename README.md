# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
J-Quants API からのデータ取得（株価・財務・市場カレンダー）、ニュース収集・NLP による銘柄センチメント評価、研究用ファクター計算、監査ログ（発注→約定トレーサビリティ）、ETL パイプラインなどを含むモジュール群を提供します。

概要や設計方針はソース中の docstring に詳述されています。主に DuckDB を内部データベースとして利用し、OpenAI（gpt-4o-mini）を用いた NLP 処理や J-Quants API を使ったデータ取得を組み合わせたスタックです。

---

## 主な機能一覧

- 環境変数 / 設定管理
  - .env / .env.local を自動で読み込み（プロジェクトルート検出、自動ロードは無効化可）
- データETL（J-Quants）
  - 日次株価（OHLCV）の差分取得・保存（ページネーション対応、冪等保存）
  - 財務データの差分取得・保存
  - JPX マーケットカレンダー取得・保存
  - ETL の実行結果を ETLResult で集約
- データ品質チェック
  - 欠損、スパイク（急騰/急落）、重複、日付不整合などの検出
- ニュース収集
  - RSS 取得（SSRF 対策、gzip 対応、トラッキングパラメータ除去）、raw_news 保存用ユーティリティ
- AI/NLP
  - ニュースの銘柄別センチメント（score_news）
  - マクロ記事 + ETF (1321) MA200 乖離を合成して市場レジーム判定（score_regime）
  - OpenAI 呼び出しにリトライ・パース安全対策を実装
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ
  - Zスコア正規化ユーティリティ
- 監査ログ（audit）
  - signal → order_request → execution までの監査テーブル定義・初期化
  - DuckDB 上に冪等にスキーマを作成するユーティリティ（init_audit_schema / init_audit_db）

---

## 必要環境（参考）

- Python 3.10+
  - 型注釈で `X | Y` 形式を使用しているため 3.10 以降を推奨
- 主な Python パッケージ（プロジェクトに合わせて適宜追加）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API、RSS フィード、OpenAI API へアクセス可能であること

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってインストールしてください）

---

## セットアップ手順（例）

1. リポジトリをクローン／チェックアウト
   - 例: git clone ...

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそれを利用）

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` と `.env.local` が自動読み込みされます（OS 環境変数が優先）。
   - 必須の環境変数（少なくとも以下）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API 用パスワード（本リポジトリ内で利用箇所がある場合）
     - SLACK_BOT_TOKEN — Slack 通知に使う場合
     - SLACK_CHANNEL_ID — Slack チャネル ID
     - OPENAI_API_KEY — OpenAI を使う処理（score_news/score_regime 等）を実行する場合
   - 任意 / 設定値:
     - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH （デフォルト: data/monitoring.db）
     - KABUSYS_ENV （development / paper_trading / live）
     - LOG_LEVEL
   - 自動 .env ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース初期化（監査DB 例）
   - Python で実行:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
     - （init_audit_db はパスの親ディレクトリを自動作成します）

---

## 使い方（主要な API とサンプル）

- ETL（日次 ETL 実行）
  - 例:
    - from datetime import date
      from duckdb import connect
      from kabusys.config import settings
      from kabusys.data.pipeline import run_daily_etl
      conn = connect(str(settings.duckdb_path))
      result = run_daily_etl(conn, target_date=date.today())
      print(result.to_dict())
  - run_daily_etl はカレンダー → 株価 → 財務 → 品質チェック の順に差分ETLを実行し、ETLResult を返します。

- ニュースセンチメント（銘柄単位、日次）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込んだ銘柄数

  - OpenAI API キーは引数 api_key に渡すか環境変数 OPENAI_API_KEY を設定します。

- 市場レジーム判定（マクロセンチメント + ETF MA200）
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 03, 20))

- 研究用ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    momentum = calc_momentum(conn, target_date=date(2026,3,20))
  - 返り値は (date, code) をキーとする dict のリストです。zscore_normalize は kabusys.data.stats にあります。

- 監査スキーマ初期化（既存接続に対して）
  - from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)

- J-Quants クライアント（直接利用）
  - from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - get_id_token() を内部で管理。リトライ・レート制御を実装済み。

- ニュース収集（RSS）
  - from kabusys.data.news_collector import fetch_rss, preprocess_text
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
    for a in articles:
        text = preprocess_text(a["title"] + " " + a["content"])
    - fetch_rss は SSRF 対策・サイズ制限・gzip 対応等をしています。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと役割のまとめです。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数ロード・Settings クラス（J-Quants, kabu API, Slack, DB パス, 環境設定 等）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄ごとに集約して OpenAI でセンチメントを算出し ai_scores テーブルへ書き込む
    - regime_detector.py
      - ETF 1321 の MA200 乖離とマクロニュースセンチメントから市場レジームを判定し market_regime テーブルへ書き込む
  - data/
    - __init__.py
    - calendar_management.py
      - market_calendar の管理・営業日判定・カレンダー更新ジョブ
    - pipeline.py
      - ETL の実行ロジック（run_daily_etl 等）、ETLResult
    - etl.py
      - ETLResult のエクスポート
    - jquants_client.py
      - J-Quants API の HTTP ラッパー、取得関数（fetch_*）、保存関数（save_*）
    - news_collector.py
      - RSS フィード取得・前処理・ID生成ユーティリティ（SSRF対策等）
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC, ランク関数、統計サマリ

---

## 運用上の注意 / 実装上の考慮

- Look-ahead bias を防ぐ設計が随所に取り入れられています（target_date 未満のデータのみ利用、datetime.today の直接参照回避等）。
- OpenAI 呼び出しや J-Quants API 呼び出しはリトライ・バックオフ・エラーハンドリングを実装しており、API 失敗時はフェイルセーフとしてスコアを 0 にフォールバックする等の対策がなされています。
- DuckDB に対する executemany の空リストバインド制約や、保存時の冪等性（ON CONFLICT）に注意して実装されています。
- ニュース収集は SSRF 対策（リダイレクト検査、プライベート IP へのアクセス遮断）や XML 安全パーサ（defusedxml）を利用しています。
- 自動 .env ロードはプロジェクトルートを .git または pyproject.toml から検出します。テスト時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## よく使う例（まとめ）

- ETL を一回実行する:
  - from duckdb import connect
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl
    conn = connect(str(settings.duckdb_path))
    run_daily_etl(conn)

- ニューススコアを作る:
  - from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date=date(2026,3,20), api_key="sk-...")

- レジームスコアを作る:
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査DBを初期化:
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")

---

この README はソースの docstring を元に要点をまとめたものです。実際の運用やデプロイでは、API トークンの管理、ネットワーク制限、バックテスト用データの事前準備（Look-ahead 対応）などを適切に行ってください。README の補足・整備や具体的な運用手順（systemd / cron / Airflow 等でのスケジューリング、監視、アラート）についてはプロジェクトのデプロイ方針に合わせて追記してください。