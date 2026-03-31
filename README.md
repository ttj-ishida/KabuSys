# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。ETL（J-Quants）、ニュース収集・NLP、リサーチ（ファクター計算）、監査ログ、マーケットカレンダー、監視・発注インターフェース等のユーティリティを提供します。

主な設計思想：
- DuckDB を中心にしたオンプレ・ローカル処理（バックテスト・運用双方を想定）
- Look‑ahead バイアス回避（内部で date.today() を直接参照しない等）
- 外部 API 呼び出しに対する堅牢なリトライ・フォールバック
- 冪等性（DB への保存は ON CONFLICT / idempotent 実装）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定）
  - 必須変数チェック（Settings オブジェクト）
- データ ETL（J-Quants）
  - 株価日足（raw_prices）の差分取得・保存（fetch / save）
  - 財務データ（raw_financials）の差分取得・保存
  - JPX マーケットカレンダー取得・保存
  - 日次 ETL パイプライン（run_daily_etl）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース系
  - RSS 収集（fetch_rss、前処理、SSRF 対策、トラッキング除去）
  - ニュース NLP（score_news）：OpenAI を使った銘柄別センチメント集計・ai_scores への保存
  - 市場レジーム判定（score_regime）：ETF（1321）の MA200 乖離 + マクロニュース（LLM）で判定
- リサーチ / ファクター
  - モメンタム / バリュー / ボラティリティ計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン算出 / IC 計算 / 統計サマリー
  - Zスコア正規化ユーティリティ
- 監査 / トレーサビリティ
  - signal_events / order_requests / executions の監査スキーマ定義・初期化（init_audit_schema / init_audit_db）
- J-Quants クライアント（rate limiting・リトライ・トークン自動リフレッシュ・DuckDB への保存関数）
- ユーティリティ（統計、カレンダー判定、ニュース前処理 など）

---

## 動作要件（主な依存パッケージ）

- Python 3.10+
- duckdb
- openai
- defusedxml

（他に標準ライブラリの urllib, json, datetime 等を広く使用）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# ローカルパッケージとして使う場合（プロジェクトルートに pyproject.toml があることを想定）
pip install -e .
```

---

## 環境変数（主なもの）

設定は .env または OS 環境変数で行います。パッケージはプロジェクトルート（.git または pyproject.toml）を基に .env/.env.local を自動読込します。自動読込を無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（Settings で _require されるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使用（必要時）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必要時）

任意／デフォルトあり:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) (default: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (default: INFO)
- OPENAI_API_KEY — OpenAI を使う機能（score_news / score_regime）で必要

例（.env の簡易例）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=my_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン／取得
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール
   - 最低限: duckdb, openai, defusedxml
   - 例: pip install duckdb openai defusedxml
4. プロジェクトルートに .env または .env.local を作成し、上記の環境変数を設定
5. DuckDB データディレクトリを作成（例: data/）
6. （必要なら）監査用 DB 初期化を実行

---

## 使い方（代表的な例）

以下は Python REPL やスクリプトからの呼び出し例です。DuckDB 接続には duckdb.connect(...) を使用します。

- 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores）を生成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print("書き込み銘柄数:", n_written)
```
OPENAI_API_KEY を環境変数に設定していれば api_key 引数は不要です。

- 市場レジームを判定する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
```

- 監査ログ用の DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は監査スキーマが作成された DuckDB 接続
```

- ニュース RSS を取得して raw_news に保存（fetch_rss は記事取得のみ）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
# 取得後、DB に保存するロジックはアプリ側で実装（fetch -> INSERT）
```

---

## 注意事項 / 運用メモ

- OpenAI API 呼び出しは明示的なリトライ・フォールバック処理がありますが、API キーのレートやコストを考慮してください。
- ETL / データ取得処理は Look‑ahead バイアスを避けるため、target_date を明示して実行することを推奨します。内部で date.today() を直接参照する処理は極力避けていますが、run_daily_etl のデフォルトは実行日です。
- settings は .env(.local) / 環境変数を参照します。テスト時に自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の executemany に空リストを渡すと問題になるバージョン（例: 0.10）があるため、内部でガードしています。DuckDB のバージョン差に注意してください。

---

## ディレクトリ構成（抜粋と説明）

ルート: src/kabusys 以下に主要モジュールが配置されています。

- kabusys/
  - __init__.py
  - config.py
    - Settings: 環境変数取得・バリデーション、自動 .env ロード処理
  - ai/
    - __init__.py
    - news_nlp.py         : ニュースを LLM でスコアリングして ai_scores に保存
    - regime_detector.py  : マクロニュース + ETF ma200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   : J-Quants API クライアント（fetch/save 含む）
    - pipeline.py         : ETL パイプライン（run_daily_etl 等）
    - etl.py              : ETL 公開インターフェース（ETLResult の再エクスポート）
    - news_collector.py   : RSS 取得・前処理（SSRF 対策等）ユーティリティ
    - calendar_management.py : マーケットカレンダー管理（is_trading_day 等）
    - stats.py            : zscore_normalize 等の統計ユーティリティ
    - quality.py          : データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py            : 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py  : momentum / value / volatility 等のファクター計算
    - feature_exploration.py : forward returns / calc_ic / factor_summary / rank 等

各モジュールは DuckDB 接続を引数に取り、外部副作用（実際の注文送信など）を行わない設計のものが多く、テストしやすくなっています。

---

もし README に追加してほしい具体的な実行スクリプト例（systemd タスク、Airflow DAG、cron 等）や、pyproject.toml / packaging のサンプルが必要であれば教えてください。必要に応じて .env.example のテンプレートも作成します。