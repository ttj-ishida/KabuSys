# KabuSys

日本株向けのデータプラットフォームと自動売買補助ライブラリです。  
J-Quants / kabuステーション / OpenAI を組み合わせた ETL、データ品質チェック、特徴量計算、ニュース NLP、監査ログ等の共通機能を提供します。

---

## 概要

このコードベースは次の機能群を提供します。

- J-Quants API からの株価・財務・カレンダーの差分ETL（DuckDB を使用）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- マーケットカレンダー管理（営業日判定、next/prev trading day 等）
- ニュース収集（RSS）と NLP による銘柄別センチメントスコア生成（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリ）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- kabuステーションや Slack などへの実際の発注・通知層とは分離した設計

設計上の方針として、ルックアヘッドバイアス回避、冪等性（ON CONFLICT 等）、フェイルセーフ（API失敗時はスキップやデフォルト値）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants からの取得・DuckDB への保存（fetch_* / save_*）
  - pipeline: 日次 ETL 実行エントリ（run_daily_etl 等）
  - quality: データ品質チェック（check_missing_data, check_spike, ...）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - news_collector: RSS 収集と前処理
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore 正規化ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースを合成して market_regime へ書き込み
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: 環境変数の自動読み込みと settings（必須 API トークンなど）

---

## セットアップ手順

前提
- Python 3.10 以上（typing に `|` や list[str] を使っているため）
- DuckDB を利用するため pip パッケージをインストール

推奨パッケージ（例）
```bash
python -m pip install duckdb openai defusedxml
```

プロジェクトのインストール（プロジェクトを pip editable にする場合）
```bash
# プロジェクトルートで
python -m pip install -e .
```
（実際の packaging 情報はプロジェクトに依存します。requirements.txt / pyproject.toml があればそちらを参照してください）

環境変数の設定
- プロジェクトは .env / .env.local を自動でプロジェクトルート（.git または pyproject.toml を起点）から読み込みます。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須の環境変数（Settings により参照）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API パスワード
- SLACK_BOT_TOKEN        : Slack Bot トークン
- SLACK_CHANNEL_ID       : Slack チャンネル ID
- OPENAI_API_KEY         : OpenAI API キー（ai.score_news / regime_detector で使用）

任意（デフォルトあり）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
- LOG_LEVEL (DEBUG | INFO | ...) — デフォルト `INFO`
- DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
- SQLITE_PATH — デフォルト `data/monitoring.db`

例: .env
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
```

---

## 使い方（代表的な呼び出し例）

下記は Python REPL / スクリプト内での呼び方例です。

1) DuckDB 接続の作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # パスは settings.duckdb_path と合わせても良い
```

2) 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 30))
print(result.to_dict())
```
戻り値は ETLResult（fetched/saved 数や quality_issues, errors を含む）。

3) ニュース NLP（銘柄別 ai_scores へ書き込む）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数で設定するか、api_key 引数に渡す
n_written = score_news(conn, target_date=date(2026, 3, 30), api_key=None)
print(f"written: {n_written}")
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 30), api_key=None)
# market_regime テーブルに書き込まれます
```

5) 監査ログ DB 初期化（別 DB に監査用を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 監査テーブル（signal_events, order_requests, executions）が作られます
```

6) カレンダー・営業日ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 30)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

7) 研究用ファクター計算（例: momentum）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026,3,30))
# records は {"date","code","mom_1m","mom_3m","mom_6m","ma200_dev"} の dict リスト
```

8) J-Quants クライアントの直接利用
```python
from kabusys.data.jquants_client import fetch_listed_info, fetch_daily_quotes

# id_token は自動で settings.jquants_refresh_token から取得されます
stocks = fetch_listed_info()
quotes = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,30))
```

9) RSS 取得（ニュースコレクター）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

注意点:
- OpenAI 呼び出しはリトライやエラーハンドリングを持っていますが、APIキーは環境変数か明示引数で必ず与えてください。
- ETL と品質チェックは DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news 等）が前提です。スキーマ初期化はプロジェクト固有のスクリプトで実施する想定です。

---

## ディレクトリ構成

以下は主要ファイル・モジュールの階層（抜粋）です。

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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (参照: __all__ に含まれるが本 README の抜粋では詳細省略)
  - strategy/ (戦略関連モジュールは別に存在する想定)
  - execution/ (発注実行モジュールは別に存在する想定)

各モジュールはコメントと docstring による設計意図・使用上の注意が詳細に記載されています。実運用では docstring を参照し、DB スキーマやテーブル名（raw_prices, ai_scores, market_regime 等）を整備した上で使用してください。

---

## 設計上の重要な注意点

- ルックアヘッドバイアス対策:
  - 各種関数は内部で datetime.today() や date.today() を直接参照せず、呼び出し側が target_date を明示する設計が多く採用されています。バックテストや再現性のために target_date を明示してください。
- 冪等性:
  - J-Quants からの保存関数や監査テーブル作成は冪等に設計されています（ON CONFLICT, RETURNING 等を利用）。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants 等）に失敗しても、コードは多くのケースでその失敗をロギングして安全なデフォルトで継続するよう設計されています（例: macro_sentiment = 0.0）。
- テスト容易性:
  - OpenAI 呼び出しなどは内部で差し替え可能（_call_openai_api のモックなど）な設計がされています。

---

この README はコードベースの主要な使い方と設計方針をまとめた要約です。より詳細な API / テーブルスキーマ / 運用手順は各モジュールの docstring や別途提供されるドキュメント（DataPlatform.md, StrategyModel.md 等）を参照してください。必要であれば、各機能ごとのサンプルスクリプトやスキーマDDLの README 追加を支援します。