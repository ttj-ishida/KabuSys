# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、データ品質チェック、ニュース収集・NLP、AIによるスコアリング、ファクター計算、監査ログなど、バックテスト／ライブ運用に必要なユーティリティを提供します。

---

## プロジェクト概要

KabuSys は以下の機能群を含む Python パッケージです。

- J-Quants API を用いた株価・財務・カレンダーの差分ETL（ページネーション・レート制御・トークン自動リフレッシュ対応）
- DuckDB を利用したデータ保存／冪等保存ロジック（ON CONFLICT DO UPDATE）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集（RSS）と前処理（SSRF対策、トラッキングパラメータ除去、最大読み取りサイズ制限など）
- OpenAI（gpt-4o-mini）を利用したニュースのセンチメント解析（銘柄別 ai_score）と市場レジーム判定
- 監査ログ（signal → order_request → execution をトレースする監査スキーマ）初期化ユーティリティ
- 研究用モジュール（ファクター計算、特徴量探索、統計ユーティリティ）

設計方針の例:
- ルックアヘッドバイアスを避けるため、内部で date.today()／datetime.today() を無制限に参照しない。
- API 呼び出しはリトライ・バックオフ・フェイルセーフを備える。
- DuckDB に対してはできる限り冪等的にデータを書き込む。

---

## 主な機能一覧

- data.jquants_client
  - fetch/save: daily_quotes, financial_statements, market_calendar, listed_info
  - レートリミット・リトライ・トークン自動更新対応
- data.pipeline
  - run_daily_etl: カレンダー・株価・財務の差分取得と品質チェックを一括実行
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別実行可）
  - ETL 結果を ETLResult オブジェクトで返却
- data.quality
  - 欠損、スパイク、重複、日付不整合チェック（QualityIssue を返す）
- data.news_collector
  - RSS 取得（SSRF対策、gzip対応、トラッキング除去、ID生成）
- ai.news_nlp
  - score_news: 指定ウィンドウのニュースを銘柄ごとに集約し OpenAI でスコア化して ai_scores に保存
- ai.regime_detector
  - score_regime: ETF(1321) の MA200 乖離 + マクロニュース LLM スコアで市場レジーム（bull/neutral/bear）を判定し market_regime に保存
- data.audit
  - init_audit_schema / init_audit_db: 監査テーブル群（signal_events, order_requests, executions）を冪等初期化
- research.*
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / zscore_normalize 等

---

## 動作要件（推奨）

- Python 3.10+
  - コード中で PEP 604 の | 型記法や型ヒントを使用しているため 3.10 以上を推奨します
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の依存は実行する機能に応じて必要になります）

requirements.txt はこのリポジトリに含まれていない可能性があるため、上記パッケージを適宜インストールしてください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... （リポジトリURL）

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. インストール
   - pip install -e .  （ローカル開発インストール）
   - 必要に応じて追加パッケージをインストール:
     - pip install duckdb openai defusedxml

4. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動的に読み込まれます（os 環境変数が優先）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知を使う場合）
     - OPENAI_API_KEY: OpenAI API キー（score_news/score_regime 呼び出し時に None の場合環境変数から取得）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 SQLite、デフォルト: data/monitoring.db）

   例 `.env`（プロジェクトルートに配置）:
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

## 使い方 — 主要な例

ここでは DuckDB 接続を利用した主要ワークフローの例を示します。target_date はテストやバッチ実行で明示的に渡すことを推奨します（ルックアヘッドバイアス対策）。

- DuckDB 接続の作成（環境設定のデフォルトパスを使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次ETL の実行（カレンダー -> 株価 -> 財務 -> 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメント（銘柄別）のスコア化
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を直接渡すか、環境変数 OPENAI_API_KEY を設定する
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査用 DuckDB データベース初期化
```python
from kabusys.data.audit import init_audit_db

# ファイルパスを指定して監査DBを初期化（ディレクトリを自動作成）
audit_conn = init_audit_db("data/audit.duckdb")
audit_conn.close()
```

- 研究（ファクター計算）の例
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))

# Zスコア正規化（クロスセクション）
normed = zscore_normalize(momentum, columns=["mom_1m", "mom_3m", "mom_6m"])
```

- RSS を取得する（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```
（fetch_rss はネットワークエラーや XML パースエラーを適切に扱います。実際の保存は raw_news テーブルへ行うロジックを別途呼び出す想定です。）

---

## 実運用上の注意

- OpenAI 呼び出しはコストと API レートに注意して運用してください（gpt-4o-mini を使用）。
- J-Quants はレート制限（120 req/min）を遵守するため実装側でスロットリングしていますが、過度の同時実行は避けてください。
- 本ライブラリはルックアヘッドバイアス対策を念頭に設計されています。ETL / スコア生成関数は target_date を外部から明示して呼ぶことを推奨します。
- DB 書き込みは可能な限り冪等性を保つよう設計されていますが、運用中のスキーマ変更や外部からの直接書き込みに注意してください。
- 自動 .env 読み込みはプロジェクトルートを基準に行われます。テストや CI から環境を切り替えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。

---

## ディレクトリ構成（抜粋）

以下は主要なモジュール・ファイルの構成（提供コードに基づく抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - stats.py
    - quality.py
    - calendar_management.py
    - news_collector.py
    - audit.py
    - (その他: schema 初期化など)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research や monitoring / execution / strategy などのパッケージは将来的な拡張領域として想定されます（README 内の __all__ に基づく公開APIの整理）。

---

## 参考・補足

- config.Settings により環境変数から各種設定を参照できます（settings.jquants_refresh_token, settings.duckdb_path 等）。
- .env のパースはコメントやクォートを考慮した実装になっており、.env.local は .env を上書きします（OS 環境変数は保護されます）。
- テスト時には各種内部関数（例: OpenAI の呼び出し部分）をモックして差し替えられるよう設計されています。

---

もし README に含めたい追加の使用例（たとえば CI のワークフロー、Dockerfile、監視/アラート設定、より詳細なスキーマ定義やサンプル .env.example）などがあれば知らせてください。必要に応じて追記します。