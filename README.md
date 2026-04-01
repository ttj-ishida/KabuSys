# KabuSys

日本株向けのデータ基盤・リサーチ・AIスコアリング・監査・ETL を含む自動売買システム基盤ライブラリ。

このリポジトリは、J-Quants からのデータ取得（株価・財務・市場カレンダー）、ニュース収集・NLP スコアリング、マーケットレジーム判定、ファクター計算、ETL パイプライン、監査ログ（発注/約定トレース）の初期化・管理などのユーティリティ群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を不用意に参照しない等）
- DuckDB を中心にデータ永続化を行う
- OpenAI（gpt-4o-mini 等）による JSON Mode を用いたスコアリングを行う
- 冪等（idempotent）設計（INSERT ... ON CONFLICT 等）を重視
- ネットワーク/外部API 呼び出しにはリトライ・バックオフ等の耐障害性を組み込む

---

## 機能一覧

- 設定管理
  - .env ファイル・環境変数の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - 必須環境変数の取得用 Settings（kabusys.config.settings）

- データ取得 / ETL
  - J-Quants API クライアント（jquants_client）
    - 株価日足（/prices/daily_quotes）
    - 財務データ（/fins/statements）
    - 市場カレンダー（/markets/trading_calendar）
    - トークン自動リフレッシュ・レートリミット・ページネーション対応
  - ETL パイプライン（data.pipeline）
    - run_daily_etl: カレンダー／株価／財務の差分 ETL + 品質チェック
    - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
  - 品質チェック（data.quality）
    - 欠損、スパイク、重複、日付不整合などの検出

- ニュース収集・NLP
  - RSS 収集（data.news_collector）
    - URL 正規化、SSRF 対策、XML の安全パース（defusedxml）、前処理
  - ニュースセンチメント（ai.news_nlp）
    - OpenAI による銘柄ごとのセンチメントスコア生成（JSON mode、バッチ & リトライ）
    - 関数: score_news(conn, target_date, api_key=None)

- マーケットレジーム判定（ai.regime_detector）
  - ETF(1321) の 200 日 MA 乖離 + マクロニュース（LLM）を重み付けしてレジーム判定
  - 関数: score_regime(conn, target_date, api_key=None)

- リサーチ / ファクター計算（research）
  - Momentum / Value / Volatility などの計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化等

- 監査ログ（data.audit）
  - signal_events, order_requests, executions テーブルの DDL と初期化ユーティリティ
  - init_audit_schema / init_audit_db による初期化（UTC タイムゾーン固定）

- 汎用統計ユーティリティ（data.stats）
  - zscore_normalize など

---

## 必要条件（依存ライブラリ）

主な依存例（プロジェクトの実際の requirements は別途管理してください）:
- Python 3.10+
- duckdb
- openai
- defusedxml

推奨：
- 仮想環境（venv, pyenv 等）

インストール例（最低限のライブラリ）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージを editable インストールするなら:
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／展開する。

2. 仮想環境を作成して依存をインストールする（上記参照）。

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）配下の `.env` / `.env.local` を自動で読み込みます（OS 環境変数を上書きしないようにデフォルトで制御）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot Token
   - SLACK_CHANNEL_ID: Slack 通知の送信先チャンネル ID
   - KABU_API_PASSWORD: kabu API のパスワード（必要な場合）
   - OPENAI_API_KEY: OpenAI を使う場合は API キー（score_news / score_regime に未指定時に参照）
   - その他オプション: DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KABUSYS_ENV, LOG_LEVEL 等

例: `.env`（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

以下は基本的な利用例です。すべて DuckDB 接続を渡して実行します。

- DuckDB に接続する例:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数に設定済みなら None で可
print(f"書き込み銘柄数: {written}")
```

- マーケットレジームを判定して market_regime に書き込む（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/monitor_audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

- audit スキーマのみを既存接続に追加:
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

---

## 主要 API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.log_level, など

- ETL / Data
  - run_daily_etl(conn, target_date, id_token=None, ...)
  - run_prices_etl(conn, target_date, ...)
  - run_financials_etl(conn, target_date, ...)
  - run_calendar_etl(conn, target_date, ...)

- AI
  - score_news(conn, target_date, api_key=None)  -> ai_scores に書き込む
  - score_regime(conn, target_date, api_key=None) -> market_regime に書き込む

- Research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons=None)
  - calc_ic(factor_records, forward_records, factor_col, return_col)
  - factor_summary(records, columns)
  - rank(values)

- Data utilities
  - init_audit_db(path) / init_audit_schema(conn)
  - jquants_client.fetch_daily_quotes / save_daily_quotes / fetch_financial_statements / save_financial_statements / fetch_market_calendar / save_market_calendar

---

## ディレクトリ構成

（src 以下を基準に主要ファイルを抜粋）

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
      - quality.py
      - stats.py
      - calendar_management.py
      - audit.py
      - (その他 data 関連ユーティリティ)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
    - monitoring/ (パッケージは __all__ にあるがここでは詳細省略)
    - strategy/ (同上)
    - execution/ (同上)

---

## 開発 / テストに関するメモ

- 環境変数自動読み込みは .env / .env.local をプロジェクトルートから読みます。テストで環境を動的制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API 呼び出しは JSON Mode を期待しており、レスポンスのパースに失敗した場合はフォールバック（score_news: スコア除外、score_regime: macro_sentiment=0.0）して継続する設計です。ユニットテストでは _call_openai_api などをモックして動作検証してください。
- DuckDB の executemany に空配列を渡せない制約（バージョン依存）に注意して、ライブラリ内では空チェックを行っています。
- news_collector は SSRF 対策、受信サイズ制限、XML の安全パースなどを行っています。RSS フィードの取り扱いは慎重に。

---

## ライセンス・貢献

リポジトリに含める LICENSE ファイルを参照してください。バグ報告・機能提案は Issue を作成してください。

---

README はここまでです。必要なら以下を追加できます：
- .env.example の完全版
- requirements.txt の推奨内容
- 実運用時のデプロイ手順（systemd, Supervisor, Cron など）
- Slack / kabu API を使ったモニタリング・通知の設定例

ご希望があれば追記します。