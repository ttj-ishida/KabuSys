# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクター計算、監査ログ・発注トレース、マーケットカレンダー管理などを提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 概要

KabuSys は以下の領域をカバーするモジュール群を持つライブラリです。

- データ取得・ETL（J-Quants API 経由）
- ニュース収集と LLM による銘柄ごとのセンチメント解析（gpt-4o-mini を想定）
- 日次 ETL パイプラインとデータ品質チェック
- リサーチ用ファクター計算（モメンタム / バリュー / ボラティリティ等）
- マーケットカレンダー管理（JPX）
- 監査ログ（signal → order_request → executions のトレース）
- 環境変数ベースの設定管理（.env 自動ロード機能）

設計方針として「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API障害時はスキップ・デフォールト）」を重視しています。

---

## 機能一覧（主な公開 API）

- 環境設定
  - kabusys.config.settings: 各種設定（J-Quants トークン、Kabu API 設定、DB パスなど）
  - 自動 .env ロード（プロジェクトルートにある `.env` / `.env.local`、無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）

- データ ETL
  - kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
    - 日次の市場カレンダー / 株価 / 財務データの差分取得と品質チェック
  - 個別ジョブ:
    - run_prices_etl, run_financials_etl, run_calendar_etl

- J-Quants クライアント
  - kabusys.data.jquants_client.get_id_token(...)
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系関数で DuckDB へ冪等保存

- ニュース & NLP
  - kabusys.data.news_collector.fetch_rss(...)：RSS 取得と前処理
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)：銘柄別 ai_score を ai_scores テーブルへ保存
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)：市場レジーム（bull/neutral/bear）を market_regime テーブルへ保存

- リサーチ / ファクター
  - kabusys.research.calc_momentum / calc_value / calc_volatility
  - kabusys.research.feature_exploration.calc_forward_returns, calc_ic, factor_summary, rank
  - kabusys.data.stats.zscore_normalize

- カレンダー管理
  - kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job(conn, lookahead_days=...)

- 監査ログ（監査テーブル初期化）
  - kabusys.data.audit.init_audit_schema(conn, transactional=False)
  - kabusys.data.audit.init_audit_db(db_path)

- データ品質チェック
  - kabusys.data.quality.run_all_checks(...)（欠損・重複・スパイク・日付不整合）

---

## 要求環境 / 依存パッケージ（例）

実際のビルド設定はプロジェクトの pyproject.toml / requirements に従ってください。主要依存は次の通りです。

- Python 3.10+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

ローカル開発時は仮想環境を作成して依存をインストールしてください。

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .           # パッケージがセットアップ可能な場合
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／展開
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数の設定（.env をプロジェクトルートに配置することを推奨）

推奨される .env に含める変数（必須・任意）:

必須（ETL 実行や一部機能で必要）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- OPENAI_API_KEY : OpenAI API キー（score_news / regime_detector で使用; 関数引数で明示的に渡すことも可）

KabuStation / 実運用で使う場合
- KABU_API_PASSWORD
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)

その他（ログや DB パス、監視設定）
- LINE_CHANNEL_ACCESS_TOKEN、LINE_USER_ID
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development|paper_trading|live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

自動 .env ロード:
- パッケージ読み込み時にプロジェクトルート (.git または pyproject.toml を上位で探索) にある `.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効化する場合:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（簡単な例）

以下は典型的な利用例です。DuckDB 接続を作成して各 API を呼び出します。

- ETL（デイリー）を実行:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースに対する銘柄スコア（OpenAI API キーは環境変数 OPENAI_API_KEY または引数で指定）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブル群が作成されます
```

- マーケットカレンダー判定:
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- AI モジュールは OpenAI API を呼び出します。API キーが設定されていない場合は ValueError が発生します（関数引数で api_key を渡すことも可）。
- ETL / J-Quants クライアントは J-Quants のリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必要です。
- DuckDB のスキーマやテーブルはプロジェクトの別スクリプト（schema 初期化等）で作成する前提です。save_* 関数は与えられたテーブルに対して冪等に INSERT/UPDATE を行います。

---

## 設定（重要な環境変数一覧）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector が利用）
- KABU_API_PASSWORD — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)
- LOG_LEVEL — ログレベル（DEBUG|INFO|...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env 読み込みを無効化

（詳細は kabusys/config.py を参照）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主なモジュール構成です（抜粋）。

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
    - etl.py (ETLResult re-export)
    - stats.py
    - quality.py
    - calendar_management.py
    - news_collector.py
    - audit.py
    - (その他: schema/init などを想定)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - (その他: strategy, execution, monitoring パッケージが __all__ に予定)

各モジュールは docstring と設計方針が充実しており、関数単位での責務が明確です。

---

## 開発メモ / 注意事項

- ルックアヘッドバイアス対策: 多くの関数は date 引数を明示的に受け取り、内部で date.today()/datetime.today() を参照しない設計です。バックテスト時は適切な target_date を指定してください。
- 冪等性: J-Quants から取得したデータを保存する関数は ON CONFLICT DO UPDATE による冪等保存を行います。
- フェイルセーフ: LLM 呼び出しや外部 API の失敗時は例外を投げずにスコア 0.0 を採用するなどのフェイルセーフ処理が施されています（ログは出力されます）。
- テスト: 各種 HTTP / OpenAI 呼び出しは関数単位で差し替え（mock）できるよう設計されています（例: _call_openai_api を patch）。

---

README はここまでです。実行時のエラーや具体的なスキーマ初期化・マイグレーション、CI 設定などはプロジェクトの追加ドキュメント（pyproject.toml / docs）に従ってください。必要であれば、使い方の具体的なコード例（ETL スケジュール、CI 用テスト用モック例など）を追記します。