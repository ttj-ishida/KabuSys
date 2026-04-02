# KabuSys

日本株向けの自動売買 / データプラットフォーム向けユーティリティ群です。  
DuckDB をデータ層に用い、J-Quants API からのデータ ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログスキーマなどを提供します。

Version: 0.1.0

---

## 概要

KabuSys は以下のような目的で設計されたライブラリ群です。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に格納する ETL パイプライン
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント分析（銘柄別）およびマクロセンチメントとETF MA を組み合わせた市場レジーム判定
- 研究用：モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン・IC・統計サマリー
- 監査ログ（signal → order → execution）用の DuckDB スキーマ初期化ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上のポイント：
- ルックアヘッドバイアス防止のため内部で `date.today()`／`datetime.today()` をテスト実行時以外に直接参照しない実装方針
- API 呼び出しはリトライ・バックオフ・レート制限を実装
- ETL/保存は冪等性を重視（ON CONFLICT / DELETE→INSERT 等）

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系関数）
  - マーケットカレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS → raw_news / news_symbols）
  - データ品質チェック（check_missing_data / check_spike / run_all_checks）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースで市場レジームを判定し market_regime に書き込む
- research/
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量探索用）
- config
  - .env 自動読み込みと Settings（環境変数ラッパ）

---

## 必要条件 / 推奨

- Python 3.10 以上（PEP 604 Union 型記法 `X | Y` を使用）
- pip install でインストールする主要依存パッケージの例:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）

例:
```bash
python -m pip install duckdb openai defusedxml
```

プロジェクト環境によっては追加の依存が必要になる可能性があります（HTTP 標準ライブラリで足りる箇所も多いです）。

---

## 環境変数（主なもの）

設定は OS 環境変数またはプロジェクト直下の `.env` / `.env.local` から自動ロードされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化）。

必須（Settings._require で要求されるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- SLACK_BOT_TOKEN — Slack 通知用（プロジェクトで通知を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネルID
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注周り）

OpenAI 関連:
- OPENAI_API_KEY — AI モジュール（news_nlp / regime_detector）で使用（関数呼び出し時に api_key を引き渡すことも可能）

任意 / デフォルトあり:
- KABUSYS_ENV (development / paper_trading / live) — 動作モード（default: development）
- LOG_LEVEL (DEBUG/INFO/...) — ログレベル（default: INFO）
- DUCKDB_PATH — DuckDB のファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視用

※ `.env.example` を参考に `.env` を作成してください（本リポジトリに `*.example` がない場合は README の環境変数表を参照して手動で作成してください）。

---

## セットアップ手順（ローカルで試す場合の例）

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo-dir>
```

2. Python 環境の作成（推奨: venv）
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install duckdb openai defusedxml
```

3. 環境変数設定
- プロジェクトルートに `.env` を作成し、必要な環境変数を設定します。例:
```
JQUANTS_REFRESH_TOKEN=...
OPENAI_API_KEY=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
```
- 自動ロードは `kabusys.config` により .env/.env.local を読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. DuckDB ファイル用ディレクトリを作成（必要に応じて）
```bash
mkdir -p data
```

---

## 使い方（代表的な例）

Python REPL やスクリプトからモジュールを呼び出して利用できます。

- ETL（日次 ETL）を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを生成（OpenAI APIキーを環境変数に設定済みの想定）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API key は env または引数で指定可能
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

- RSS フィードを取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"])
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# schema が初期化された DuckDB 接続を返す
```

注意:
- AI 呼び出し部分は外部 API（OpenAI）を使用します。課金/鍵の管理に注意してください。
- J-Quants API 呼び出しはレート制限・認証が必要です。`JQUANTS_REFRESH_TOKEN` を用意してください。

---

## 主要 API（抜粋）

- kabusys.config.settings — 環境設定アクセサ（例: settings.jquants_refresh_token）
- kabusys.data.pipeline.run_daily_etl — 日次 ETL のエントリ
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.news_collector.fetch_rss — RSS フィード取得
- kabusys.ai.news_nlp.score_news — 銘柄別ニュースセンチメント計算 & ai_scores 書き込み
- kabusys.ai.regime_detector.score_regime — 市場レジーム判定 & market_regime 書き込み
- kabusys.research.* — 研究用ファクター計算・統計ユーティリティ
- kabusys.data.quality.run_all_checks — データ品質チェック
- kabusys.data.audit.init_audit_schema / init_audit_db — 監査ログスキーマ初期化

---

## ディレクトリ構成

プロジェクトの主要ファイル構成（抜粋）:

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
      - calendar_management.py
      - etl.py
      - pipeline.py
      - stats.py
      - quality.py
      - audit.py
      - jquants_client.py
      - news_collector.py
      - (その他: jquants_client に関連するユーティリティなど)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
    - monitoring/ (パッケージに含まれる想定の監視モジュール)
    - execution/ (発注系モジュール想定)
    - strategy/ (戦略層想定)

（実行時に使用する DBファイルやログは project-root/data/ に置かれる想定です。）

---

## 開発・テストに関するメモ

- 環境変数の自動ロードは `kabusys.config` が .env/.env.local をプロジェクトルートから探して自動読み込みします。テスト時に環境依存を避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI API 呼び出しや外部ネットワークアクセス部はテスト容易性を考慮して内部関数（例: `_call_openai_api` / `_urlopen`）をモック可能に設計しています。
- DuckDB はスキーマや SQL による一貫性を期待しているため、複数プロセスで同一ファイルを扱う運用には注意が必要です。

---

## 注意事項 / ライセンス等

- 実際の発注（ブローカー連携）や本番環境稼働時はリスク管理・十分なテストを行ってください。特に発注ロジック・監査ログまわりは二重発注や取り消し・例外ケースを想定した検証が必須です。
- 外部 API（OpenAI, J-Quants, RSS）利用時の利用規約・課金に注意してください。

---

この README では主要な使い方と構成をまとめました。さらに具体的な利用方法や導入手順（CI/CD、運用監視、Slack 通知など）について要件があれば追記します。