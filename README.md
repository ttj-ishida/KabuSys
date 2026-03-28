# KabuSys

日本株のデータプラットフォームと自動売買（研究・監査・ETL・AI支援）を想定した Python パッケージ群です。ETL、データ品質チェック、ニュース収集・NLP（LLM）評価、リサーチ用ファクター計算、監査ログ（発注/約定トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような用途を想定した内部ライブラリ群です。

- J-Quants API から株価・財務・カレンダー等のデータを差分取得して DuckDB に保存する ETL パイプライン
- raw_news の RSS 収集・前処理・銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント評価（銘柄別 ai_score やマクロセンチメント）
- 研究向けのファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ（Zスコア、IC 等）
- 監査ログ用スキーマ（signal / order_request / executions）と初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上のポイント:
- ルックアヘッドバイアスを避けるため、内部で datetime.today() を不用意に参照しない
- DuckDB を主要なデータ永続化先とする（分析・ETL用）
- 冪等性（ON CONFLICT）・リトライ・フェイルセーフを考慮

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード（無効化可能）
  - 必須環境変数の明示的取得

- データ関連（kabusys.data）
  - jquants_client: J-Quants API 呼び出し、保存関数（raw_prices / raw_financials / market_calendar 等）
  - pipeline: 日次 ETL（run_daily_etl）と個別 ETL ジョブ（run_prices_etl 等）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - news_collector: RSS 収集、前処理、SSRF 対策
  - quality: データ品質チェック一括実行
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）

- AI / NLP（kabusys.ai）
  - news_nlp.score_news: 銘柄別ニュースセンチメントを取得して ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースを合成して市場レジーム判定

- 研究（kabusys.research）
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize

---

## 前提（Prerequisites）

- Python 3.10+
- 必要パッケージ（主なもの）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - その他標準ライブラリ（urllib, datetime, json 等）

例:
pip install duckdb openai defusedxml

※ 実運用では requirements.txt / pyproject.toml に依存関係を明記してください。

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（編集可能な開発モード推奨）
   - pip install -e . あるいは pip install ./path/to/project

2. 環境変数の設定
   - ルートに `.env` を置くと自動で読み込まれます（.env.local は .env を上書き）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   重要な環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI の API キー（score_news / score_regime 用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注などを将来追加する場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知関連
   - DUCKDB_PATH: デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

   .env の例（.env.example をプロジェクトルートに置くことを推奨）:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C...
   DUCKDB_PATH=data/kabusys.duckdb

3. DuckDB 初期化（監査テーブルを作る例）
   Python REPL / スクリプトで:
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db(settings.duckdb_path)  # :memory: も可
   # これで監査用テーブルが作成されます

---

## 使い方（例と簡単なガイド）

以下は代表的な利用例です。すべて Python スクリプト内で実行します。

- ETL を日次で実行する（例: run_daily_etl）
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュースのセンチメントをスコアリングして ai_scores に保存する
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数で参照
  print(f"書き込んだ銘柄数: {written}")

- 市場レジームを判定して market_regime に保存する
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- 研究用ファクター計算（例: モメンタム）
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(records[:5])

- データ品質チェックを一括実行
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)

注意点:
- OpenAI 呼び出しを行う関数は api_key を引数で上書き可能（デフォルトでは OPENAI_API_KEY を使用）。
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml を基準）から探します。CIなどで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## よく使う API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.is_live など

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token (トークン取得)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成

（主要ファイルのみ抜粋、プロジェクトルートに README.md / pyproject.toml 等を想定）

src/kabusys/
- __init__.py
- config.py                      # 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                   # ニュースセンチメント（銘柄別 ai_scores 書込）
  - regime_detector.py            # 市場レジーム判定（MA + マクロ）
- data/
  - __init__.py
  - jquants_client.py             # J-Quants API クライアント + 保存関数
  - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
  - calendar_management.py        # マーケットカレンダー管理
  - news_collector.py             # RSS 収集・前処理
  - quality.py                    # データ品質チェック
  - audit.py                      # 監査ログスキーマ初期化 / init_audit_db
  - etl.py                        # ETLResult 再エクスポート
  - stats.py                      # 統計ユーティリティ（zscore_normalize 等）
- research/
  - __init__.py
  - factor_research.py            # calc_momentum / calc_value / calc_volatility
  - feature_exploration.py        # calc_forward_returns / calc_ic / factor_summary / rank

テストや CLI スクリプトは本リポジトリの別ディレクトリに追加することを想定しています。

---

## 運用上の注意 / ベストプラクティス

- 環境変数（API キー等）は安全に管理し、リポジトリにコミットしないでください。
- OpenAI や J-Quants の API 呼び出しはレート制限やコストが発生します。ローカルでの開発時はモックを使うか小さめの対象で実行してください。
- DuckDB のファイルは定期バックアップを検討してください（分析用に大きくなる可能性あり）。
- run_daily_etl は複数ステップから構成され、個別に失敗しても他ステップは継続します。ログ・結果（ETLResult）を監視してください。
- audit スキーマは監査目的のため削除しない運用を想定しています。

---

この README はコードベースの概要および典型的な使用法をまとめたものです。詳細や運用ルール（CI / デプロイ方法、テーブルスキーマの完全仕様など）は別ドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。