# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレーサビリティ）など、アルゴリズム取引に必要なコンポーネント群を提供します。

## 主な特徴
- J-Quants API からの差分 ETL（株価日足、財務、JPX カレンダー）
- DuckDB を用いたデータ格納・冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（RSS）と OpenAI による銘柄別センチメントスコア生成（gpt-4o-mini を想定）
- 市場レジーム判定（1321 ETF の MA200 とマクロニュースの LLM センチメントを合成）
- 研究用途ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → executions のトレーサビリティ）
- 自動的な .env 読み込み（プロジェクトルートの .env / .env.local。無効化フラグあり）

---

## 機能一覧（モジュール）
- kabusys.config
  - 環境変数の読み込み・検証（自動 .env ロード、必須キー検査）
- kabusys.data.*
  - jquants_client: J-Quants API クライアント（レートリミット / リトライ / トークン自動リフレッシュ）
  - pipeline: ETL 実行（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news への保存ロジック
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - quality: データ品質チェック（QualityIssue）
  - audit: 監査（監査テーブルの初期化 / init_audit_db）
  - stats: 汎用統計ユーティリティ（Z スコア正規化）
- kabusys.ai.*
  - news_nlp.score_news: ニュースから銘柄ごとの AI スコアを作成・ai_scores へ保存
  - regime_detector.score_regime: 市場レジーム判定（ma200 と LLM センチメントの合成）
- kabusys.research.*
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要要件（主な依存ライブラリ）
- Python 3.10+
- duckdb
- openai (OpenAI SDK)
- defusedxml
- （標準ライブラリの urllib, json, datetime などを使用）

依存は pyproject.toml / setup.py に記載している想定です。開発環境では virtualenv / venv を推奨します。

---

## 環境変数
このパッケージは .env（または .env.local）から自動的に環境変数を読み込みます（プロジェクトルートは .git または pyproject.toml を起点に探索）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（必須／任意）:
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
  - KABU_API_PASSWORD: kabu ステーション API パスワード（発注等で使用）
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
  - OPENAI_API_KEY: OpenAI API キー（ai/news_nlp/regime_detector で使用）
- 任意（デフォルトあり）
  - KABUSYS_ENV: environment（development / paper_trading / live）。デフォルト: development
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- 自動ローディングに読み込まれる .env の記法はシェル風（export も可、クォート/コメントの扱いあり）に対応しています。

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install -e .   # 開発インストール（プロジェクトルートに pyproject.toml / setup.py がある想定）
   - もしくは必要なパッケージ個別に: pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルートに .env を作成し、必要なキーを設定するか、環境に直接設定してください。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678

5. DuckDB ファイル用ディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡単な使用例）

以下は Python REPL やスクリプトから呼ぶ例です。いずれも settings（kabusys.config.settings）により .env の値や既定値を参照できます。

- 共通: DuckDB へ接続
  from datetime import date
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（run_daily_etl）
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn, target_date=date(2026,3,20))
  print(res.to_dict())

- ニューススコアを生成（score_news）
  from kabusys.ai.news_nlp import score_news
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {n_written} codes")

- 市場レジーム判定（score_regime）
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))

- 監査 DB を初期化（監査専用 DB）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_db は TimeZone を UTC に設定してスキーマを作成します

- ファクター計算（研究用途）
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))

- カレンダー更新ジョブの実行
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved {saved} calendar rows")

注意点:
- OpenAI 呼び出しを行う関数（score_news, score_regime 等）は OPENAI_API_KEY を必要とします。api_key 引数で直接渡すことも可能です。
- ETL / API 呼び出し系は外部ネットワークや API レート制限に依存します。実行環境でのネットワーク接続と API 利用制限にご注意ください。
- 本ライブラリはルックアヘッドバイアスを避ける設計方針を採っています。内部で date.today() や datetime.today() を直接参照しない関数設計になっています（target_date を明示的に渡すことが推奨されます）。

---

## 設定（.env）読み込みの挙動
- 自動ロード順序: OS 環境 > .env.local > .env
- テストなどで自動 .env 読み込みを無効化したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主なファイル）
- src/kabusys/
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

（README に含まれるのは主要ファイルの抜粋です。実際のリポジトリ内にさらにサブモジュールやユーティリティが存在する可能性があります。）

---

## 運用上の注意点 / ベストプラクティス
- 本システムは本番発注（live）とペーパートレード（paper_trading）を区別できる設定（KABUSYS_ENV）を持っています。発注・実行系は運用時に十分な検証を行ってください。
- OpenAI API 呼び出しはレイテンシ・コストが発生します。バッチサイズやリトライ設定はモジュール内定数で調整できます。
- J-Quants API トークンは機密情報です。 .env ファイルの取り扱いに注意し、リポジトリに公開しないでください。
- DuckDB ファイルは定期的なバックアップを推奨します（監査ログなど永続的データが保存されます）。

---

何か追加で README に含めたいチュートリアル例や、CI / デプロイ用のガイド（systemd / cron での ETL スケジューリングや Dockerfile 例など）があれば教えてください。それに合わせた追記を作成します。