# KabuSys

日本株向けのデータパイプライン＆自動売買支援ライブラリ（DuckDB ベース）。  
データ収集（J-Quants / RSS）、品質チェック、特徴量（ファクター）計算、ニュースNLP / LLM を用いたスコアリング、監査ログスキーマなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム設計に必要な以下の機能をライブラリとして提供します。

- J-Quants API を用いた株価・財務・上場情報・市場カレンダーの差分 ETL（DuckDB 保存）
- RSS ベースのニュース収集と前処理（raw_news / news_symbols）
- OpenAI を利用したニュースセンチメント・マクロセンチメント評価（JSON Mode を利用）
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査用テーブル群（signal_events / order_requests / executions）と初期化ユーティリティ

設計上の重要点:
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を直接参照しない）
- 冪等性（DB 書き込みは ON CONFLICT/DELETE→INSERT 等で保護）
- フェイルセーフ（API 失敗時は処理継続、ログ出力してスコアは中立化）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API 呼び出し・保存ロジック（レートリミット・リトライ・トークンリフレッシュ）
  - pipeline: 日次 ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news への保存補助
  - quality: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 監査ログテーブル作成・初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに LLM でスコア化し ai_scores へ格納
  - regime_detector.score_regime: MA200 とマクロ LLM スコアを合成して market_regime に保存
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config:
  - Settings クラス経由で環境変数を集約

---

## 要件（推奨）

- Python 3.10+
- 必要なパッケージ（主な import から）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の依存がある場合は setup や pyproject を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / ソース配置
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください）
4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（下記を参照）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数 / 設定

Settings（kabusys.config.settings）が参照する主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（get_id_token のため）。
- OPENAI_API_KEY (必須 for LLM を使う処理)  
  OpenAI API key。score_news / score_regime にも直接 api_key 引数で渡せます。
- KABU_API_PASSWORD  
  kabuステーション API 用パスワード（必要に応じて）。
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID  
  通知用（必要に応じて）。
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)  
  DuckDB ファイルパス。
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)  
  SQLite（監視用途等）パス。
- KABUSYS_ENV (任意, デフォルト: development)  
  有効値: development / paper_trading / live
- LOG_LEVEL (任意, デフォルト: INFO)

自動 .env ロードの優先順位:
- OS 環境変数 > .env.local > .env  
プロジェクトルートは __file__ の親ディレクトリを上方検索して `.git` か `pyproject.toml` を検出して決定します。見つからない場合は自動ロードをスキップします。

---

## 使い方（代表的な例）

以下は Python スクリプトからの代表的な呼び出し例です。

- DuckDB 接続の作成（推奨: settings.duckdb_path を利用）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI を使用）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定する
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("written:", n_written)
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB 初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn を使用して監査テーブルにアクセス
```

- ファクター計算例
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, date(2026,3,20))
```

注意点:
- LLM 呼び出し (score_news / score_regime) は OpenAI API のキーが必要です。api_key 引数で明示的に与えるか、環境変数 OPENAI_API_KEY を設定してください。
- ETL / 保存処理は DuckDB テーブルのスキーマが期待通りに作成されていることを前提とします（スキーマ初期化ロジックは別途用意されている想定）。

---

## 代表的な API（関数）一覧

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成

主要ファイルを抜粋した構成（src/kabusys 以下）:

- kabusys/
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
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research, execution, monitoring など（パッケージ外にあるモジュールがあれば同階層に展開）

各モジュールは README で示した機能ごとに責務が分割されています。詳細は各ファイルの docstring を参照してください。

---

## 開発・テスト時のヒント

- 自動 .env 読み込みを無効化（テストで明示的に環境を制御したい場合）:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しなど外部 API を伴う関数は、コード内で明示的に _call_openai_api の差し替えを想定している箇所があります（unittest.mock.patch 等でモック可能）。
- DuckDB を使ったローカル開発は高速で簡単に始められます（:memory: も使用可能）。

---

もし README の具体的な実行例、サンプル .env.example、あるいはプロジェクト用の pyproject/requirements を作成する必要があれば、そのテンプレートを作成します。どの例が欲しいか教えてください。