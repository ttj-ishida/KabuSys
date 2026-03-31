# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォームと自動売買支援ライブラリです。J-Quants / kabuステーション / OpenAI 等を組み合わせて、データETL、品質チェック、ニュースセンチメント解析、マーケットレジーム判定、監査ログ（発注トレース）などを提供します。

---

## 概要

本プロジェクトは以下の領域に対応するモジュール群を提供します。

- データ収集・ETL（J-Quants API 経由で株価・財務・カレンダーを取得し DuckDB に保存）
- データ品質チェック（欠損・重複・スパイク・日付不整合など）
- ニュース収集・NLP（RSS 収集、OpenAI による銘柄別センチメント算出）
- 市場レジーム判定（ETF の 200 日 MA 乖離 + マクロニュースの LLM センチメントを合成）
- 研究用ユーティリティ（ファクター算出、将来リターン、IC、統計）
- 監査ログ（signal → order_request → execution までのトレーサビリティ）
- 環境設定管理（.env / 環境変数自動読み込み）

設計方針として、ルックアヘッドバイアスを避けるために内部で datetime.today()/date.today() を直接参照しないよう配慮されています（対象日を明示して処理）。

---

## 主な機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - データ品質チェック: run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - ニュース収集: RSS fetch_rss（SSRF 対策・サイズ制限・ID正規化）
  - 監査ログ（audit）: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に保存
  - regime_detector.score_regime: 市場レジーム（日次）を market_regime に保存（ETF + LLM 合成）
- research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - Settings: 環境変数経由の設定取得（自動 .env 読み込み、必須キー検査）

---

## 必要要件 / 依存パッケージ（例）

- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリ: urllib, json, logging, datetime 等）

requirements.txt をプロジェクトに用意する場合の例:
- duckdb
- openai
- defusedxml

（実行環境に応じて追加の依存がある可能性があります）

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. 仮想環境を作成・有効化（例）
```bash
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows
```

3. 依存パッケージをインストール
```bash
pip install duckdb openai defusedxml
```

4. 環境変数 / .env を準備

プロジェクトルートに `.env`（および必要に応じ `.env.local`）を置くと、モジュール起動時に自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。

必須 (Settings で _require_ される項目):
- JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API パスワード
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV            — development / paper_trading / live（デフォルト development）
- LOG_LEVEL              — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動ロードを無効化
- DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

例 `.env`:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（コード例）

以下は主要な機能の Python からの呼び出し例です。実行前に必要な環境変数を設定してください。

- Settings の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB に接続して日次 ETL を実行
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=None)  # target_date=None なら今日
print(result.to_dict())
```

- ニュースセンチメント（前日の前日15:00JST～当日08:30JST のウィンドウ）をスコア化して ai_scores に保存
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key 省略で OPENAI_API_KEY を使用
print(f"scored {count} symbols")
```

- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
print("score_regime returned", res)
```

- 監査DB 初期化（監査ログ用 DuckDB を作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルにアクセス可能
```

- ETL の個別実行（例: 株価差分ETL）
```python
from kabusys.data.pipeline import run_prices_etl
from datetime import date

fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
print(f"fetched {fetched}, saved {saved}")
```

- ニュース RSS 取得（news_collector.fetch_rss）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

注意: OpenAI を利用する処理（score_news / score_regime 等）は API キーやレート制限に注意して利用してください。API 呼び出しはリトライやフォールバックの実装がありますが、実行コストは発生します。

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (score_news / score_regime で使用; 引数で上書き可能)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (kabu API のベース URL、デフォルト http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (INFO 等)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env の自動ロードを無効化

自動読み込み順序: OS 環境変数 > .env.local > .env（プロジェクトルートは .git または pyproject.toml を基準に探索）

---

## ディレクトリ構成

（主要ファイル／モジュールの抜粋）

```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ etl.py
│  ├─ quality.py
│  ├─ stats.py
│  ├─ calendar_management.py
│  ├─ news_collector.py
│  ├─ audit.py
│  └─ ...
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
└─ research/  (ファクター探索・統計ユーティリティ)
```

各サブパッケージに実装詳細が置かれており、公開APIはパッケージの __all__ を通じて選別してエクスポートされています。

---

## 運用上の注意

- DuckDB を永続化する場合はバックアップと VACUUM（必要に応じて）を検討してください。
- OpenAI・J-Quants API はレート制限と使用料金が発生します。バッチ処理頻度・バッチサイズを適切に設計してください。
- ニュース収集は外部 URL を扱うため、SSRF 対策やサイズ制限が組み込まれています。追加のソースを追加する際は URL の妥当性を確認してください。
- 監査ログは削除しない前提で設計されています。運用時はディスク容量と保持ポリシーに注意してください。
- テスト時は環境ロードや API 呼び出しをモックすることを推奨します（コード側でもモック可能なフックが用意されています）。

---

## 開発・貢献

- コードスタイル、テスト、CI のルールはプロジェクトルートに置くファイル（pyproject.toml 等）に従ってください。
- 外部 API への実際の呼び出しはテストしづらいため、ユニットテストではモックを利用してください（例: OpenAI 呼び出し、URL open、J-Quants API の HTTP レスポンスなど）。
- .env.example を用意して、必要な環境変数を明示することを推奨します（プロジェクト内にない場合は手動で管理してください）。

---

この README はコードベース内のドキュメント文字列と設計コメントに基づいて作成しています。詳細な API 仕様や追加のユーティリティ関数については各モジュールの docstring を参照してください。必要であれば関数別の使用例や CLI エントリポイント（タスク実行スクリプト）を追記します。