# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
市場データの ETL、ニュースの NLP スコアリング、研究用ファクター計算、監査ログ（トレーサビリティ）、JPX カレンダー管理など、取引システム構築に必要な共通ユーティリティを提供します。

主な設計方針
- Look‑ahead bias を避ける（関数内で date.today()/datetime.today() を無暗に参照しない）。
- DuckDB を主体としたローカル DB を使用（ETL は冪等性を重視）。
- 外部 API（J‑Quants / OpenAI）呼び出しに対して堅牢なリトライ & フェイルセーフ実装。
- テストしやすいように API 呼び出し部分を差し替え可能に設計。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（代表的な API とサンプル）
- 環境変数（.env）例
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買 / 研究・データプラットフォーム向けの共通ライブラリセットです。  
主に以下を扱います。

- J-Quants API を通じた株価・財務・マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- RSS ニュース収集と OpenAI を用いた銘柄別センチメント（ai_score）生成
- 市場レジーム（bull/neutral/bear）判定（ETF の 200 日 MA と LLM によるマクロセンチメントの合成）
- 研究用のファクター計算・将来リターン・IC（Information Coefficient）など
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）用のスキーマ初期化ユーティリティ
- JPX カレンダー管理（営業日判定等）

---

## 機能一覧

主なモジュール（主要関数のみ抜粋）

- kabusys.config
  - settings: 環境変数ベースの設定オブジェクト
  - 自動的にプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可）

- kabusys.data
  - jquants_client
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - get_id_token（refresh トークン → id_token）
  - pipeline
    - run_daily_etl(conn, target_date, ...)
    - run_prices_etl / run_financials_etl / run_calendar_etl
    - ETLResult（処理結果オブジェクト）
  - news_collector
    - fetch_rss(url, source)
    - ニュース正規化と raw_news への冪等保存を行う想定（実装に従う）
  - calendar_management
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - calendar_update_job（J-Quants から差分取得して market_calendar を更新）
  - quality
    - run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency
  - audit
    - init_audit_schema(conn, transactional=False)
    - init_audit_db(db_path)

- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None)
    - raw_news と news_symbols に基づき OpenAI（gpt-4o-mini）で銘柄別センチメントを算出して ai_scores テーブルへ保存
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の ma200 乖離 + マクロニュース LLM センチメントを合成して market_regime テーブルへ保存

- kabusys.research
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats から）

その他にニュース前処理、URL 正規化、SSRF 対策や HTTP レートリミット管理など堅牢性を高めるユーティリティが含まれます。

---

## セットアップ手順

推奨 Python バージョン: 3.10+

必要パッケージ（代表例）
- duckdb
- openai
- defusedxml

開発環境構築例
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate

2. pip を更新して必要パッケージをインストール
   - python -m pip install --upgrade pip
   - python -m pip install duckdb openai defusedxml

   （プロジェクトが pyproject.toml / setup.py を持つ場合は開発インストール）
   - pip install -e .

3. 環境変数を準備（.env をプロジェクトルートに配置 — 下記の例を参照）

自動 .env 読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml が存在するルート）から .env / .env.local を自動ロードします。
- 自動ロードを無効にするには環境変数を設定:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 環境変数（.env）例

必須・推奨のキー（例）

- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=your_kabu_station_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルトあり）
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb          # デフォルト
- SQLITE_PATH=data/monitoring.db           # デフォルト
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|WARNING|ERROR|CRITICAL

注意: Settings オブジェクト（kabusys.config.settings）は上記のキーを読み込み、必須キーが欠けていると ValueError を投げます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など一部）。

---

## 使い方（代表的な例）

以下は簡単な Python スニペット例です。実行前に .env の設定や DuckDB 接続ファイル準備を行ってください。

1) 日次 ETL を実行（市場データ取得 → 保存 → 品質チェック）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を使ってもよい
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（銘柄別）を計算して ai_scores に保存
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
print("written:", n_written)
```

3) 市場レジームを判定して market_regime に保存
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, date(2026, 3, 20), api_key="sk-...")
```

4) 監査ログ用 DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成される
```

5) カレンダー / 営業日ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print("is trading:", is_trading_day(conn, d))
print("next trading:", next_trading_day(conn, d))
```

注意点
- OpenAI 呼び出しは API キー（引数 or OPENAI_API_KEY 環境変数）が必要です。キー未設定時は ValueError を送出します。
- テストでは内部的な API 呼び出し関数（例: kabusys.ai.news_nlp._call_openai_api）を unittest.mock.patch で差し替えてモックできます。

---

## ディレクトリ構成

主要ファイル / モジュールのツリー（抜粋）
```
src/
  kabusys/
    __init__.py
    config.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    data/
      __init__.py
      jquants_client.py
      pipeline.py
      etl.py
      calendar_management.py
      news_collector.py
      quality.py
      stats.py
      audit.py
      pipeline.py
      etl.py
      # ... その他 data 関連モジュール
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    research/ (補助モジュール)
    # strategy, execution, monitoring パッケージは __all__ に定義されているが
    # この抜粋では省略されている場合があります
```

主要な公開 API は各サブパッケージの top-level に __all__ でエクスポートされています（例: kabusys.ai.score_news、kabusys.data.pipeline.run_daily_etl 等）。

---

## テスト・開発上のヒント

- API 呼び出し（J-Quants / OpenAI）は外部依存なのでユニットテストではモックしてください。モジュール内で API 呼び出しをラップしている関数（例: _call_openai_api, _request 等）をパッチすることが想定されています。
- DuckDB に対する SQL クエリはパラメータバインド（?）を使っています。テスト用に ":memory:" 接続や一時ファイルを使うと便利です。
- 自動 dotenv 読み込みはプロジェクトルート探索に基づきます。CI / テスト中に別の .env を使いたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてから明示的に環境変数を注入してください。

---

以上が README の概要です。詳しい API の引数や戻り値、SQL スキーマなどは各モジュールの docstring を参照してください。補足や特定 API の使用例（追加のコードスニペット）が必要であれば教えてください。