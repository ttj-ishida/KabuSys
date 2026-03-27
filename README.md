# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース NLP（OpenAI を用いたセンチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなど、アルゴリズムトレーディングに必要な基盤機能群を提供します。

---

## 特徴（概要）

- J-Quants API からの差分取得（株価、財務、マーケットカレンダー）
- DuckDB を用いたローカルデータストア（冪等保存）
- ニュース記事の収集・前処理・LLM を用いた銘柄センチメントスコアリング（gpt-4o-mini）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ用スキーマ初期化）
- .env ファイル / 環境変数による設定管理（自動ロード機能あり）

---

## 機能一覧（主要 API）

- ETL / データ取得
  - run_daily_etl(conn, target_date=...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - jquants_client.save_* 系で DuckDB に冪等保存
- ニュース NLP（OpenAI）
  - score_news(conn, target_date, api_key=None)
  - calc_news_window(target_date)
- 市場レジーム判定
  - score_regime(conn, target_date, api_key=None)
- リサーチ・ファクター
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- データ管理
  - calendar_update_job(conn)
  - get_last_price_date / get_last_financial_date / get_last_calendar_date
- 品質チェック
  - run_all_checks(conn, target_date=None, ...)
- 監査ログ初期化
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)
- ニュース収集（RSS）
  - fetch_rss(url, source, timeout=30)

---

## 必要条件

- Python 3.10 以上
- 推奨パッケージ（主要な実行に必要）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib 等）は既に利用

pip でのインストール例（プロジェクトルートで）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
pip install -e .
```

（プロジェクトがパッケージ化されている想定で `pip install -e .` を推奨）

---

## 環境変数・設定

設定は環境変数またはプロジェクトルートの `.env`, `.env.local` から自動で読み込まれます（ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。設定は `kabusys.config.settings` からアクセスできます。

重要な環境変数（必須）:
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD：kabuステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN：Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID：通知先 Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV：development / paper_trading / live（デフォルト `development`）
- LOG_LEVEL：`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト `INFO`）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH：監視用 SQLite パス（デフォルト `data/monitoring.db`）
- OPENAI_API_KEY：OpenAI 呼び出しで利用（score_news, score_regime に渡すことも可）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
2. Python 仮想環境作成・有効化
3. 依存パッケージをインストール（上記参照）
4. `.env` を作成して必要な環境変数を設定
5. DuckDB データベース接続先のディレクトリを作成（自動的に作られることが多いですが、保証したい場合は手動で作成）

---

## 使い方（簡単な例）

以下は簡易的な利用例です。実行前に環境変数（JQUANTS_REFRESH_TOKEN など）を設定してください。

- DuckDB 接続を作成する例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（target_date を指定しないと today が使われる）:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ったニューススコアリング:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("scored:", n_written)
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB 初期化:
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# 以降 audit_conn を使って監査テーブルへ書き込み可
```

- ニュース RSS 取得（単体テスト等）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## 注意点 / 設計上の考慮

- ルックアヘッドバイアス対策: 多くの処理（ニュースウィンドウ、MA 計算、ETL の target_date 処理）は `date.today()` を直接参照せず、呼び出し側で `target_date` を渡すことを前提にしています。バックテスト等では必ず対象日を明示してください。
- OpenAI / J-Quants API 呼び出しはリトライやフォールバックが組み込まれていますが、API キーやレート制限はプロジェクト側で適切に管理してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。自動読み込みを抑制する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の executemany 等で空リストを渡すとバージョン差によりエラーになることがあるため、保存処理では空チェックが入っています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                      : 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   : ニュース NLP（LLM 呼び出し・バッチ処理）
    - regime_detector.py            : 市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py        : マーケットカレンダー管理
    - etl.py                        : ETL インターフェース（ETLResult エクスポート等）
    - pipeline.py                   : 日次 ETL パイプライン実装
    - stats.py                      : 統計ユーティリティ（zscore 正規化等）
    - quality.py                    : データ品質チェック
    - audit.py                      : 監査ログスキーマの初期化
    - jquants_client.py             : J-Quants API クライアント + DuckDB 保存
    - news_collector.py             : RSS 収集・前処理
  - research/
    - __init__.py
    - factor_research.py            : ファクター計算（momentum/value/volatility）
    - feature_exploration.py        : 将来リターン / IC / 統計サマリー等
  - research、ai、data パッケージはそれぞれリサーチ・NLP・データ管理周りを担当

---

## 開発・テスト

- 単体テストの実装・実行はこの README に含まれていませんが、テストしやすい設計（依存注入、モック可能な private 関数等）が施されています。
- OpenAI 呼び出しは内部で専用ラッパー関数を使っているため、unittest.mock.patch を使って差し替えが容易です。
- ETL 実行や API 呼び出しは外部サービスに依存するため、CI ではモックやローカル DuckDB を使った統合テストを推奨します。

---

何か特定の利用例（バックテスト連携、kabuステーション発注、Slack 通知の統合など）について README に追記したい点があれば教えてください。必要に応じて実行コマンド例やサンプル .env.example も作成します。