# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤のプロトタイプライブラリです。  
ETL、データ品質チェック、ニュースNLP（LLM 統合）、市場レジーム判定、監査ログなどを含むモジュール群を提供します。

---

## 概要

KabuSys は次の目的を持つモジュール集合です。

- J-Quants API からの市場データ取得（株価日足、財務、カレンダー）
- DuckDB を用いたローカルデータストアと ETL パイプライン
- ニュース収集と OpenAI を用いたニュースセンチメント評価（銘柄単位 / マクロ）
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- データ品質チェック、マーケットカレンダー管理
- 監査ログ（signal → order → execution のトレーサビリティ）初期化ユーティリティ

設計上のポイント:
- ルックアヘッドバイアス回避のため date/target_date を明示して処理する（datetime.today() を内部で直接参照しない）
- API 呼び出しは耐障害性（リトライ・バックオフ）と冪等性（ON CONFLICT / idempotent）を重視
- テスト時に差し替え可能な内部呼び出し設計（例: OpenAI 呼び出しのモック）

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・バックフィル・保存）
  - ETLResult による実行結果集約
- データ品質
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- 市場カレンダー
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- ニュース収集・NLP
  - fetch_rss / preprocess_text / news → raw_news 保存 (news_collector)
  - score_news: OpenAI を用いた銘柄別ニュースセンチメントの算出・ai_scores へ保存
- レジーム判定
  - score_regime: ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime に保存
- 監査ログ
  - init_audit_schema / init_audit_db（監査テーブル群の作成・初期化）
- J-Quants API クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info
  - save_* 系関数で DuckDB へ冪等保存
- 研究用ユーティリティ
  - factor 計算（momentum / value / volatility）および特徴量探索（forward returns / IC / summary）
- 共通設定
  - 環境変数管理（kabusys.config.settings）と .env 自動読み込み（プロジェクトルート検出）

---

## セットアップ手順

※ 実際の requirements.txt / pyproject.toml はプロジェクトに合わせてください。以下は代表的な依存例です。

前提:
- Python 3.10+（typing に union 型や型ヒントが使われているため）
- DuckDB（python パッケージ）
- openai（OpenAI v1 SDK を想定）
- defusedxml（RSS パースの安全化）

例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# 開発版インストール（パッケージ化されていれば）
# pip install -e .
```

.env の作成:
プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化可能）。

必須環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先
- OPENAI_API_KEY — OpenAI 呼び出し（score_news / score_regime は引数でも指定可）

その他（デフォルトあり）:
- KABU_API_PASSWORD, KABU_API_BASE_URL — kabu ステーション連携
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 sqlite データベースのパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/…（デフォルト INFO）

---

## 使い方（主な例）

基本的な DuckDB 接続と ETL 実行例:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

OpenAI を使ったニューススコアリング（score_news）の例:

```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数にセットしておくか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

市場レジーム判定（score_regime）の例:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

監査ログDB の初期化例:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

設定値参照（設定 API）:

```python
from kabusys.config import settings
print(settings.duckdb_path)           # Path オブジェクト
print(settings.is_live, settings.log_level)
```

ニュース収集（fetch_rss）の例（RSS を手動にて取得して raw_news に保存する処理は news_collector を参照）:

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意: OpenAI 呼び出し関数はリトライロジックやフェイルセーフが実装されていますが、API キーの有無は事前に確認してください。テスト用に内部の API 呼び出し関数をモック可能です（例: kabusys.ai.news_nlp._call_openai_api のパッチ）。

---

## 主要な API（抜粋）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, id_token=None, ...)
  - run_prices_etl(...)
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token(refresh_token=None)
- kabusys.data.quality
  - run_all_checks(conn, ...)
- kabusys.ai.news_nlp
  - calc_news_window(target_date)
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

各関数の詳細はモジュールの docstring を参照してください。

---

## ディレクトリ構成

プロジェクトの主要ファイル構成（src 以下を抜粋）:

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
    - (その他: jquants_client での保存/取得ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (モニタリング用モジュールが存在する想定)
  - strategy/ (戦略実装用モジュールが存在する想定)
  - execution/ (発注実装用モジュールが存在する想定)

ルートには pyproject.toml / .git 等がある想定で、config.py はそれらを基準にプロジェクトルートを検出して `.env` を自動読み込みします。

---

## 注意事項 / 設計上の考慮

- Look-ahead bias の回避:
  - 多くの処理は target_date を明示することを前提に実装されています（内部で datetime.today() を参照しない）。
  - ETL / スコアリング / レジーム判定ともに「その時点でシステムが知り得た情報のみ」を使う設計を意識しています。
- 冪等性:
  - jquants_client の save_* 系は ON CONFLICT DO UPDATE 等で冪等に保存します。
  - audit の order_request_id は冪等キーとして扱う設計です。
- フェイルセーフ:
  - OpenAI 呼び出し失敗時はスコアを 0 にフォールバックするなど、致命的障害にならない振る舞いを優先しています（ログは出力されます）。
- テスト容易性:
  - 外部 API 呼び出しは内部関数をモックしやすいように分離しています。

---

## 開発 / 貢献

- コードは PEP8 / typing を意識して実装されています。ユニットテストを追加する際は外部 API 呼び出しのモック（unittest.mock.patch）を活用してください。
- 大きな変更をする場合は設計方針（Look-ahead / 冪等性 / トレーサビリティ）を維持するよう注意してください。

---

この README はコードベースの docstring とモジュール設計に基づいて作成しています。詳細な API 仕様や追加のユーティリティ関数については各モジュールの docstring を参照してください。