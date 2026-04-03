# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買補助ライブラリ群です。J-Quants / JPX / RSS / OpenAI（LLM）等からデータを取得・加工し、ETL・品質チェック・特徴量計算・AI スコアリング・監査ログ管理までをカバーします。

この README はコードベース（src/kabusys）を元に作成した概要・機能・セットアップ・使い方・ディレクトリ構成のドキュメントです。

---

## プロジェクト概要

主な目的：

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- ニュース収集（RSS）と OpenAI を用いた記事センチメント（銘柄別 ai_score）の自動計算
- ETF（1321）の 200 日移動平均乖離とマクロニュースセンチメントを合成した市場レジーム判定
- 監査ログ（シグナル → 発注 → 約定）のための監査テーブル定義と初期化ユーティリティ
- 研究（research）モジュール：ファクター計算、将来リターン、IC や統計ユーティリティ

設計上の特徴：

- ルックアヘッドバイアス防止（target_date を明示し、datetime.today() 依存を最小化）
- DuckDB を用いたローカルデータ保存（冪等保存、ON CONFLICT を使用）
- API 呼び出しはリトライ／バックオフ・レート制御を実装
- フェイルセーフ：API 失敗時は適切にフォールバックして処理継続

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch/save 系）
  - market calendar 管理（is_trading_day, next_trading_day, get_trading_days 等）
  - news_collector（RSS 取得・正規化・保存）
  - quality（欠損・スパイク・重複・日付不整合チェック）
  - audit（監査テーブルの初期化・DB 初期化ユーティリティ）
  - stats（zscore_normalize）
- ai/
  - news_nlp.score_news: 記事を集約して OpenAI で銘柄別センチメントを算出し ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA 乖離とマクロニュースセンチメントを合成して market_regime に保存
- research/
  - factor_research (calc_momentum / calc_value / calc_volatility)
  - feature_exploration (calc_forward_returns / calc_ic / factor_summary / rank)
- config
  - Settings: .env の自動ロード（プロジェクトルート検出）と環境変数ラッパー

---

## セットアップ手順

前提

- Python 3.10+（一部 typing 機能を使用）
- duckdb, openai, defusedxml 等の依存ライブラリ

1. リポジトリをクローン・チェックアウト（プロジェクトルートに pyproject.toml または .git があることを想定）:

   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化（推奨）:

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell)

3. 依存パッケージをインストール（必要に応じて requirements.txt を用意してください）。代表的な依存：

   pip install duckdb openai defusedxml

   （他に logging 用やテスト用の依存がある場合はプロジェクトの requirements を参照してください）

4. 環境変数の設定

   プロジェクトルートに `.env` または `.env.local` を配置すると自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。

   主な環境変数（最低限必要なもの）:

   - JQUANTS_REFRESH_TOKEN - J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD - kabuステーション API パスワード（必須/発注連携時）
   - OPENAI_API_KEY - OpenAI API キー（ai.score_news / regime_detector で使用）
   - DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH - 監視/モニタリング用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV - 開発環境: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL - ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

   例（.env）:

   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
   DUCKDB_PATH=./data/kabusys.duckdb
   KABU_API_PASSWORD=your_kabu_pass
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

5. （任意）データディレクトリを作成:

   mkdir -p data

---

## 使い方（簡単なコード例）

以下は Python スクリプトや REPL から呼び出す代表的な使い方例です。

- DuckDB 接続を作って日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# DuckDB ファイルパスは settings.duckdb_path に従う場合:
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

# ETL を実行（target_date を指定しない場合は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を用いたニューススコアリング（銘柄別 ai_scores への書き込み）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
num_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print("written:", num_written)
```

- 市場レジーム判定（market_regime へ書き込み）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB 初期化

```python
from kabusys.data.audit import init_audit_db

# ファイルを指定して監査DBを作成・初期化
conn_audit = init_audit_db("data/audit.duckdb")
```

- RSS フィード取得（news_collector のユーティリティ）

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

注意点：

- AI 関連の関数（score_news / score_regime）は OpenAI API キーが必要です。api_key 引数で指定するか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API を使う処理（ETL 等）は JQUANTS_REFRESH_TOKEN が必須です。

---

## よく使う内部 API（概要）

- kabusys.data.pipeline.run_daily_etl(conn, target_date, id_token=None, ...)
  - 日次 ETL（calendar, prices, financials, 品質チェック）
  - 戻り値: ETLResult（to_dict で詳細を取得可）

- kabusys.data.jquants_client.*
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - save_daily_quotes(conn, records)
  - fetch_financial_statements(...)
  - save_financial_statements(conn, records)
  - fetch_market_calendar(...)
  - save_market_calendar(conn, records)

- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - raw_news と news_symbols を読み、ai_scores に銘柄別スコアを保存

- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 乖離 + マクロニュースセンチメントを合成し market_regime を更新

- kabusys.data.quality.run_all_checks(conn, ...)
  - データ品質チェックを実行し QualityIssue のリストを返す

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) - J-Quants のリフレッシュトークン
- OPENAI_API_KEY (AI 機能を使う場合必須)
- KABU_API_PASSWORD (kabuAPI連携で使用)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB)
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/...)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py  -- 環境変数 / Settings
- ai/
  - __init__.py
  - news_nlp.py        -- ニュース NLP（score_news）
  - regime_detector.py -- 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py  -- 市場カレンダー管理（is_trading_day 等）
  - etl.py                  -- ETLResult の公開
  - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
  - stats.py                -- zscore_normalize 等
  - quality.py              -- データ品質チェック
  - audit.py                -- 監査ログ（DDL / init_audit_db）
  - jquants_client.py       -- J-Quants API client & save_*
  - news_collector.py       -- RSS 取得・正規化・保存
- research/
  - __init__.py
  - factor_research.py      -- calc_momentum / calc_value / calc_volatility
  - feature_exploration.py  -- calc_forward_returns / calc_ic / factor_summary / rank
- research/... (補助モジュール)
- その他: strategy/ execution/ monitoring のエクスポート（パッケージ化時に利用）

---

## 開発上の注意 / ヒント

- DuckDB の executemany に空リストを渡すと問題が起きる箇所があるため、コード中では空チェックが多く入っています。自作コードから呼ぶ際は空パラメータの扱いに注意してください。
- AI 呼び出し（OpenAI）にはリトライや JSON パース安全化が入っていますが、プロンプトや出力フォーマットが変わるとパースエラーになるので、実運用ではログ監視を強化してください。
- .env の自動読み込みはプロジェクトルートの検出に依存します。パッケージ配布後やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して明示的に設定することを推奨します。
- 監査スキーマ（audit.init_audit_schema）はトランザクションオプションがあり、既にトランザクション中の接続に対しては注意が必要です（DuckDB のトランザクション仕様を参照）。

---

必要であれば README にサンプルの .env.example やより詳細な CLI / サービス起動手順、Docker / systemd ユニット例、テストの実行方法などを追加できます。どの情報を優先して追記しましょうか？