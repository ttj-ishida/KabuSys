# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（DuckDB）などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群を含みます。

- J-Quants API からの市場データ取得（株価・財務・取引カレンダー）
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集と OpenAI を用いたニュースセンチメント算出（銘柄別 ai_score）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- 研究用ユーティリティ（ファクター計算・将来リターン・IC・統計）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）を DuckDB に保存
- マーケットカレンダー管理（営業日判定など）
- 冪等性・フェイルセーフ・リトライ・レート制御等を重視した実装

設計上の特徴：
- ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を直接参照しない設計が多い）
- DuckDB を主要なローカル DB として使用、ETL は冪等に保存
- OpenAI 呼び出しのリトライ・JSON Mode 対応（gpt-4o-mini 想定）
- ネットワーク/API エラーに対するフォールバック（スコアは 0.0 など）

---

## 主な機能一覧

- data.jquants_client
  - J-Quants からの取得（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info）
  - DuckDB への保存（save_daily_quotes, save_financial_statements, save_market_calendar）
  - レートリミット・トークン自動リフレッシュ・リトライ実装
- data.pipeline
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の一括実行
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別実行
- data.quality
  - 欠損・重複・スパイク・日付不整合チェック（QualityIssue を返す）
- data.news_collector
  - RSS からニュースを取得・前処理・raw_news へ冪等保存（SSRF 対策、XML 安全パーサ）
- ai.news_nlp
  - calc_news_window, score_news: ニュースを銘柄別に集約して LLM でスコア算出、ai_scores へ保存
- ai.regime_detector
  - score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime を更新
- research
  - calc_momentum, calc_volatility, calc_value（ファクター群）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量解析）
- data.audit
  - 監査テーブル（signal_events / order_requests / executions）DDL と初期化ユーティリティ
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job

---

## 必要条件・依存関係

- Python 3.10 以上（型注釈の `|` を使用）
- 主な Python パッケージ
  - duckdb
  - openai
  - defusedxml
- そのほか標準ライブラリ（urllib 等）

（パッケージ管理はプロジェクトの setup/pyproject に合わせてください。pipenv / poetry / virtualenv 推奨）

---

## セットアップ手順

1. リポジトリをクローンし Python 仮想環境を作成
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 例:
     - pip install duckdb openai defusedxml

   （実際は pyproject.toml / requirements.txt があればそちらを使用してください）

3. 環境変数を設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知を使う場合
     - KABU_API_PASSWORD — kabuステーション API を使う場合
     - OPENAI_API_KEY — ニュース NLP / レジーム判定を実行する場合
   - デフォルト例（.env）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO

4. DuckDB ファイルやディレクトリ作成
   - settings.duckdb_path のデフォルトは `data/kabusys.duckdb`。必要に応じてディレクトリを作成してください。

---

## 使い方（代表的な例）

下記は Python REPL やスクリプト内での利用例です。DuckDB 接続は duckdb.connect() を使います。

- ETL（日次パイプライン）の実行例:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア生成（OpenAI API キーが必要）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("書き込み件数:", n_written)
```

- 市場レジーム判定:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB 初期化:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
```

- ファクター計算（研究用）:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026,3,20))
```

---

## 環境変数の自動読み込みについて

- パッケージ起動時にプロジェクトルート（.git または pyproject.toml を基準）を自動検出し、`.env` → `.env.local` の順で読み込みます。
- OS 環境変数は上書きされません（.env.local は override=True ですが OS 環境変数は protected）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 注意点 / 設計上の挙動

- Look-ahead バイアス対策: 多くの関数は内部で現在時刻に依存しない設計（target_date を明示的に渡す）です。バックテスト等では target_date を適切に扱ってください。
- 冪等性: ETL の保存処理は ON CONFLICT DO UPDATE を使用しているため、再実行しても重複を避けます。
- フェイルセーフ: OpenAI や外部 API が失敗した場合、多くの処理はゼロスコアやスキップで継続します（例: news/regime の macro_sentiment が計算できないときは 0.0 にフォールバック）。
- レート制限: J-Quants API は 120 req/min を想定し固定間隔スロットリングで制御されています。
- セキュリティ: news_collector は SSRF 対策や defusedxml による XML 攻撃対策を行っています。

---

## ディレクトリ構成

主要なファイル・モジュール構成（src/kabusys 配下）:

```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ __init__.py
│  ├─ audit.py
│  ├─ calendar_management.py
│  ├─ etl.py
│  ├─ jquants_client.py
│  ├─ news_collector.py
│  ├─ pipeline.py
│  ├─ quality.py
│  └─ stats.py
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
└─ (その他: strategy/ execution/ monitoring 等は __all__ に定義)
```

各モジュールの役割は上記「主な機能一覧」を参照してください。

---

## 開発・貢献

- テストを書き、OpenAI / 外部 API 呼び出し部分はモックで差し替えてください（モジュール内で _call_openai_api をパッチ可能に設計）。
- 自動環境読み込みはテスト時に邪魔になる場合があるため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用してください。

---

ご要望があれば、README に以下を追記できます：
- 例の .env.example（テンプレート）
- 詳しい API の使用例（J-Quants API のパラメータやレスポンス例）
- CI / テストのセットアップ手順
- ライセンス表記

必要であれば指示ください。