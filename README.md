# KabuSys

KabuSys は日本株のデータパイプライン、リサーチ、AI を用いたニュース解析、及び監査/発注トレーサビリティを備えた自動売買プラットフォーム用の Python ライブラリ群です。本リポジトリは ETL、データ品質チェック、ファクター計算、ニュース NLP（OpenAI）、市場レジーム判定、監査ログ（DuckDB）などの基盤処理を提供します。

## 主な特徴
- データ取得・ETL
  - J-Quants API から株価（日足）・財務・市場カレンダーを差分取得して DuckDB に保存
  - 差分取得 / バックフィル / ページネーション / リトライ、レートリミット対応
- データ品質チェック
  - 欠損値検出、スパイク検出、重複チェック、日付整合性チェックを実施
- ニュース収集・NLP
  - RSS からのニュース収集（SSRF 対策／トラッキング除去／gzip 対応）
  - OpenAI（gpt-4o-mini）を用いたニュースの銘柄別センチメント付与（ai_scores テーブル）
  - マクロニュースを用いた市場レジーム判定（ma200 + LLM センチメントの合成）
- リサーチ用ユーティリティ
  - モメンタム／バリュー／ボラティリティ等のファクター計算、将来リターン、IC（Spearman）
  - Zスコア正規化等の統計ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルを提供、監査 DB 初期化ユーティリティあり
- 設定管理
  - .env / .env.local / 環境変数の自動読み込み（パッケージ配布後も動作するルート検出）

---

## セットアップ（開発 / 実行環境の準備）

前提
- Python 3.9+（typing の新構文を使用）
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml

例: 仮想環境作成とパッケージインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発用にローカルパッケージとしてインストールする場合:
# pip install -e .
```

環境変数（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携など）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack 送信先チャンネル ID
- OPENAI_API_KEY: OpenAI 呼び出しに使用（news_nlp / regime_detector は引数で上書き可能）
- オプション: DUCKDB_PATH / SQLITE_PATH / KABU_API_BASE_URL / KABUSYS_ENV / LOG_LEVEL

自動読み込み
- プロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）にある `.env` および `.env.local` が自動的に読み込まれます。
- 自動読み込みを無効化する場合:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な利用例）

以下はライブラリを直接インポートして利用する例です。DuckDB を用いる前提で説明します。

1) 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- J-Quants の認証は settings.jquants_refresh_token を参照します（.env に設定してください）。
- `run_daily_etl` はカレンダー・株価・財務の差分取得と品質チェックを順に実行します。

2) ニュースセンチメント（銘柄別）を生成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# APIキーを引数で渡すことも可能: api_key="sk-xxx"
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

3) 市場レジーム判定を実行する（ma200 + マクロニュースLLM）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db

# ファイル DB を作成してスキーマを初期化（親ディレクトリ自動作成）
conn = init_audit_db("data/monitoring.duckdb")
# 以後 conn を使って監査ログの INSERT/SELECT が可能
```

5) RSS を取得して raw_news に保存する（ニュースコレクタを利用する場合は独自にラッパーを作成）
- ライブラリ内の fetch_rss を使って記事を取得できます。取得後、DB への保存ロジックを作成してください。
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点
- OpenAI 呼び出しでは API エラーやレートリミットに対してリトライやフォールバック（失敗時は中立スコア）を実装していますが、利用する際は OpenAI の利用料とレートに注意してください。
- ETL / AI モジュールはルックアヘッドバイアスを避ける設計（target_date より未来のデータを参照しない）になっています。

---

## ディレクトリ構成（主なファイルと役割）
（省略されたテストやセットアップファイルがある前提）

- src/kabusys/
  - __init__.py
    - パッケージのバージョンなどを定義
  - config.py
    - 環境変数読み込み・設定管理（.env 自動ロード・必須チェック）
  - ai/
    - __init__.py
    - news_nlp.py: ニュースを銘柄別に集約して OpenAI でスコア付与 → ai_scores に書き込む
    - regime_detector.py: ETF(1321) の MA200 乖離とマクロニュース LLM を合成して market_regime に書込
  - data/
    - __init__.py
    - calendar_management.py: 市場カレンダー管理・営業日判定ユーティリティ
    - etl.py: ETLResult の公開エントリ（再エクスポート）
    - pipeline.py: 日次 ETL / 個別 ETL ジョブ（prices, financials, calendar）
    - stats.py: z-score 正規化など統計ユーティリティ
    - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py: 監査ログ（signal_events / order_requests / executions）のDDL / 初期化ユーティリティ
    - jquants_client.py: J-Quants API クライアント（リトライ、レート制限、保存関数）
    - news_collector.py: RSS 取得・前処理・SSRF 防御・ID生成のロジック
  - research/
    - __init__.py
    - factor_research.py: Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py: 将来リターン計算、IC、統計サマリー等
  - monitoring / execution / strategy / etc.
    - （本リポジトリ内の他モジュール群。実装に応じて発注・監視・ストラテジー層が存在）

---

## 開発上の注意
- DuckDB の executemany に空リストを与えるとエラーになるバージョンがあるため、コード内で空チェックを行っています。
- OpenAI SDK のレスポンス形式（JSON Mode）を前提にしており、予期せぬ文字列が混入する場合のパース復元ロジックを備えています。
- 外部ネットワークを扱う箇所（RSS 取得、J-Quants、OpenAI）はタイムアウト・リトライを考慮しています。運用時は API キーやレート制限に応じた運用設計を行ってください。
- .env 読み込みはプロジェクトルートを自動検出して行います。ユニットテスト等で自動読み込みを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

必要であれば、README に以下を追加できます：
- 具体的な SQL スキーマ（テーブル定義）の抜粋
- CI / テスト実行手順
- 運用時の cron / Airflow などのジョブ設定例
- 依存パッケージの固定 requirements.txt 例

ご希望があれば追記します。