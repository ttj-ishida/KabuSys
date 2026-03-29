# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）など、トレーディングプラットフォームのコア機能を提供します。

---

## 主な機能

- データ取得・ETL
  - J-Quants API を用いた株価（日足）、財務データ、JPX カレンダーの差分取得・保存（ページネーション対応・冪等保存・レートリミット＆リトライ）
  - 日次 ETL パイプライン（差分取得／バックフィル／品質チェック）
- ニュース収集
  - RSS から記事を安全に取得（SSRF 対策、サイズ上限、トラッキングパラメータ除去）
- ニュース NLP（OpenAI）
  - 記事を銘柄単位で集約して LLM によりセンチメントスコアを算出・ai_scores テーブルへ保存
- 市場レジーム判定（AI + テクニカル）
  - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して 'bull' / 'neutral' / 'bear' を判定
- リサーチ用ユーティリティ
  - モメンタム／バリュー／ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）評価、統計サマリー
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合等の検出
- 監査ログ（Audit）
  - シグナル→発注→約定までのトレーサビリティを保証する監査テーブルの作成・初期化ユーティリティ

---

## 前提・依存関係

- Python 3.10+
- 主な依存パッケージ（プロジェクトの requirements.txt があればそちらを参照してください）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリの urllib, json, logging, datetime 等を多用）

例（手動インストール）:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリを取得して仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate (Windows では .venv\Scripts\activate)

2. 依存関係をインストール
   - pip install -r requirements.txt
   - または個別に: pip install duckdb openai defusedxml

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` ファイルを置くと自動で読み込まれます。
   - 読み込み順: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須（コード内で _require() によって要求される）例:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必要な場合）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必要な場合）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必要な場合）
   - OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で使用）

   任意:
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

4. DuckDB ファイルの準備
   - データベースファイルは自動作成されます。ETL 等を実行する前に、必要なテーブル定義（スキーマ初期化）を行ってください。
   - 監査ログ専用 DB を初期化するには:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（代表的な API・例）

（以下は Python REPL / スクリプトでの利用例）

- 設定値の取得
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)

- DuckDB 接続を作成
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（OpenAI API 必須）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # conn は duckdb 接続
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を None にすると環境変数 OPENAI_API_KEY を使用
  print(f"scored {count} codes")

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- ニュース RSS 取得（保存処理は別途行ってください）
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])

- 監査ログスキーマを初期化（同一 DuckDB 接続に適用）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- リサーチ系ユーティリティ
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

---

## 注意事項 / 実運用上の設計ポリシー

- Look-ahead bias を避けるため、各モジュールは date.today() / datetime.today() を内部ロジックで直接参照せず、呼び出し側から target_date を渡す設計です。バッチ処理では必ず対象日を明示してください。
- OpenAI / J-Quants の呼び出しはリトライやバックオフ・フェイルセーフが組み込まれていますが、API キーやレート制限に注意してください。
- .env 自動読み込みはプロジェクトルートを探索して行われます。テストで自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB の executemany に空の params を渡すとエラーになるバージョンがあるため、実装では空チェックを行ってから executemany を実行しています。

---

## ディレクトリ構成（主要ファイル・モジュール説明）

src/kabusys/
- __init__.py
  - パッケージのメタ情報（__version__ 等）
- config.py
  - 環境変数 / 設定管理（.env 自動ロード、Settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py
    - ニュースを銘柄ごとに集約して OpenAI でセンチメントを評価、ai_scores に書き込む
  - regime_detector.py
    - ETF(1321) の MA 乖離 + マクロニュース LLM を合成して市場レジームを判定し market_regime に書込む
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・保存ロジック・レートリミット・リトライ）
  - pipeline.py
    - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - ETLResult の定義
  - etl.py
    - ETLResult の再エクスポート
  - news_collector.py
    - RSS 収集、URL 正規化、SSRF 対策、記事前処理
  - calendar_management.py
    - market_calendar 管理、営業日判定・前後営業日取得、calendar_update_job
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - quality.py
    - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit.py
    - 監査ログテーブル定義・初期化（signal_events / order_requests / executions）
- research/
  - __init__.py
  - factor_research.py
    - Momentum / Value / Volatility / Liquidity 等のファクター計算
  - feature_exploration.py
    - 将来リターン計算、IC、統計サマリー、ランク変換
- research.__all__ による公開関数定義が含まれます

（上記は主要モジュールの要約です。実装ファイル内に詳細なドキュメントと設計方針コメントが含まれています。）

---

## よくある質問

Q. .env の読み込み順は？  
A. OS 環境変数 > .env.local（存在すれば） > .env の順で読み込みます。既に OS にあるキーは上書きされません。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定します。

Q. OpenAI の呼び出しに失敗したらどうなる？  
A. ニュース NLP / レジーム判定ともにリトライ・バックオフを行い、最終的に失敗した場合はフェイルセーフの既定値（例: macro_sentiment=0.0）で継続する設計です。致命的な例外は上位に伝播しますが、可能な限り部分失敗で全体処理が止まらないようになっています。

Q. DuckDB のスキーマはどこで定義される？  
A. コード内の各モジュール（audit.init_audit_schema や ETL の保存先テーブル等）で使用するテーブル DDL が定義されています。運用時は必要なスキーマを事前に初期化してください（監査ログや raw_ テーブルなど）。

---

必要に応じて README をプロジェクトの実ファイル構成や CI / デプロイ手順に合わせて調整できます。追加で「実行スクリプト例」「SQL スキーマダンプ」「docker-compose 例」などが必要であれば教えてください。