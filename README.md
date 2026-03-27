# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどを含む一連のユーティリティを提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- J-Quants API からの株価・財務・カレンダーなどの差分取得と DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集と前処理、ニュースと銘柄の紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント分析（AI スコアリング）
- ETF（1321）の長期移動平均乖離とマクロニュースから市場レジームを判定
- 研究用ファクター計算・特徴量解析（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック、マーケットカレンダー管理
- 発注・約定フローの監査ログ（監査用 DuckDB スキーマの初期化）

設計上の特徴：
- Look-ahead バイアスを避ける実装（内部で直接 `datetime.today()` を参照しない）
- DuckDB を中心としたローカル永続化と冪等保存
- API 呼び出しに対してリトライ・レートリミット制御・フェイルセーフを備える

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（取得 + DuckDB 保存関数）
  - pipeline: 日次 ETL（run_daily_etl）および個別 ETL（run_prices_etl 等）
  - calendar_management: マーケットカレンダー判定・更新ロジック
  - news_collector: RSS 取得・前処理（SSRF 対策、サイズ制限、URL 正規化）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを取得して ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースに基づく市場レジーム判定
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提（依存関係）

主に標準ライブラリで実装されていますが、ランタイムでは以下が必要です：

- Python 3.10+
- duckdb
- openai (OpenAI の新 SDK, OpenAI クライアント)
- defusedxml

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
# あるいは必要なパッケージを個別に
pip install duckdb openai defusedxml
```

※ 本リポジトリは src レイアウトを仮定しています。setup / pyproject に従ってインストールしてください。

---

## 環境変数 / 設定

settings（kabusys.config.Settings）で読み込む主な環境変数：

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD (必須)  
  kabuステーション API パスワード（発注周りで利用想定）
- KABU_API_BASE_URL (任意, default: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)  
  Slack 通知用トークン
- SLACK_CHANNEL_ID (必須)  
  Slack 通知先チャンネル ID
- DUCKDB_PATH (任意, default: data/kabusys.duckdb)  
  デフォルトの DuckDB ファイルパス
- SQLITE_PATH (任意, default: data/monitoring.db)
- KABUSYS_ENV (任意, default: development)  
  有効値: development / paper_trading / live
- LOG_LEVEL (任意, default: INFO)  
  有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL
- OPENAI_API_KEY (必要時)  
  OpenAI API 呼び出しに使用（score_news / score_regime に渡すか env に設定）

.env の自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を自動読み込みします。
- 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます（テスト向け）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンし、仮想環境を準備

```bash
git clone <repo-url>
cd <repo-root>
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

2. 必要な環境変数を設定（.env を作成）

例: .env（プロジェクトルート）

```
JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

3. DuckDB の初期スキーマ（監査ログ等）を作成（任意）

Python REPL またはスクリプトで:

```python
import duckdb
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
# これで監査用のテーブルが作成されます
```

---

## 使い方（代表的な API 使用例）

以下は簡単なコード例です。適切に環境変数を設定してから実行してください。

- 日次 ETL を実行する（prices/financials/calendar の差分取得、品質チェック含む）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 単独で株価 ETL を走らせる（ページネーション対応）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_prices_etl

conn = duckdb.connect("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
print("fetched:", fetched, "saved:", saved)
```

- ニュースセンチメント（銘柄別）をスコアリングして ai_scores に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY が env にあれば None で可
print("written:", n_written)
```

- 市場レジームを判定して market_regime に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 研究用ファクター計算例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
```

- RSS フィードの取得（news_collector.fetch_rss）

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

---

## ディレクトリ構成

（主要ファイル・モジュールの概観）

- src/kabusys/
  - __init__.py
  - config.py                   - 環境変数 / 設定読み込みロジック
  - ai/
    - __init__.py                - score_news をエクスポート
    - news_nlp.py                - ニュース NLP スコアリング（score_news）
    - regime_detector.py         - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          - J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py                - ETL パイプライン（run_daily_etl 等）
    - etl.py                     - ETLResult の再エクスポート
    - news_collector.py          - RSS 取得・前処理
    - calendar_management.py     - マーケットカレンダー管理
    - quality.py                 - データ品質チェック
    - stats.py                   - zscore_normalize 等
    - audit.py                   - 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py         - calc_momentum / calc_value / calc_volatility
    - feature_exploration.py     - calc_forward_returns / calc_ic / factor_summary / rank
  - research/*                    - 研究用ユーティリティ

---

## 運用上の注意 / 設計に関するポイント

- Look-ahead バイアス防止のため、ETL・分析関数は内部で現在日時を勝手に参照せず、target_date を明示的に受け取る設計です。バックテスト等で使用する際は target_date を正しく渡してください。
- OpenAI API 呼び出しはリトライ・タイムアウトなどのハンドリングを備えていますが、API キー・レート制限に注意してください。
- J-Quants API はレート制限と 401 トークンリフレッシュロジックを実装しています。JQUANTS_REFRESH_TOKEN を用意してください。
- news_collector は SSRF や XML インジェクション（defusedxml）対策、レスポンスサイズ制限を実装していますが、運用では信頼できる RSS ソースのみを設定することを推奨します。

---

## 追加情報 / 開発

- 単体テストを用意することでリトライや外部 API 呼び出し部分はモック化してテスト可能です（コード中にモック用の差し替えポイントを用意しています）。
- 本 README はコードベースの主要機能を抜粋したサマリです。各モジュール内の docstring に詳細な仕様・設計方針が書かれていますので、実装を修正・拡張する際は各ファイルの docstring を参照してください。

---

ご要望があれば、README をプロジェクトの pyproject.toml に合わせたインストール手順や、具体的なサンプルスクリプト（ETL バッチの crontab/airflow 用テンプレートや、Slack 通知の例）を追加します。