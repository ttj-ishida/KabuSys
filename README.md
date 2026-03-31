# KabuSys

日本株向けの自動売買データプラットフォーム / 研究・AI評価・監査ログ機能を備えたライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、ファクター計算、研究用ユーティリティ、監査ログ（約定トレース）などを提供します。

主な設計方針：
- DuckDB をデータレイクとして利用（ローカルファイル / インメモリ対応）
- Look-ahead バイアスを避ける実装（target_date を明示的に渡す）
- 外部 API 呼び出しにはリトライ／レートリミット対策あり
- ETL / 品質チェック / 監査ログ等の冪等性を重視

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数取得 API（settings）

- データ取得（J-Quants）
  - 日次株価 (OHLCV) 取得 / 保存（fetch_daily_quotes / save_daily_quotes）
  - 財務諸表取得 / 保存（fetch_financial_statements / save_financial_statements）
  - JPX マーケットカレンダー取得 / 保存（fetch_market_calendar / save_market_calendar）
  - レート制限・自動トークンリフレッシュ・リトライ実装

- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 品質チェック（欠損・スパイク・重複・日付整合性）

- ニュース収集 / NLP
  - RSS 取得（SSRF 対策・サイズ制限・URL 正規化）
  - OpenAI を用いたニュースセンチメント集約（score_news）
  - 市場レジーム判定（ETF 1321 MA200 とマクロニュースの LLM 結果を合成して score_regime）

- 研究用ユーティリティ
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - z-score 正規化ユーティリティ

- 監査（トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - init_audit_schema / init_audit_db（DuckDB）

---

## セットアップ手順

前提
- Python 3.10+（| 型注釈、match 等の構文に依存しないが Path | None を使っているため 3.10 以上推奨）
- DuckDB を使用可能な環境

推奨インストール（仮想環境を推奨）:

1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .\.venv\Scripts\activate）

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があればそれを使ってください）

3. リポジトリルートに .env を作成
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動検出し、
     `.env` と `.env.local` を順に読み込みます（OS 環境変数が優先されます）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（コード参照）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（settings.jquants_refresh_token）
- KABU_API_PASSWORD      : kabuステーション API のパスワード（settings.kabu_api_password）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack の送信先チャネル ID
- OPENAI_API_KEY         : OpenAI を利用する場合（score_news / score_regime で参照）
オプション
- KABUSYS_ENV            : "development" / "paper_trading" / "live"（デフォルト development）
- LOG_LEVEL              : "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite（デフォルト data/monitoring.db）

.env の例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=your_openai_api_key_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易ガイド）

以下は Python スクリプトや REPL での利用例です。DuckDB の接続には duckdb.connect を使用してください。

- 基本的な使い方（settings の参照、DuckDB 接続）
```python
from kabusys.config import settings
import duckdb

# settings.duckdb_path は Path を返す
db_path = str(settings.duckdb_path)
conn = duckdb.connect(db_path)
```

- 日次 ETL を実行する（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を渡すか環境変数 OPENAI_API_KEY を使う
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"{n_written} 銘柄のスコアを更新しました")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査データベース初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit_duckdb.db")
# これで signal_events, order_requests, executions テーブル等が作成されます
```

- ニュース RSS 取得（単体）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点：
- OpenAI の呼び出しには API キー（OPENAI_API_KEY）が必要です。score_news / score_regime は失敗時フェイルセーフ（スコア 0 等）で継続する実装です。
- J-Quants API 呼び出しはレート制限（120 req/min）に従って実装されています。get_id_token / fetch_* 関数は自動でトークンを更新します。
- DuckDB への大量挿入や executemany の空リストに関する制約（コメント参照）に注意しています。

---

## ディレクトリ構成

主要なモジュールと役割を抜粋した構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP / score_news（OpenAI）
    - regime_detector.py           — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得/保存）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py            — RSS ニュース収集
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（z-score 等）
    - calendar_management.py       — 市場カレンダー管理 / 営業日判定
    - audit.py                     — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum / value / volatility）
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー
  - ai/                          — AI 関連ユーティリティ（LLM 呼び出しと結果整形）
  - research/                    — 研究用関数群
  - data/                        — ETL / DB 保存 / 品質チェック / カレンダー管理 等

（実際のファイルは src/kabusys 以下に多数含まれます。README の要点は上記に示した主要モジュールです）

---

## 運用・設計上の注意

- Look-ahead バイアス対策：内部処理は target_date を明示する設計であり、datetime.today() を直接参照しない箇所が多くあります。バックテストで使用する際は、過去時点のデータしか参照しないように注意してください。
- 冪等性：ETL / 保存処理は基本的に ON CONFLICT (または個別 DELETE → INSERT) による冪等設計です。
- エラーハンドリング：外部 API 呼び出しはリトライ・フォールバックを行い、可能な限り処理を継続するフェイルセーフを採用しています。重大な品質問題は quality モジュールで検出できます。
- セキュリティ：news_collector は SSRF 対策・XML インジェクション対策（defusedxml）・レスポンスサイズ制限等を実装しています。

---

必要であれば、README にサンプル .env.example、requirements.txt、さらに具体的な CLI / systemd / Airflow などの運用例（ETL スケジューリング、Slack 通知連携、kabuステーション経由の発注フロー）を追記できます。どの部分を詳細化したいか教えてください。