# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
J-Quants / kabuステーション / OpenAI 等の外部サービスからデータを取り込み、品質チェック・特徴量計算・ニュースセンチメント・監査ログなどのユーティリティを提供します。

## 概要

KabuSys は以下の目的を持つモジュール群を含みます。

- データ取得・ETL（J-Quants API 経由の株価・財務・マーケットカレンダー）
- ニュース収集・NLP（RSS 収集、OpenAI を用いた銘柄センチメント算出）
- 市場レジーム判定（MA とマクロニュースを組み合わせた判定）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、正規化）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order → execution のトレーサビリティ）
- 設定管理（.env / 環境変数の読み込み・検証）

設計上の共通方針として、ルックアヘッドバイアスを避けるために内部で `date.today()` 等を安易に参照せず、DuckDB を用いた SQL ベースの処理を採用しています。

## 主な機能

- ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- J-Quants API クライアント（ページネーション・リトライ・トークン自動リフレッシュ対応）
- ニュース RSS 収集（SSRF 対策・コンテンツ圧縮制限・トラッキング除去）
- ニュースセンチメント（OpenAI / gpt-4o-mini を用いた銘柄別スコアリング）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコアを合成）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- データ品質チェック（QualityIssue による問題収集）
- 監査ログ初期化（init_audit_schema / init_audit_db）

## 動作要件（例）

- Python 3.10+
- 必要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）
- 環境変数 / .env に API トークン等を設定

（実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください）

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

2. 依存パッケージをインストールします（例）。

   pip install duckdb openai defusedxml

3. 環境変数 / .env を用意します。
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` として保存すると自動読み込みされます。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード
   - SLACK_BOT_TOKEN       : Slack Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 等で使用）
   - 任意:
     - KABUSYS_ENV (development / paper_trading / live)
     - LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)

5. データベースディレクトリの作成（必要に応じて）

   mkdir -p data

## .env の書き方例

例: .env

JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO

注意: .env の自動読み込みは OS 環境変数を優先します。`.env.local` は `.env` の上書きとして読み込まれます（.env.local が優先）。

## 使い方（代表的な利用例）

以下は Python スクリプト内での利用例です。

- 設定取得

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必須。未設定なら ValueError
print(settings.duckdb_path)            # Path オブジェクト
```

- DuckDB 接続と日次 ETL 実行

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
if result.has_errors:
    print("ETL 中にエラーあり:", result.errors)
```

- ニュースセンチメント計算（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"{written} 銘柄のスコアを書き込みました")
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（専用 DB を作る場合）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンも設定されます
```

- RSS フィードの取得（ニュース収集モジュールの一部）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

source_name = "yahoo_finance"
url = DEFAULT_RSS_SOURCES[source_name]
articles = fetch_rss(url, source=source_name)
for a in articles[:5]:
    print(a["datetime"], a["title"])
```

注意点:
- OpenAI 呼び出しはネットワーク/レート制限エラーを考慮した実装になっており、ユニットテスト時は内部の API 呼び出しをモックすることが想定されています（例: unittest.mock.patch）。
- J-Quants クライアントは内部でトークンキャッシュとリトライを実装しています。get_id_token() は settings.jquants_refresh_token を用います。

## 主要 API（抜粋）

- kabusys.config.settings — 環境変数からの設定取得
- kabusys.data.pipeline.run_daily_etl — 日次 ETL のメインエントリ
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes — J-Quants API と保存
- kabusys.data.news_collector.fetch_rss — RSS フェッチ
- kabusys.ai.news_nlp.score_news — 銘柄別ニュースセンチメント算出（AI）
- kabusys.ai.regime_detector.score_regime — 市場レジーム判定（MA + マクロニュース）
- kabusys.research.* — ファクター計算・分析ユーティリティ
- kabusys.data.quality.run_all_checks — データ品質チェック
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログ初期化

各関数の詳細は該当モジュールの docstring を参照してください。

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env の自動読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（銘柄単位の OpenAI 呼び出し）
    - regime_detector.py — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント、保存ロジック
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダーユーティリティ
    - news_collector.py — RSS 収集・前処理
    - quality.py — 品質チェック
    - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査テーブル DDL / 初期化ユーティリティ
    - etl.py — ETL インターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラ/バリューファクター計算
    - feature_exploration.py — 将来リターン / IC / サマリー
  - research/*（ユーティリティのエクスポート）
- README.md（本ファイル）

各モジュールは docstring に設計方針と使用法が記載されています。実運用に組み込む際には、まず DuckDB スキーマを用意し（ETL を回すことで自動でテーブルが作成される箇所もあります）、適切な API キーと .env を整備してください。

## 開発・テストに関するヒント

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）から行われます。テスト時に自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しやネットワークアクセスはユニットテストでモックすることを想定しています（内部の `_call_openai_api` や `_urlopen` を patch してください）。
- DuckDB は開発時に `:memory:` を用いてインメモリ DB を使用できます（init_audit_db も対応）。

---

ご要望があれば、README に含める実行スクリプトのサンプル（cron / systemd / Airflow 用タスク定義）や、DuckDB スキーマの最小セット、CI 用のテストセットアップ例などを追加します。どの情報が欲しいか教えてください。