# KabuSys

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。  
ETL によるデータ収集、データ品質チェック、ニュース収集と LLM を使ったニュースセンチメント評価、ファクター計算、マーケットレジーム判定、監査ログ（オーディット）などをモジュールとして提供します。

---

## 概要

主な設計方針は以下の通りです。

- DuckDB をデータ基盤として利用し、J-Quants API から株価・財務・カレンダー等を差分取得する ETL パイプラインを提供します。
- ニュース収集 (RSS) → LLM による銘柄別 / マクロのセンチメント評価（OpenAI）を行う機能を備えています。
- 研究用途（ファクター計算、将来リターン、IC 等）と実運用用（監査ログ、発注ログ、約定ログ）の両方をサポートします。
- Look-ahead bias を避ける設計（target_date を明示、date.today() の無秩序な使用を避けるなど）を重視しています。
- 冪等性（INSERT ... ON CONFLICT / トランザクション）を意識した実装になっています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、トークン自動リフレッシュ、リトライ、レート制限）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS → raw_news、SSRF / Gzip / トラッキングパラメータ対策）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ（signal_events / order_requests / executions）初期化ユーティリティ
  - 汎用統計ユーティリティ（zscore_normalize 等）
- ai
  - ニュース NLP（銘柄別センチメント score_news）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM 結果を合成する score_regime）
- research
  - ファクター計算（momentum, volatility, value 等）
  - 特徴量探索（forward returns, IC, summary, rank）
- config
  - 環境変数管理（.env の自動読み込み、必須キーチェック、設定オブジェクト）

---

## セットアップ手順（開発環境）

1. Python バージョン
   - Python 3.10+ を想定（PEP 604 の型記法や __future__ の注釈を利用）。

2. 必要パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （HTTP リクエストやテスト用に urllib 等は標準ライブラリで賄われます）
   - 例: pip install duckdb openai defusedxml

   ※ プロジェクトの requirements.txt / pyproject.toml がある場合はそちらを利用してください。ローカル開発では `pip install -e .` でインストールする構成を想定しています（パッケージ化済みである前提）。

3. 環境変数（最低限必要）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
   - KABU_API_PASSWORD: kabu ステーション等の発注 API パスワード（発注関連）
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（通知機能）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI を使う機能（ai.score_news / ai.regime）の場合に必要（関数呼び出しで api_key を渡すことも可）
   - （任意）KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - （任意）LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - （任意）DUCKDB_PATH: DuckDB ファイルの保存先（デフォルト: data/kabusys.duckdb）
   - （任意）SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - .env にこれらを置くと、パッケージはプロジェクトルート（.git または pyproject.toml）を検出して自動で `.env` / `.env.local` を読み込みます。

4. .env の自動読み込みを無効化する（テスト等）
   - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. ディレクトリの初期化（データ保存先の作成）
   - DuckDB ファイル保存ディレクトリなどを事前に作ると安全です（init_audit_db は親ディレクトリ自動作成を行います）。

---

## 簡単な使い方（コードスニペット）

- DuckDB 接続を作って daily ETL を実行する例:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path を使う場合:
from kabusys.config import settings
db_path = str(settings.duckdb_path)

conn = duckdb.connect(db_path)
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）をスコア化する:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数にあるなら api_key 引数は不要
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"written scores: {n_written}")
```

- 市場レジームを判定して DB に書き込む:

```python
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ用の DuckDB を初期化する:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成されます
```

- RSS をフェッチする（ニュース収集部分のユーティリティ）:

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

url = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(url, source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"])
```

注意:
- OpenAI 呼び出し部分はネットワークに依存します。テスト時は内部の _call_openai_api をモックして呼び出しを置き換えられるように設計されています。
- ai.score_news / ai.regime_detector は api_key 引数で明示的にキーを渡せます。None の場合は環境変数 OPENAI_API_KEY を参照します。

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（ETL）
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注）
- SLACK_BOT_TOKEN — Slack ボットトークン（通知）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意・デフォルトあり:
- KABUSYS_ENV — development | paper_trading | live（default: development）
- LOG_LEVEL — INFO（デフォルト）
- KABU_API_BASE_URL — kabu API の base URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH — data/kabusys.duckdb（default）
- SQLITE_PATH — data/monitoring.db（default）
- OPENAI_API_KEY — OpenAI API キー（ai 機能を使う場合）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュールとファイル一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（銘柄別）
    - regime_detector.py     — 市場レジーム判定（1321 MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプライン（run_daily_etl など）
    - etl.py                 — ETL インターフェース再エクスポート
    - calendar_management.py — 市場カレンダー管理
    - news_collector.py      — RSS ニュース収集
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - audit.py               — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Value/Volatility 等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

---

## 注意点 / 補足

- Look-ahead バイアス対策が随所に入っています。target_date を明示して使用することを推奨します。
- ETL の各ステップは独立してエラーハンドリングしており、部分失敗しても他ステップは継続します（結果は ETLResult に集約されます）。
- DuckDB の executemany に関する制約など実運用のトリッキーな点に対応しています（空リストバインド回避等）。
- OpenAI SDK の例外（RateLimitError, APIConnectionError, APITimeoutError, APIError 等）を考慮したリトライ・フォールバック処理を含みます（失敗時はゼロやスキップして継続する設計）。
- テスト容易性のため、内部の HTTP / OpenAI 呼び出しポイントはモックできるように分離してあります。

---

必要に応じて README に、インストール用の requirements.txt や利用例スクリプト（etl runner / scheduler / Slack 通知ラッパー等）を追記できます。追加 の要望（例: Docker 化手順、システム構成図、CI 設定テンプレートなど）があれば教えてください。