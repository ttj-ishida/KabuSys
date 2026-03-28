# KabuSys

日本株自動売買システム・ライブラリ（kabusys）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けのデータパイプライン、リサーチ、AI ベースのニュース解析、監査ログ（トレーサビリティ）、および市場レジーム判定を含むライブラリ群です。J-Quants API からのデータ取得、DuckDB を使ったデータ保存・品質チェック、OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価などを提供します。バックテストや自動売買システムの基礎コンポーネントとして利用できます。

主な設計方針：
- ルックアヘッドバイアス（未来情報参照）を避ける（内部で date.today() などを安易に使わない）
- DuckDB をデータ格納の中心に置く（ETL は冪等的に保存）
- 外部 API への呼び出しはリトライ・レート制御・フェイルセーフを実装
- 監査ログ（signal → order_request → execution のトレーサビリティ）を厳格に保持

---

## 機能一覧

- 環境設定管理（.env 自動ロード / Settings オブジェクト）
- J-Quants API クライアント（株価・財務・カレンダー取得、保存）
- ETL パイプライン（差分取得・保存・品質チェック）
- 市場カレンダー管理（営業日判定 / next/prev / get_trading_days）
- ニュース収集（RSS 取得・前処理・保存補助）
- ニュース NLP（OpenAI を使った銘柄別センチメント → ai_scores）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
- 研究用ユーティリティ（モメンタム / バリュー / ボラティリティ計算、将来リターン、IC 計算、Z-score 正規化）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ初期化（監査用テーブルとインデックスの作成）
- DuckDB ベースの監査 DB 初期化ユーティリティ

---

## セットアップ手順

前提：
- Python 3.10+（タイプヒントに | を使うコードがあるため）
- DuckDB ライブラリ（duckdb）
- OpenAI Python SDK（openai）を利用する機能あり（AI 機能を使う場合）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローンまたはパッケージをソースから配置
2. 依存関係をインストール（例）:
   pip install duckdb openai defusedxml
   （必要に応じてその他の依存を追加してください）

3. 環境変数を設定
   プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（自動ロードはデフォルト有効）。
   自動ロードを無効化する場合：
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   例: .env（最小）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   必須環境変数（Settings が require するもの）
   - JQUANTS_REFRESH_TOKEN
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID
   - KABU_API_PASSWORD
   （OpenAI は各 AI 関数で api_key 引数を直接渡すか OPENAI_API_KEY 環境変数を使います）

4. DuckDB 用ディレクトリ作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（主要 API 例）

以下は典型的な利用例です。各関数は duckdb 接続を受け取るため、DuckDB の接続を渡して呼び出します。

共通: DuckDB 接続作成例
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

1) 日次 ETL（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日を対象に実行（内部で営業日に調整）
result = run_daily_etl(conn, target_date=None, id_token=None)
print(result.to_dict())
```

2) ニュースセンチメント（OpenAI 使用）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# 必要: OPENAI_API_KEY 環境変数 または api_key 引数でキーを渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定（MA + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

5) 監査ログ DB 初期化（監査テーブル・インデックス作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って signal/order/execution ログを操作できます
```

6) 市場カレンダー関数例
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
from datetime import date

d = date(2026,3,20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

7) J-Quants クライアント直接利用（必要に応じて）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

quotes = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
fin = fetch_financial_statements(date_from=date(2025,1,1), date_to=date(2026,3,20))
```

8) ニュース収集（RSS 取得のみ）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（ai 関数で未指定時に参照）
- SLACK_BOT_TOKEN: Slack ボットトークン（通知に使用）
- SLACK_CHANNEL_ID: Slack チャンネル ID（通知に使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

設定は .env または OS 環境変数で指定できます。パッケージは起点ファイルからプロジェクトルート（.git または pyproject.toml を探索）を探し、自動で .env/.env.local を読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## よく使う内部 API（短説明）

- kabusys.config.settings: 環境設定（プロパティアクセス）
- kabusys.data.jquants_client:
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（トークン取得）
- kabusys.data.pipeline:
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult（実行結果オブジェクト）
- kabusys.data.quality:
  - run_all_checks（品質チェックの統合呼出し）
- kabusys.data.calendar_management:
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- kabusys.data.news_collector:
  - fetch_rss / preprocess_text（RSS 取得と前処理）
- kabusys.ai.news_nlp:
  - score_news（銘柄別ニュースセンチメントの生成）
- kabusys.ai.regime_detector:
  - score_regime（市場レジーム判定）
- kabusys.research:
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.audit:
  - init_audit_schema / init_audit_db（監査ログ初期化）

---

## ディレクトリ構成

簡易ツリー（主要ファイル）
```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ ai/
   │  ├─ __init__.py
   │  ├─ news_nlp.py
   │  └─ regime_detector.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ pipeline.py
   │  ├─ etl.py
   │  ├─ jquants_client.py
   │  ├─ news_collector.py
   │  ├─ calendar_management.py
   │  ├─ stats.py
   │  ├─ quality.py
   │  ├─ audit.py
   │  └─ etc...
   ├─ research/
   │  ├─ __init__.py
   │  ├─ factor_research.py
   │  └─ feature_exploration.py
   ├─ research/ (他ユーティリティ)
   └─ (strategy/, execution/, monitoring/ などのパッケージが想定される)
```

各ファイルは README 内の「よく使う内部 API」に書かれている役割に対応します。

---

## 運用上の注意・ベストプラクティス

- AI 機能（score_news / score_regime）を利用する際は OpenAI の利用料・レートに注意してください。モックを使った単体テストのために各モジュール内の _call_openai_api をパッチできるように設計されています。
- J-Quants API はレート制限があるため、jquants_client 内で RateLimiter による固定間隔スロットリングとリトライが実装されています。大量の連続リクエストを行う際は設定に注意してください。
- ETL は部分失敗を許容して続行する設計ですが、result.errors および result.quality_issues を監視し、重大な品質問題があれば人が介入してください。
- 監査ログは削除しない前提で設計されています。order_request_id を冪等キーとして二重発注防止を行ってください。
- DuckDB は executemany に空リストを渡すと失敗するバージョンがあるため、ライブラリ内でも空チェックが入っています。自分で executemany を呼ぶ際は注意してください。

---

もし README に追加したい詳細（例えば CI/CD 手順、開発用の Dockerfile、例データやサンプルワークフロー）があれば教えてください。必要に応じてサンプル .env.example や実行スクリプトのテンプレートを作成します。