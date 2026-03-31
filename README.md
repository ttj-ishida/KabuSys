# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリ（モジュール群）。  
ETL、ニュース収集・NLP、リサーチ（ファクター計算）、監査ログ、J-Quants クライアント、マーケットカレンダーなどの機能を提供します。

主な目的は「ルックアヘッドバイアスを避けつつ、DuckDB をデータ層に用いて安全にデータ取得・スコアリング・監査を行う」ことです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（代表的なサンプル）
- 環境変数例（.env）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下を中心に実装された Python パッケージです。

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- RSS を用いたニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント解析（銘柄別）およびマクロセンチメントを使った市場レジーム判定
- Research 用ユーティリティ（モメンタム、ボラティリティ、バリュー等のファクター、将来リターン、IC 等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 発注・約定に関する監査ログ（監査テーブルの初期化・DB 操作ユーティリティ）
- 設定（.env 自動読み込み・保護）と環境管理

設計上の特徴：
- Look-ahead バイアスを避けるため、日付の扱いを明示的に行う（datetime.today() などに依存しない関数設計）
- DuckDB を利用した SQL 処理（大半の処理は SQL + 軽い Python）
- API 呼び出しに対する堅牢なリトライ / レート制御 / フォールバックロジック

---

## 機能一覧

主要モジュールと代表機能：
- kabusys.config
  - .env 自動ロード（.env / .env.local）と Settings クラス（J-Quants トークン、kabu API、Slack、DB パス等）
- kabusys.data.jquants_client
  - J-Quants からのデータ取得 (fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info)
  - DuckDB への冪等保存 (save_daily_quotes / save_financial_statements / save_market_calendar)
  - トークン自動リフレッシュ、レートリミット管理
- kabusys.data.pipeline
  - 日次 ETL 実行（run_daily_etl）と個別 ETL ジョブ（run_prices_etl 等）
  - ETLResult データクラス
- kabusys.data.news_collector
  - RSS 取得（fetch_rss）、前処理（preprocess_text）、SSRF 対策、URL 正規化
- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合チェック（run_all_checks）
- kabusys.data.calendar_management
  - market_calendar の運用・営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
- kabusys.data.audit
  - 監査テーブル定義と初期化（init_audit_schema / init_audit_db）
- kabusys.ai.news_nlp
  - 銘柄ごとのニュースセンチメントを LLM に投げて ai_scores に書き込む（score_news）
- kabusys.ai.regime_detector
  - ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime を書き込む（score_regime）
- kabusys.research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）、特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- kabusys.data.stats
  - zscore_normalize（クロスセクション正規化）

---

## セットアップ手順

前提:
- Python 3.10+（型注釈の | 記法や標準ライブラリ機能を使用）
- DuckDB, openai, defusedxml などが必要

推奨インストール（例: Poetry / pipenv / pip）:
1. 仮想環境を作成・有効化
2. 必要パッケージをインストール例（pip）:
   - duckdb
   - openai
   - defusedxml

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

プロジェクト配布時の依存リストがあればそちらを使用してください。

.env ファイル:
- ルート（pyproject.toml/.git があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

DB の初期化:
- DuckDB ファイルはデフォルトで data/kabusys.duckdb（settings.duckdb_path）を指します。適宜ディレクトリ作成や接続してください。

---

## 使い方（代表的なサンプル）

以下は Python REPL / スクリプトからの利用例です。各例では DuckDB 接続オブジェクトを渡しています。

1) 設定の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)          # Path('data/kabusys.duckdb') など
print(settings.jquants_refresh_token)  # 環境変数が未設定だと例外が出ます
```

2) DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) ニュースセンチメント（銘柄別）を生成する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"書込銘柄数: {n_written}")
# OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定可能
```

4) 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

5) 監査 DB の初期化（監査用 DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.db")
# または in-memory:
# conn_audit = init_audit_db(":memory:")
```

6) RSS フィード取得の例
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- OpenAI の呼び出しは gpt-4o-mini を想定し、JSON mode を使った応答パースを行います。API 制限・エラー時は安全にフォールバックする実装になっていますが、API キーの管理には注意してください。
- ETL / スコア生成関数はルックアヘッドバイアスを避けるため、target_date を明示して使うことを推奨します。

---

## 環境変数（.env の例）

必要/想定される主要環境変数（プロジェクト内 Settings 参照）:

- JQUANTS_REFRESH_TOKEN  (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD      (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL      (任意) — デフォルト http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN        (必須) — Slack Bot トークン
- SLACK_CHANNEL_ID       (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH            (任意) — デフォルト data/kabusys.duckdb
- SQLITE_PATH            (任意) — 監視用 SQLite のパス
- KABUSYS_ENV            (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL              (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
```

自動ロード:
- パッケージ起動時にルートディレクトリに `.env`/`.env.local` があれば自動で読み込みます（ただし OS 環境変数が優先され、.env.local は上書きされます）。
- テストや明示的に自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                              — 環境変数 / Settings
- ai/
  - __init__.py
  - news_nlp.py                           — 銘柄別ニューススコアリング（score_news）
  - regime_detector.py                    — マクロ + MA200 で市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                     — J-Quants API クライアント & DuckDB 保存
  - pipeline.py                           — ETL パイプライン（run_daily_etl 等）
  - etl.py                                — ETLResult 再エクスポート
  - news_collector.py                     — RSS 収集 / 前処理
  - calendar_management.py                — 市場カレンダー管理・営業日ロジック
  - quality.py                            — データ品質チェック
  - stats.py                              — 共通統計ユーティリティ（zscore_normalize）
  - audit.py                              — 監査ログテーブル初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py                    — ファクター計算（momentum / value / volatility）
  - feature_exploration.py                — 将来リターン・IC・統計サマリー・rank
- research/*.py and others as above

補足:
- 多くの処理は DuckDB 接続（duckdb.DuckDBPyConnection）を引数として受けます。スキーマ初期化やテーブル定義はプロジェクト固有の schema 初期化関数を用意しておく必要があります（audit.init_audit_schema などを参照）。

---

## 備考 / 開発者向けメモ

- DuckDB での executemany の空リスト取り扱い等の互換性を考慮した実装がされています（DuckDB バージョンに注意）。
- OpenAI・J-Quants 呼び出しはリトライ/バックオフ/フェイルセーフを備えています。テスト時は各 _call_openai_api 等をモックしてテスト可能です。
- 外部依存（openai, defusedxml, duckdb）についてはバージョン互換性に注意してください。
- 監査テーブルは UTC タイムゾーン固定で TIMESTAMP を扱います（init_audit_schema は SET TimeZone='UTC' を実行）。

---

必要に応じて README に追記します（インストール手順を詳述したい、スキーマ定義ファイルを追加したい、CLI や Docker の起動方法を載せたい等）。どの項目を詳しく知りたいか教えてください。