# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ（KabuSys）。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）による銘柄センチメント算出、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。

---

目次
- プロジェクト概要
- 主な機能一覧
- 動作要件・インストール
- 環境変数 / 設定
- セットアップ手順
- 使い方（簡単なコード例）
- ディレクトリ構成（主要ファイル説明）
- 補足（自動 .env 読み込み、トラブルシュート）

---

## プロジェクト概要

KabuSys は日本株に特化したデータ基盤とリサーチ／自動売買補助ロジック群をまとめた Python パッケージです。  
主な目的は以下：

- J-Quants API からの差分 ETL（株価日足・財務・JPX カレンダー）
- RSS を用いたニュース収集と前処理（SSRF 対策、サイズ制限、トラッキング除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（銘柄単位）とマクロセンチメント（市場レジーム）
- DuckDB を用いた効率的なデータ処理・保存
- 研究（ファクター計算・前方リターン・IC 計算・Z スコア正規化）
- 監査テーブル（signal / order_request / executions）によるトレーサビリティ

設計上の特徴として、ルックアヘッドバイアス防止、堅牢なリトライ/バックオフ、冪等処理、外部接続の安全対策（SSRF や XML パースの防御）を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存・トークン自動リフレッシュ・レートリミット）
  - カレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - ニュース収集（RSS フェッチ・前処理、安全対策）
  - データ品質チェック（欠損・重複・スパイク・未来日付等）
  - 監査ログ初期化（監査スキーマ作成 / init_audit_db）
  - 統計ユーティリティ（Z スコア正規化）
- ai
  - ニュース NLP（銘柄ごとのセンチメント算出: score_news）
  - 市場レジーム判定（ETF 1321 の MA + マクロ記事の LLM 評価の合成: score_regime）
- research
  - ファクター計算（momentum / value / volatility）
  - 特徴量解析（forward returns / IC / summary / rank）
- config
  - 環境変数読み込み（.env 自動読み込み、必須値チェック：settings オブジェクト）

---

## 動作要件・インストール

前提（例）
- Python 3.10+
- duckdb
- openai (OpenAI の Python SDK)
- defusedxml
- （標準ライブラリ以外の依存は setup.cfg / pyproject.toml に記載されている想定）

開発環境に導入する例:

```bash
# 仮想環境（推奨）
python -m venv .venv
source .venv/bin/activate

# パッケージのインストール（プロジェクトルートで）
pip install -e .
# もしくは必要ライブラリだけを直接:
pip install duckdb openai defusedxml
```

※ pyproject.toml / setup.cfg がある想定で pip install -e . が推奨です。

---

## 環境変数 / 設定

settings（kabusys.config.Settings）で参照する主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（get_id_token で ID トークンを取得）。
- OPENAI_API_KEY (OpenAI 呼び出しに使用。score_news / score_regime に渡す api_key を省略した場合参照)
- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

自動で .env / .env.local をプロジェクトルートから読み込みます（プロジェクトルートは .git または pyproject.toml を基準に検出）。  
読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 .env:

```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成：
   - git clone ...
   - python -m venv .venv && source .venv/bin/activate

2. パッケージをインストール：
   - pip install -e .

3. 環境変数を用意：
   - プロジェクトルートに `.env` を作成（上記参照）。自動ロードにより settings が使えるようになります。

4. DuckDB ファイルとディレクトリ準備（settings.duckdb_path の親ディレクトリを作る）：
   - settings.duckdb_path はデフォルトで data/kabusys.duckdb（必要なディレクトリは自動作成することを推奨）

5. 監査用 DB 初期化（必要に応じて）：
   - Python REPL またはスクリプトで init_audit_db を実行（次節参照）

---

## 使い方（コード例）

以下は代表的な利用例です。各関数は duckdb.DuckDBPyConnection を受け取るため、まず接続を作成します。

- 共通準備

```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 個別 ETL（株価のみ）

```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
print(f"fetched={fetched}, saved={saved}")
```

- ニュースセンチメント（OpenAI API キーは環境変数か api_key 引数で指定）

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を参照
print(f"scored {count} codes")
```

- 市場レジーム判定

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)  # returns 1 on success
```

- 監査ログスキーマ初期化（別 DB に作る例）

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査ログを書き始められます
```

- RSS フェッチ（ニュース収集）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- OpenAI 呼び出しはコストと API レート制限があるため、ローカルでの実行はキーの管理に気を付けてください。
- score_news / score_regime は API 呼び出しに失敗した場合にもフェイルセーフ（0 や空スキップ）で継続する設計です。

---

## ディレクトリ構成（主要ファイル・概要）

ルート: src/kabusys 以下に主要モジュールが配置されています。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み（.env / .env.local）、settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news(conn, target_date, api_key=None): 銘柄別ニュースの LLM センチメント算出
    - regime_detector.py
      - score_regime(conn, target_date, api_key=None): マクロ + MA を合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API の取得関数と DuckDB への保存（fetch_* / save_*）
      - get_id_token(refresh_token) によるトークン取得
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
      - ETLResult dataclass
    - news_collector.py
      - fetch_rss / URL 正規化 / テキスト前処理 / SSRF 対策 等
    - calendar_management.py
      - market_calendar の更新・営業日判定や next/prev_trading_day
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・未来日付）
    - audit.py
      - 監査テーブル DDL / init_audit_schema / init_audit_db
    - stats.py
      - zscore_normalize
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_value / calc_volatility
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank

（上記以外にも execution / strategy / monitoring 等のエクスポートが想定されていますが、今回のコードでは主に data / ai / research に注力しています）

---

## 補足・運用メモ

- .env 自動読み込み  
  パッケージインポート時にプロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を順に読み込みます。OS 環境変数が優先され、.env.local は .env を上書きします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DB 書き込みの冪等性  
  jquants_client.save_* 関数や ETL は ON CONFLICT DO UPDATE を使って冪等保存する設計です。部分失敗時のデータ保護にも注意が払われています。

- LLM 呼び出しの挙動  
  OpenAI への呼び出しはリトライ、JSON Mode（厳密 JSON 出力）を利用し、失敗時は安全側にフォールバック（例：macro_sentiment=0.0、該当コードのスキップ）します。

- 時刻・タイムゾーン  
  監査用 TIMESTAMP は UTC に統一することを想定（init_audit_schema は conn.execute("SET TimeZone='UTC'") を実行します）。raw_news.datetime や ETL の fetched_at 等も UTC ベースで扱います。

---

もし README に追加したい「実行用スクリプト」「CI 設定」「デプロイ手順」「サンプルデータの初期ロードスクリプト」などがあれば、必要な想定を教えてください。README をそれに合わせて拡張します。