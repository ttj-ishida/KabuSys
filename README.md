# KabuSys

KabuSys は日本株のデータプラットフォーム、研究・ファクター計算、ニュース NLP、マーケットレジーム判定、ETL、監査ログなどを含む日本株自動売買システムのライブラリです。本 README はコードベース（src/kabusys）を対象に設計思想・使い方・セットアップ手順などを日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を提供します。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- ニュース収集・前処理モジュール（RSS 取得、テキスト正規化、SSRF 対策）
- OpenAI を使ったニュースセンチメントおよび市場レジーム判定（gpt-4o-mini の JSON Mode を利用）
- 研究用ユーティリティ（モメンタム・ボラティリティ・バリューなどのファクター計算、将来リターン、IC 計算、Zスコア正規化）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ用テーブル定義と初期化）
- 市場カレンダー管理（JPX カレンダーの取得・営業日判定）

設計上の注意点（重要）
- ルックアヘッドバイアス防止のため、モジュール内で datetime.today() / date.today() を不用意に参照しない実装方針が採られています。外部から target_date を渡して使う設計です。
- DuckDB をデータ格納先として想定。多くの関数は DuckDB の接続オブジェクトを引数に取り、SQL＋Pythonで処理を行います。
- OpenAI / J-Quants API 呼び出しはリトライやバックオフ、エラーハンドリングを備えています。

---

## 機能一覧（主要モジュール）

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 各設定値（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY など）をプロパティで取得
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御・ページネーション）
  - pipeline: 日次 ETL 実行（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news への保存ロジック
  - quality: データ品質チェック（欠損/スパイク/重複/日付不整合）
  - calendar_management: 営業日判定 / next/prev_trading_day / calendar_update_job
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを生成して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA 乖離とマクロニュースを合成して market_regime に保存
- kabusys.research
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提
- Python 3.10+（PEP 604 の union 表記（X | Y）を使用）
- Git, pip が使える環境

1. リポジトリをクローン
   - git clone <repo-url>
   - リポジトリルートに pyproject.toml / .git がある想定です（config モジュールがこれらでプロジェクトルートを検出します）。

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - 最低限の依存（例）:
     - pip install duckdb openai defusedxml
   - 開発時は他に linters 等を追加してください。
   - パッケージがプロジェクトとして組み立てられている場合:
     - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY (推奨) — OpenAI API キー（score_news / score_regime が使用）
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（必要に応じて）
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知に使用（任意）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE — paper_trading のフィルモード（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH — paper trading の SQLite パス（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH, KILL_FLAG_PATH, ...（監視用）
     - KABUSYS_ENV — development | paper_trading | live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL

   - .env の書式は export KEY=val や KEY="value" に対応し、コメント行やクォート・エスケープを考慮したパーサーが使われます。

---

## 使い方（簡単なコード例）

以下はライブラリを直接使う例です。いずれも DuckDB の接続オブジェクトを渡して使います（duckdb.connect）。

- 日次 ETL を実行して DuckDB にデータを取り込む

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ってニュースセンチメントを算出（score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数にセットしていれば api_key は省略可
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込み銘柄数:", n_written)
```

- 市場レジームを評価して保存（score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB を初期化

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済の DuckDB 接続
```

- 研究用ファクター計算例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は (date, code, mom_1m, mom_3m, mom_6m, ma200_dev) の dict リスト
```

- RSS をフェッチする（news_collector.fetch_rss）

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意点:
- OpenAI / J-Quants の呼び出しは API キー・トークンが必要です。環境変数で管理するか、関数引数で渡してください。
- 多くの関数は target_date を明示的に受け取ります（内部で現在時刻を参照しない設計）。

---

## ディレクトリ構成（抜粋）

以下はパッケージ内の主要ファイル構成（src/kabusys）です。実際のリポジトリでは他にドキュメント・テスト・CI ファイルが存在する可能性があります。

- src/
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
      - pipeline.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/ (参照のみ; ここには監視周りのコードが入る想定)
    - strategy/ (戦略実装用スペース)
    - execution/ (発注実行関連)
    - data/（上に示したDataモジュール群）

（上記はコードベースから抽出した主要ファイル群です。詳細はリポジトリを参照してください）

---

## 運用上の注意・ベストプラクティス

- API キー管理は .env / 環境変数で行い、ソース管理システムに API キーを含めないでください。
- ETL を定期実行する場合は run_daily_etl を cron / scheduler で呼び出してください。ETLResult をログ・監査に残すことを推奨します。
- OpenAI 呼び出しにはコストが発生するため、バッチ化や記事数上限（コード内で制御）を活用してください。
- news_collector は SSRF・XML Bomb 対策（defusedxml など）を実装していますが、未知のフィードを追加する際は事前検証を行ってください。
- DuckDB ファイルはバックアップを推奨します。特に監査ログは削除せず履歴保存を想定しています。

---

## 追加情報 / トラブルシュート

- 自動 .env 読み込みを無効化したい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- PAPER_FILL_MODE の有効値:
  - instant / partial / never / reject
- KABUSYS_ENV の有効値:
  - development / paper_trading / live
- ログレベル:
  - DEBUG / INFO / WARNING / ERROR / CRITICAL

---

この README はコードベースに含まれるドキュメント・docstring を元にまとめています。各モジュールの詳細な仕様や追加のユーティリティは該当ファイルの docstring や関数コメントを参照してください。質問や追加の使い方サンプルが必要であれば教えてください。