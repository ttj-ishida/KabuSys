# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログなどの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／リサーチ基盤のためのライブラリ群です。主に次を目的とします。

- J-Quants API からの株価・財務・マーケットカレンダー等の差分取得と DuckDB への永続化（ETL）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース収集（RSS）と LLM による銘柄別センチメント算出（ai_score）
- マクロニュース＋テクニカル指標（ETF MA乖離）を組み合わせた市場レジーム判定
- ファクター計算・統計ユーティリティ（モメンタム、ボラティリティ、バリュー等）
- 監査（audit）テーブルによるシグナル→発注→約定のトレーサビリティ

設計上の特徴：
- DuckDB を中心とした SQL ベースの高速処理
- Look-ahead バイアス回避（内部で date.today() を不用意に参照しない等）
- API 呼び出しに対するリトライ・レート制御・フェイルセーフロジック
- 冪等（idempotent）書き込み（ON CONFLICT / DELETE→INSERT 等）

---

## 主な機能一覧

- data/
  - ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント: fetch / save 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar 等）
  - カレンダー管理: is_trading_day, next_trading_day, get_trading_days, calendar_update_job
  - ニュース収集: RSS 取得・正規化・raw_news への保存ロジック（SSRF 対策、トラッキング除去）
  - 品質チェック: 欠損、重複、スパイク、日付不整合の検出（run_all_checks）
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF(1321)のMA乖離 + マクロニュースセンチメントで市場レジーム（bull/neutral/bear）判定・保存
- research/
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量解析: calc_forward_returns, calc_ic, factor_summary, rank
- config.py
  - .env / 環境変数読み込み補助、Settings クラス（各種キー／パス／フラグ）を提供

---

## 必要条件（概略）

- Python 3.10+
- パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS, OpenAI）

pip 用の正確な requirements.txt はプロジェクトに合わせて用意してください。上記パッケージは最低限必要です。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します（例: venv）。
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストールします（例）:
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を推奨）

3. パッケージを開発モードでインストール（任意）:
   - pip install -e .

4. データディレクトリを作成（Defaults）:
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（config.py の自動ロード）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。

必須環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN
  - J-Quants の refresh token（get_id_token に使用）
- KABU_API_PASSWORD
  - kabu ステーション API パスワード（発注周りで利用）
- OPENAI_API_KEY
  - OpenAI API キー（AI モジュール使用時）
オプション／デフォルト値（代表例）:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_FILL_MODE — paper trading のフィルモード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db

例 (`.env`):
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（代表的な例）

以下は Python からライブラリを利用する簡単な例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作成し ETL を走らせる

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は .env の DUCKDB_PATH を参照（デフォルト data/kabusys.duckdb）
conn = duckdb.connect(str(settings.duckdb_path))

# ETL 実行（target_date を指定、省略時は today）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores テーブルへ書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数にある前提
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジームをスコアリングして market_regime テーブルへ保存

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DuckDB を初期化する（別 DB に分離して使う例）

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
# conn_audit を使って以後の監査ログを書き込める
```

- ニュース RSS を取得する（news_collector.fetch_rss を単体で使う）

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles[:5]:
    print(a["datetime"], a["title"])
```

注意:
- OpenAI 呼び出しや J-Quants API はネットワーク／課金が関係するので、キーやレートに注意してください。
- 各関数はログ出力・例外処理を行います。運用時は適切にログレベルを設定してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
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
  - pipeline.py  (ETLResult の定義と run_daily_etl 等)
  - etl.py (ETL の公開エントリ)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/（他モジュール）
- ai/（上記）
- その他（strategy / execution / monitoring のプレースホルダが __all__ に存在するが、詳細はプロジェクト内）

上記は本 README に含まれるコードベースの抜粋に基づく主要モジュール一覧です。

---

## 運用時の注意点 / ヒント

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を基準に行われます。テスト時や CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを抑止できます。
- OpenAI の呼び出しは JSON mode を利用し、レスポンスのパース失敗や API エラー時はフェイルセーフ（スコアを 0 にする等）で継続する設計です。ただし、API 料金・レート制限に注意してください。
- J-Quants API 呼び出しはレート制御（120 req/min）・リトライ・401 の自動トークンリフレッシュに対応しています。JQUANTS_REFRESH_TOKEN は必須です。
- DuckDB のバージョンや挙動差に依存する箇所（executemany の空リストなど）に注意して運用してください。
- 監査テーブル（audit）は UTC のタイムスタンプを前提としています。DB の TimeZone を UTC に固定する処理が含まれます。

---

## ライセンス / コントリビューション

本 README はコードベースの説明用に生成されています。実際のライセンス・貢献フローについてはリポジトリの LICENSE / CONTRIBUTING を参照してください。

---

何か追加で README に追記したい項目（例: CI 設定、テストの実行方法、requirements.txt の具体的な内容、CLI コマンド例など）があれば教えてください。必要に応じてサンプル .env.example も作成します。