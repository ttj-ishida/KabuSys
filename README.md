# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP スコアリング、ファクター計算、監査ログ（発注トレース）、マーケットカレンダー管理、そして市場レジーム判定などの機能を備え、研究（research）・データ処理（data）・AI（news/LLM）・監視/実行の各レイヤーを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような要件を念頭に設計されています。

- バックテストでのルックアヘッドバイアスを避ける（datetime.now()/today を内部で直接参照しない設計）
- DuckDB をデータ基盤として利用し、ETL は冪等（ON CONFLICT）で安全に実行
- J-Quants API から差分取得・ページネーション対応・リトライ・レートリミット遵守
- ニュース収集（RSS）→ NLP（OpenAI）による銘柄別スコアリング（ai_scores）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメントの合成）
- 監査ログ（signal → order_request → execution）のスキーマ・初期化機能
- データ品質チェック（欠損・重複・スパイク・日付不整合）

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save の各種関数）
  - ニュース収集（RSS → raw_news、SSRF 対策・サイズ上限・トラッキング除去）
  - market_calendar の管理 & 営業日判定ユーティリティ（is_trading_day, next_trading_day など）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: ニュースを銘柄ごとに集約して LLM でスコア化）
  - 市場レジーム判定（score_regime: MA200 とマクロセンチメントの合成）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込み / 設定取得（Settings クラス）
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、無効化可）

---

## 必要な環境変数

最低限必要な環境変数（.envに設定する想定）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション等の接続パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — 通知先チャンネルID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に必要）
- DUCKDB_PATH — DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（省略時: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、省略時 development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、省略時 INFO）

設定は .env または環境変数で行います。パッケージ起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）から自動で `.env` と `.env.local` を読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env.example）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
SQLITE_PATH=~/kabusys/data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 環境を準備（3.10+ を推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 必要パッケージをインストール

   必要なパッケージ例（プロジェクトの pyproject.toml に依存しますが、主要な外部依存は以下）:

   ```
   pip install duckdb openai defusedxml
   ```

   （他に標準ライブラリ以外のパッケージがあれば pyproject.toml / requirements.txt を参照してください）

3. パッケージを開発モードでインストール（プロジェクトルートで）:

   ```
   pip install -e .
   ```

4. .env を作成して上記の環境変数を設定

   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` または `.env.local` を置くと自動読み込みされます。

---

## 使い方（基本例）

以下はライブラリの主要な関数をプログラムから利用する例です。コマンドラインのラッパーは提供されていないため、スクリプトや REPL から呼び出します。

事前準備: DuckDB 接続の取得（例: data/db.duckdb を使用）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime
from kabusys.data.audit import init_audit_db

# DuckDB 接続
conn = duckdb.connect("data/kabusys.duckdb")

# 日次ETL を実行（デフォルト: today）
res = run_daily_etl(conn)
print(res.to_dict())

# ニューススコアリング（target_date に対して前日15:00～当日08:30のウィンドウを処理）
n = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI キーは環境変数 OPENAI_API_KEY を利用
print(f"scored {n} codes")

# 市場レジーム算出
score_regime(conn, target_date=date(2026, 3, 20))

# 監査ログ用の専用 DB 初期化
audit_conn = init_audit_db("data/audit.duckdb")
```

注意点:
- score_news / score_regime を実行するには OpenAI API キー（環境変数 OPENAI_API_KEY）が必要です（引数で明示的に渡すことも可）。
- ETL 処理は J-Quants API へのネットワークアクセスを伴います。J-Quants のトークンが必須です。

---

## 主要 API（抜粋）

- data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
  - run_prices_etl(conn, target_date, id_token=None, ...)
  - run_financials_etl(...)
  - run_calendar_etl(...)

- data.jquants_client
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- data.news_collector
  - fetch_rss(url, source, timeout=30)

- data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(path)

- ai.news_nlp
  - score_news(conn, target_date, api_key=None) -> int (書き込み件数)

- ai.regime_detector
  - score_regime(conn, target_date, api_key=None) -> int

- research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons=None)
  - calc_ic(factor_records, forward_records, factor_col, return_col)
  - factor_summary(records, columns)
  - rank(values)

- config
  - settings: Settings インスタンス（settings.jquants_refresh_token 等のプロパティ経由で取得）

---

## .env 自動読み込みについて

- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` → `.env.local` の順で読み込みます。
- OS 環境変数を上書きしないのがデフォルト（`.env.local` は override=True で上書き可能）。
- 自動読み込みを無効化するには環境変数を設定:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成（主要ファイル）

以下はパッケージの主要なファイル・モジュール構成です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py        # ニュースセンチメントスコアリング（LLM 呼び出し）
    - regime_detector.py # 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（fetch / save / auth / rate limit）
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - etl.py                # ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py     # RSS 取得・前処理・保存ロジック（SSRF 対策 etc.）
    - calendar_management.py# 市場カレンダー管理（is_trading_day 等）
    - quality.py            # データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py              # 汎用統計ユーティリティ（zscore_normalize）
    - audit.py              # 監査ログ（スキーマ作成・初期化）
    - pipeline.py           # ETL の実行ロジック（重複記載は上部参照）
  - research/
    - __init__.py
    - factor_research.py    # ファクター計算（momentum/value/volatility）
    - feature_exploration.py# 将来リターン、IC、統計サマリ、rank

（上記は抜粋です。詳細はソースコードを参照してください。）

---

## 運用上の注意

- OpenAI / J-Quants API の呼び出しにはそれぞれ料金・レート制限があるため、本番運用時はキーや呼び出し頻度を管理してください。
- ETL は idempotent（冪等）設計ですが、DB のバックアップ/スナップショット運用を推奨します。
- ニュース取得では外部 URL を開くため、ネットワークセキュリティ・SSRF 対策が組み込まれていますが、運用環境のプロキシやファイアウォール設定によって挙動が変わる可能性があります。
- KABUSYS_ENV による挙動切替（development / paper_trading / live）を適切に設定してください（ライブ環境での注文発行などは特に慎重に）。

---

## 貢献・開発

- ソースは src/kabusys 配下に配置されています。開発時は仮想環境で `pip install -e .` を行い、ユニットテストや linters を追加して品質を維持してください。
- テストを書く際は config の自動 .env 読み込みを無効化するか、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してテスト用環境を用意してください。
- OpenAI API 呼び出しなど外部依存部分はモック化できるよう設計されています（モジュール内の呼び出し関数を unittest.mock.patch で差し替え可能）。

---

必要であれば README の英語版や、具体的な .env.example、簡易スクリプト（etl_runner.py や scoring_runner.py）テンプレートも作成します。どちらを希望しますか？