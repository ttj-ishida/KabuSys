# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、研究用ファクター計算、監査ログ、マーケットカレンダー管理、監視／実行に関するユーティリティ群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムを構成するための基盤ライブラリ群です。主に以下を目的としています。

- J-Quants API から株価・財務・カレンダーなどのデータを差分取得し、DuckDB に保存する ETL
- RSS ベースのニュース収集と OpenAI を用いた銘柄別・マクロセンチメントのスコアリング
- 研究用のファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution）のためのスキーマ初期化・DB ハンドリング
- マーケットカレンダー管理（営業日判定、next/prev trading day など）
- 環境設定の集中管理（.env 自動読み込み等）

設計上の注力点は「ルックアヘッドバイアスの排除」「冪等性」「API呼び出しの頑健性（リトライ/バックオフ）」「テストしやすさ」です。

---

## 主な機能一覧

- data
  - ETL: 日次 ETL パイプライン（run_daily_etl）で prices / financials / calendar を差分取得・保存
  - J-Quants クライアント（fetch/save 各種）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - ニュース収集（RSS を安全に取得し raw_news に保存）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP：銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に保存（score_news）
  - レジーム検出：ETF（1321）200日MA乖離とマクロニュースを合成して市場レジーム判定（score_regime）
- research
  - ファクター計算：calc_momentum / calc_value / calc_volatility
  - 特徴量探索ツール：将来リターン計算 / IC / 統計サマリー等
- config
  - 環境変数管理（.env 自動読み込み、必須項目取得ヘルパー settings）

---

## 必要条件

- Python 3.9+
- 推奨パッケージ（最低限、実行に必要なもの）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）

（プロジェクト固有の追加依存関係やバージョンは requirements.txt を用意してください）

---

## セットアップ手順

1. ソースを取得（例）
   - git clone <repo-url>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - あるいはプロジェクトで requirements.txt があれば: pip install -r requirements.txt
4. パッケージをインストール（編集可能モード）
   - pip install -e .
5. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を作成すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   - 必須の環境変数例は次節参照

---

## 環境変数（例）

以下はコード内で参照される代表的な環境変数です。プロジェクトルートに `.env` を作成してください。

必須（ValueError を出すもの）:
- JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
- SLACK_BOT_TOKEN=<your_slack_bot_token>
- SLACK_CHANNEL_ID=<your_slack_channel_id>
- KABU_API_PASSWORD=<kabu_api_password>

オプション（デフォルトあり）:
- KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
- LOG_LEVEL=INFO|DEBUG|...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- OPENAI_API_KEY=<your_openai_api_key>  （ai.score_news / ai.score_regime で参照）

例 `.env`（最小）:
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=yourpassword

注意: .env 読み込みはプロジェクトルート（.git または pyproject.toml）を起点に自動検出します。自動ロードを抑止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要ユースケース）

以下は Python から直接利用する例です。各例は簡潔化しています。

- DuckDB 接続の作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # path は settings.duckdb_path で指定可
```

- 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメントを取得して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY は環境変数か api_key 引数で指定
print(f"scored {n_written} codes")
```

- 市場レジーム判定（1321 を利用）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))  # OpenAI キーは env または api_key 引数で指定
```

- 監査ログDBを初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn に対して監査テーブルが作成されます
```

- J-Quants の生データ取得（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を参照して取得
records = fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,3,31))
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

- データ品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

詳しい引数仕様・挙動は各モジュールの docstring を参照してください（ルックアヘッドバイアス回避のため内部で date.today()/datetime.today() を参照しない等の設計方針があります）。

---

## 注意事項 / 運用上のポイント

- OpenAI API 呼び出しはリトライやフェイルセーフロジックを持ちますが、コストとレート制限を意識してください。
- ETL は差分更新を行います。初回は大量のデータ取得が発生します（_MIN_DATA_DATE からのバックフィル）。
- DuckDB の executemany に空リストを渡せないなどの実装制約に注意（コード内で適切にハンドル済み）。
- カレンダー情報がない場合、曜日ベースのフォールバックを行います。JPX カレンダーは ETL で定期的に取得してください。
- .env 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 主要モジュールと責務（簡易リファレンス）

- kabusys.config
  - Settings: 環境変数経由の設定取得（必須項目を検証）
  - 自動でプロジェクトルートの .env / .env.local を読み込む（無効化可能）
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - 内部的に rate limiter / retry / token refresh を実装
- kabusys.data.pipeline
  - run_daily_etl: ETL パイプラインのエントリポイント（ETLResult を返す）
  - run_prices_etl/run_financials_etl/run_calendar_etl: 個別 ETL
- kabusys.data.news_collector
  - RSS 取得と前処理（SSRF 対策、サイズ制限、トラッキング除去、記事ID生成）
- kabusys.data.quality
  - 各種データ品質チェック（欠損・重複・スパイク・日付不整合）
- kabusys.data.calendar_management
  - market_calendar 管理と営業日判定ロジック
- kabusys.data.audit
  - 監査用スキーマ定義・初期化（signal_events / order_requests / executions）
- kabusys.ai.news_nlp
  - score_news: 銘柄別ニュースをまとめて OpenAI に送りセンチメントを ai_scores に保存
- kabusys.ai.regime_detector
  - score_regime: ETF 1321 の MA200 乖離とマクロニュースを合成して market_regime に保存
- kabusys.research.*
  - ファクター計算・特徴量探索・IC・統計サマリー

---

## ディレクトリ構成

（抜粋。実際のリポジトリに合わせてください）

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
      news_collector.py
      calendar_management.py
      quality.py
      stats.py
      audit.py
      audit.py
      etl.py
      pipeline.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    research/
    monitoring/   (README の冒頭 __all__ に含まれる可能性のあるモジュール)
    execution/    (発注実行関連のモジュール、存在する場合)
    strategy/     (戦略モデル関連のモジュール、存在する場合)
    data/         (上記。データ関連ユーティリティ群)

ファイルごとの役割は上記「主要モジュールと責務」を参照してください。

---

## 貢献 / テスト

- ユニットテストや統合テストを追加する場合、外部 API 呼び出し（OpenAI / J-Quants / ネットワーク）はモック化してテストしてください。既存コードはモック差し替えを想定した設計になっています（例えば _call_openai_api の差し替え、news_collector._urlopen の差し替え等）。
- .env を使うため、テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効にすると安定します。

---

README の内容はコード内の docstring を元にまとめています。詳細な使用方法やパラメータの挙動は各モジュールの docstring を確認してください。質問や追加したい項目があれば教えてください。