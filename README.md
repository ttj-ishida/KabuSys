# KabuSys

日本株向けの自動売買 / データプラットフォーム用ユーティリティ群です。  
データ取得（J-Quants）、ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（オーダー／約定）など、バックテストや運用に必要な共通機能を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）・財務データ・上場銘柄情報・マーケットカレンダーを取得
  - 差分取得、バックフィル、冪等保存（DuckDB へ ON CONFLICT で保存）
  - 日次 ETL パイプライン（カレンダー → 株価 → 財務 → 品質チェック）

- データ品質チェック
  - 欠損（OHLC）・スパイク（前日比閾値）・重複・日付不整合（未来日付／非営業日）を検出

- ニュース収集・NLP（OpenAI）
  - RSS ベースのニュース収集（SSRF / トラッキング除去 / XML セキュリティ対策）
  - ニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）に JSON モードで投げ、銘柄毎の ai_score を生成
  - マクロニュースから市場センチメントを判定し、市場レジーム（bull/neutral/bear）を算出

- リサーチ／ファクター
  - モメンタム / ボラティリティ / バリュー系ファクター算出（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（スピアマン）・統計サマリー、Zスコア正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル等の DDL を提供
  - 監査用 DuckDB 初期化ユーティリティ（UTC タイムスタンプ / 冪等）

- 設定管理
  - .env / .env.local / OS 環境変数から自動読み込み（プロジェクトルートを基準）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能

---

## 必要環境

- Python 3.10+
- 主な Python 依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

※ 実際のセットアップでの requirements.txt / pyproject.toml を参照してください。

---

## セットアップ手順

1. リポジトリをチェックアウト / クローン

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （開発: pip install -e . を使える構成であれば pip install -e .）

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env`（と必要なら `.env.local`）を作成します。主なキーは下記参照。

5. DuckDB / 監査 DB の初期化（任意）
   - 監査用 DB を作る例（Python REPL）:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

6. （運用）ETL を定期実行したり、score_news/score_regime をスケジューラで呼び出します。

---

## 環境変数（主な一覧）

README 内のキー名はソースから抽出した主要なものです。`.env.example` をプロジェクトに用意している想定です。必須項目と任意項目があります。

必須（実際に使用する機能による）
- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン（ETL）
- OPENAI_API_KEY - OpenAI API キー（ニュース NLP / レジーム判定）
- KABU_API_PASSWORD - kabuステーション API パスワード（発注機能がある場合）

任意 / デフォルトあり
- KABUSYS_ENV - development / paper_trading / live（デフォルト: development）
- LOG_LEVEL - DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID - 通知用
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - 監視DB（data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH - 実行監視用のファイルパス
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT - 監視閾値

その他
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとパッケージ起動時の .env 自動読み込みを無効化できます（テスト時に便利）。

---

## 使い方（代表的な例）

以下はライブラリ関数を直接呼ぶ簡易例です。詳細はソースの docstring を参照してください。

- DuckDB 接続を作る（設定で指定したパスを利用）
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュース NLP スコアを生成（target_date に対して前日 15:00 JST 〜 当日 08:30 JST の範囲）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, date(2026, 3, 20), api_key="sk-...")  # api_key を渡すか OPENAI_API_KEY を設定

- 市場レジーム判定を実行
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, date(2026, 3, 20), api_key="sk-...")

- 監査 DB の初期化（監査用テーブルを作成）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- RSS を個別に取得してニュースを前処理する（内部はニュースコレクタを使用）
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")

- J-Quants API を直接呼ぶ（必要に応じて）
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()
  records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,20))

---

## 主要 API / エントリポイント（抜粋）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_*（DuckDB への保存ユーティリティ）
  - get_id_token

- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency

- kabusys.data.news_collector
  - fetch_rss, preprocess_text

- kabusys.ai.news_nlp
  - score_news

- kabusys.ai.regime_detector
  - score_regime

- kabusys.data.audit
  - init_audit_schema, init_audit_db

- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

---

## ディレクトリ構成

以下は主要ファイルの一覧と簡単な説明（リポジトリの src/kabusys 配下に配置される想定）。

- src/kabusys/
  - __init__.py                - パッケージ初期化（公開モジュール定義）
  - config.py                  - 環境変数 / 設定読み込みロジック（.env 自動ロード等）
  - ai/
    - __init__.py
    - news_nlp.py              - ニュースの NLP スコアリング（OpenAI 呼び出し、ai_scores 書き込み）
    - regime_detector.py       - マクロ + ETF ma200 で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py        - J-Quants API クライアント（取得 / 保存 / 認証）
    - pipeline.py              - ETL パイプライン（run_daily_etl 等）
    - etl.py                   - ETL の公開型 (ETLResult) の再エクスポート
    - news_collector.py        - RSS 収集・前処理・保存ロジック
    - calendar_management.py   - マーケットカレンダー管理（営業日判定等）
    - quality.py               - データ品質チェック
    - stats.py                 - 統計ユーティリティ（Zスコア正規化）
    - audit.py                 - 監査ログ用 DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py       - ファクター計算（Momentum/Value/Volatility 等）
    - feature_exploration.py   - 将来リターン / IC / 統計サマリー 等
  - ai/、research/、data/ 以下に更に細かい実装と docstring が多数含まれます。

---

## 注意事項 / 設計上のポイント

- Look-ahead bias 対策:
  - 日付判定やデータ取得は target_date を明示して行い、datetime.today()/date.today() を直接参照しない設計箇所が多くあります（再現性確保のため）。
- フェイルセーフ:
  - 外部 API（OpenAI, J-Quants）失敗時はログを残して可能な範囲でフォールバック（0スコア等）して継続する箇所があるため、呼び出し側でのエラーハンドリング方針に注意してください。
- 冪等性:
  - DuckDB への保存は基本的に ON CONFLICT DO UPDATE または INSERT ... ON CONFLICT による冪等設計です。
- セキュリティ:
  - news_collector は SSRF 対策、XML パーサは defusedxml を使用、RSS の最大受信サイズ制限やトラッキング除去を実装しています。

---

## サポート / 貢献

本 README はコードベースの抜粋に基づくサマリです。実運用や拡張の際は、各モジュールの docstring とテストを参照してください。バグ報告や機能要望は issue を通じてお願いします。

--- 

（必要であれば README にサンプル .env.example や CI / テスト実行手順、より詳細な API 使用例を追記します。どの情報が必要か教えてください。）