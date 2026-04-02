# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）。  
ETL（J-Quants → DuckDB）・ニュース収集/センチメント（OpenAI）・ファクター計算・監査ログ管理など、投資システムで必要な基盤機能を提供します。

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質管理・特徴量生成・AI ベースのニューススコアリング・市場レジーム判定・取引監査ログ管理を行うためのライブラリ群です。主に以下を目的としています：

- J-Quants API から株価・財務・カレンダー等の差分取得（ETL）
- DuckDB を用いたデータ保管と効率的な集計クエリ
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント/マクロ判定
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- 監査ログ（signal → order_request → executions）のスキーマと初期化ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants クライアント（fetch / save / id_token 管理、rate limit、リトライ）
  - カレンダー管理（is_trading_day / next_trading_day / get_trading_days）
  - ニュース収集（fetch_rss、前処理、SSRF 対策）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news：銘柄ごとのセンチメントを ai_scores に書き込み）
  - 市場レジーム判定（score_regime：ETF 1321 の MA200 とマクロニュースを合成）
- research/
  - ファクター計算（calc_momentum、calc_value、calc_volatility）
  - 特徴量探索（calc_forward_returns、calc_ic、factor_summary、rank）
- config.py
  - .env / .env.local 自動ロード（プロジェクトルート検出）と Settings オブジェクト（環境変数管理）

---

## 必要条件 / 依存関係

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime, logging 等）

（実際のインストールはプロジェクトの pyproject.toml / requirements.txt に従ってください）

例（pip）:
```bash
python -m pip install duckdb openai defusedxml
```

---

## 環境変数

主要な環境変数（Settings 参照）:

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token
  - SLACK_BOT_TOKEN : Slack 通知用 bot token
  - SLACK_CHANNEL_ID : Slack チャンネル ID
  - KABU_API_PASSWORD : kabu ステーション API パスワード
- 任意（デフォルト値あり）
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
  - OPENAI_API_KEY (used by AI モジュール)

.env 自動ロードの優先順位:
- OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

例の .env（README 用）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt
   # または最低限
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定（.env/.env.local をプロジェクトルートに作成）
   - README の「環境変数」を参照して必要なキーを設定。

5. DuckDB データベース準備（任意）
   - 監査ログ用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（主要な API / 実行例）

以下はライブラリを直接 Python から使う基本例です。

- DuckDB へ接続して ETL を実行（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（ai.score_news）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"ai_scores written: {n_written}")
```

- 市場レジーム判定（ai.score_regime）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- カレンダー判定ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
print(is_trading_day(conn, date(2026,3,20)))
print(next_trading_day(conn, date(2026,3,20)))
```

- ニュース収集（RSS）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

- 監査スキーマ初期化（既存接続へ）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 実装上の注意点 / 設計方針（要点）

- Look-ahead バイアス回避:
  - AI/ETL モジュールは内部で datetime.today() を不適切に参照しないよう設計されています。target_date 引数を明示的に渡すことが推奨されます。
- フェイルセーフ:
  - OpenAI API 失敗時はゼロスコアやスキップで継続する実装が多く、例外による全面停止を避けています。ログを確認してください。
- 冪等性:
  - J-Quants → DuckDB の保存は ON CONFLICT による更新で冪等に実装されています。
- セキュリティ:
  - RSS 取得は SSRF 対策・受信サイズ制限・XML の安全パーサ（defusedxml）を使用しています。
- カレンダー不在時のフォールバック:
  - market_calendar がない場合は曜日ベース（土日除外）のフォールバックを行います。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                      — 環境変数/設定管理（.env 自動ロード、Settings）
- ai/
  - __init__.py
  - news_nlp.py                   — ニュースセンチメント（score_news）
  - regime_detector.py           — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py            — J-Quants API クライアント + 保存ロジック
  - news_collector.py            — RSS 収集・前処理
  - calendar_management.py       — マーケットカレンダー管理
  - quality.py                   — データ品質チェック
  - audit.py                     — 監査ログスキーマ初期化 / init_audit_db
  - etl.py                       — ETL インターフェース再エクスポート（ETLResult）
  - stats.py                     — zscore_normalize 等の統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py           — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py       — calc_forward_returns / calc_ic / factor_summary / rank

（追加の execution, strategy, monitoring モジュールがパッケージに含まれる設計になっていますが、README のコードベースでは data / ai / research が中心です）

---

## ロギング・監視

- Settings.log_level でログレベル設定が可能。環境変数 LOG_LEVEL を設定してください。
- 監視用の閾値（CPU/MEM/DISK）は環境変数 CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT で調整可能です。

---

## 開発 / テスト時のヒント

- 自動 .env ロードを無効化したい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しやネットワーク I/O を伴う関数はユニットテストでモックできます。コードは特定関数を差し替え可能な形で実装されています（例: news_nlp._call_openai_api を patch）。
- DuckDB をインメモリで使うとテストが早くなります:
  ```python
  conn = duckdb.connect(":memory:")
  ```

---

## 参考 / 追加情報

- J-Quants API の利用にはリフレッシュトークンが必要です。settings.jquants_refresh_token がそれを提供します。
- OpenAI の利用には OPENAI_API_KEY を設定してください（関数呼び出しで api_key を明示的に渡すことも可能）。
- Slack 連携や kabu API は環境変数と外部サービスへの接続が必要です。テスト実行時はダミー値やモックを使用してください。

---

必要であれば、README に含める .env.example、簡易の起動スクリプト、または CI 用のテスト実行例（pytest 用）を追加で用意します。どの情報を優先して詳述しましょうか？