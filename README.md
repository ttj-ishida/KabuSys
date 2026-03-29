# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI 経由）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（オーダー追跡）などの機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL パイプライン
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（銘柄別 / マクロ）
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- リサーチ用ファクター計算（モメンタム／バリュー／ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を DuckDB に構築

設計上の特徴として、ルックアヘッドバイアス対策、API リトライ／レート制御、冪等保存（ON CONFLICT）などを重視しています。

---

## 機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
- J-Quants クライアント
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - トークン自動リフレッシュ、レートリミッタ、リトライ実装
- ニュース収集
  - RSS 取得（SSRF 対策、gzip 上限、トラッキング除去）
  - raw_news / news_symbols への冪等保存（設計に従い保存処理が別途必要）
- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄別センチメンティング（バッチ、JSON mode、リトライ、検証）
  - calc_news_window（ニュース対象ウィンドウ計算）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離 + マクロセンチメント合成でレジーム判定
- Research（kabusys.research）
  - calc_momentum, calc_value, calc_volatility
  - calc_forward_returns, calc_ic, factor_summary, rank、zscore_normalize
- データ品質チェック（kabusys.data.quality）
  - 欠損 / 重複 / スパイク / 日付不整合の検出と QualityIssue レポート
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day 等の判定ユーティリティ、calendar_update_job
- 監査ログ（kabusys.data.audit）
  - 監査用テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理（kabusys.config）
  - .env 自動ロード（.env, .env.local）と必須環境変数チェック
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化

---

## 要件

- Python 3.10+
- 推奨パッケージ（最低限）:
  - duckdb
  - openai (OpenAI Python SDK を利用する想定)
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging など

必要に応じて他ライブラリ（例: sqlite3 は標準）も利用されます。

---

## セットアップ手順

1. リポジトリを取得し、仮想環境を作成・有効化します。

   ```bash
   git clone <repository-url>
   cd <repository-root>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストールします（例）:

   ```bash
   pip install duckdb openai defusedxml
   ```

   - プロジェクトに requirements.txt があればそれを利用してください。

3. 開発インストール（パッケージが setup / pyproject を用意している場合）:

   ```bash
   pip install -e .
   ```

4. 環境変数を用意します。ルートに `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config 参照）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 環境変数（主なもの）

以下は本ライブラリで参照される主な環境変数です（README 用の簡易一覧）。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: sqlite（monitoring 等）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

例（.env）:

```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

以下は Python REPL / スクリプト内での利用例です。import 名は kabusys パッケージを想定します。

- 共通設定取得

```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続を作って日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）をスコアリングする

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"scored {n_written} codes")
```

- 市場レジームを判定する

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化する（専用 DB を作る場合）

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を用いて order/event の挿入・クエリが可能
```

- RSS を取得する（ニュース収集の低レイヤー）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["datetime"], a["title"])
```

注意点:
- score_news / score_regime は OpenAI の API を呼び出すため、OPENAI_API_KEY を環境変数か引数で指定してください。
- ETL 周りは J-Quants トークン（JQUANTS_REFRESH_TOKEN）が必要です。
- DuckDB に対象テーブル（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar など）が存在している前提です。スキーマ初期化はプロジェクト内のスキーマ用ユーティリティ（存在する場合）を利用してください。

---

## 開発・デバッグのヒント

- .env の自動ロードは kabusys.config によりプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストや CI で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しやネットワーク部分はユニットテスト時にモックされる設計です（モジュール内の _call_openai_api や _urlopen 等を patch）。
- DuckDB の executemany に関する注意（空リストを渡さない等）がコード内に記載されています。DB 操作で失敗する場合は logs を確認してください。
- ログレベルは環境変数 LOG_LEVEL で制御できます。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
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
    - (その他: e.g. etl, schema helpers)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - (他: strategy / execution / monitoring 等のサブパッケージは __all__ に記載、実装に応じて追加)

各モジュールは docstring に設計方針・処理フロー・注意点が詳述されています。実装参照の際は docstring をまず確認してください。

---

もし README に含めたい追加項目（例: CI / テスト実行方法、具体的なスキーマ定義・DDL、運用時のワークフロー説明など）があれば教えてください。必要に応じて追記します。