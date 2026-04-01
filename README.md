# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants / kabuステーション / OpenAI 等と連携し、データ取得（ETL）・品質チェック・ニュースNLP・市場レジーム判定・ファクター計算・監査ログ管理などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の研究・運用パイプライン向けに設計されたモジュール群です。主な目的は次の通りです。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への ETL（差分更新・バックフィル対応）
- ニュース RSS 収集と OpenAI を利用したニュースセンチメントスコアリング（銘柄別）
- マクロセンチメントと 200 日移動平均乖離を組み合わせた市場レジーム判定
- ファクター（モメンタム / バリュー / ボラティリティ等）の計算、特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注〜約定までの監査ログ（監査テーブル群・初期化ユーティリティ）
- RSS収集時の SSRF 対策やサイズ制限、記事正規化など堅牢性を重視

設計上の方針として「ルックアヘッドバイアス防止」「DB 側の冪等保存」「API 呼び出し時のリトライ/バックオフ」「外部副作用の限定（研究コードは発注等にアクセスしない）」が守られています。

---

## 主な機能一覧

- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / save_* 関数
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - データ品質チェック: check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - ニュース収集: fetch_rss（SSRF 対策・トラッキング除去等）
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 汎用統計: zscore_normalize
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で算出し ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離 + マクロニュース LLM を合成して market_regime に保存
- research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings: 環境変数・.env 読み込み（.env / .env.local 自動読み込み、必要変数チェック）

---

## セットアップ手順

前提
- Python 3.10 以上
- Git（オプション）
- ネットワークから J-Quants / OpenAI API にアクセスできること

1. リポジトリをクローン（またはプロジェクトをコピー）
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   （requirements.txt が無い場合は主要依存を直接インストールします）
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 実行環境によっては追加パッケージが必要になる場合があります（例: psycopg2 等）。プロジェクト固有の requirements.txt があればそちらを使用してください。

4. 環境変数 / .env を準備
   プロジェクトルートに `.env` または `.env.local` を配置すると自動的に読み込まれます（無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   必須の環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
   任意:
   - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL（DEBUG/INFO/...）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（例）

以下は代表的なユースケースの最小例です。実行は Python スクリプトまたは対話環境から行います。

- DuckDB 接続を作成して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアを計算（OpenAI API キーが環境変数 OPENAI_API_KEY に設定されていること）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定を実行
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化（専用 DB を使用）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルにアクセス可能
```

- RSS を取得して記事一覧を得る（保存はアプリ側で処理）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- score_news / score_regime は OpenAI の API キーが必要です。api_key 引数で直接渡すこともできます（例: score_news(conn, date, api_key="sk-...")）。
- run_daily_etl や ETL の save_* 関数は DuckDB のスキーマ（raw_prices / raw_financials / market_calendar 等）を前提とします。スキーマ定義や初期化処理が必要な場合は別途用意してください（このコードベースは ETL ロジックを提供しますが、初期スキーマ作成ユーティリティは別に用いることが想定されます）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 簡単な API 参照

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.openai 等
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.news_collector
  - fetch_rss, preprocess_text
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.research
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.audit
  - init_audit_schema, init_audit_db

各関数の詳細はモジュールの docstring を参照してください。

---

## ディレクトリ構成

プロジェクトは次のような構成です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  -- 環境変数/.env 管理
  - ai/
    - __init__.py
    - news_nlp.py              -- ニュース NLP スコアリング
    - regime_detector.py       -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント + 保存ロジック
    - pipeline.py              -- ETL パイプライン実装（run_daily_etl 等）
    - etl.py                   -- ETLResult 再エクスポート
    - news_collector.py        -- RSS 取得・前処理
    - calendar_management.py   -- 市場カレンダー管理
    - quality.py               -- データ品質チェック
    - stats.py                 -- zscore_normalize 等ユーティリティ
    - audit.py                 -- 監査スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py       -- モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py   -- 将来リターン/IC/統計サマリー
  - ai, data, research 以外に strategy / execution / monitoring 等のサブパッケージを想定（__all__ に含まれる）

ドキュメントは各モジュールの docstring に設計方針や注意点が記載されています。コード内コメントも詳細です。

---

## 運用上の注意

- OpenAI / J-Quants / 証券 API の利用はそれぞれの利用規約・レート制限を遵守してください。J-Quants のレート制限（120 req/min）は jquants_client で考慮されています。
- 機密情報（API キー等）は .env（もしくは環境変数）で管理してください。`.env` ファイルはバージョン管理に含めないことを推奨します。
- DuckDB のスキーマとテーブル定義は ETL/保存関数が前提とする形になっています。既存 DB と接続する場合は互換性を確認してください。
- ニュース NLP / レジーム判定は LLM を利用するため API 呼び出し料金が発生します。バッチ化・バッチサイズ等の設定を慎重に行ってください。
- テスト環境では自動 .env ロードを無効化する（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）などの工夫を行ってください。

---

必要に応じて README を拡張します。特にセットアップ用の requirements.txt、DB スキーマ定義ファイル、運用スクリプト（systemd unit / cron / airflow 等）のテンプレートが欲しい場合は教えてください。