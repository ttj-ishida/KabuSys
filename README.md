# KabuSys

日本株向けのデータプラットフォーム＆自動売買補助ライブラリです。  
ETL / データ品質 / ニュース収集・NLP / マーケットレジーム判定 / 監査ログ（トレーサビリティ）など、戦略実装・研究・運用に必要な基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- データ取得・ETL（J-Quants API 経由の株価・財務・市場カレンダー）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- ニュース収集（RSS）と前処理
- ニュースに対する LLM ベースのセンチメント分析（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC など）
- 監査ログ（signal → order_request → executions を追跡するスキーマ）
- 設定・環境変数管理（.env 自動ロード機能付き）

設計上の特徴として、ルックアヘッドバイアス防止のために内部関数が `date`/`target_date` を明示的に受け取り、ランタイムの現在時刻を直接参照しない方針が採られています。また DuckDB を主なオンディスク DB に想定し、ETL は冪等（idempotent）に実装されています。

---

## 主な機能一覧

- data/
  - ETL: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント: token 管理、ページネーション、保存機能（save_*）
  - カレンダー管理: 営業日判定、next/prev/trading days、calendar_update_job
  - ニュース収集: RSS 取得・前処理・SSRF 対策・トラッキング除去
  - 品質チェック: 欠損、スパイク、重複、日付不整合の検出（QualityIssue で集約）
  - 監査ログ: 監査テーブル定義・初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ: Zスコア正規化など
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF(1321) MA 乖離 と マクロニュース（LLM）を合成して market_regime に保存
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility（ファクター算出）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

前提:
- Python 3.10 以上（パイプライン内で | 型・標準ライブラリの機能を使用）
- DuckDB, OpenAI SDK, defusedxml などが必要

例: 仮想環境作成 & 依存パッケージ（推奨）

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# その他、運用スクリプト等を追加する場合は適宜インストール
```

環境変数（必須／任意）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 呼び出し時に使用可能）
- DUCKDB_PATH: デフォルト database パス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（例: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

.env の自動読み込み:
- プロジェクトルート（.git か pyproject.toml があるディレクトリ）に `.env` / `.env.local` があれば自動ロードされます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

注意:
- .env のパースロジックはシェル風の export 文、引用符、インラインコメント等に対応しています。

---

## 使い方（主要な例）

以下はモジュールの典型的な使い方の抜粋です（詳細は各モジュールの docstring を参照）。

1) DuckDB 接続と日次ETL実行

```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日（ただし内部で営業日に調整）
print(result.to_dict())
```

2) OpenAI を使ったニューススコアリング（AI）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → 環境変数 OPENAI_API_KEY を参照
print(f"scored {count} tickers")
```

3) 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) J-Quants からデータを直接取得して保存

```python
from kabusys.data import jquants_client as jq
import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

id_token = jq.get_id_token()  # settings.jquants_refresh_token が必要
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,3,20))
saved = jq.save_daily_quotes(conn, records)
```

5) ニュース RSS の取得

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

6) 監査ログスキーマ初期化

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # 必要なディレクトリを自動作成
```

テスト時のヒント:
- OpenAI 呼び出しはモジュール内の `_call_openai_api` をモックすることで外部 API を叩かずにテストできます（kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api を patch）。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

OpenAI 関連:
- OPENAI_API_KEY（score_news / score_regime のデフォルトで参照。関数呼び出し時に直接 api_key を渡すことも可）

運用・DB:
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト data/monitoring.db）
- PID_FILE_PATH（プロセス監視用）
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（INFO 等）

自動ロード制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動ロードを無効にできます。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの公開パッケージルート: src/kabusys/

主要モジュール一覧:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py           # J-Quants API クライアント + 保存ロジック
  - pipeline.py                 # ETL パイプライン（run_daily_etl 等）
  - etl.py                      # ETLResult のエクスポート
  - news_collector.py           # RSS 収集・前処理
  - calendar_management.py      # market_calendar 周りのユーティリティ
  - quality.py                  # データ品質チェック
  - stats.py                    # 汎用統計（zscore_normalize 等）
  - audit.py                    # 監査ログスキーマ定義・初期化
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

各ファイル・関数は docstring に詳細な設計意図やフェイルセーフ挙動・ルックアヘッドバイアス対策が書かれています。実運用に組み込む際は各 docstring を必ず確認してください。

---

## 開発・運用上の注意

- ルックアヘッドバイアス防止:
  - AI / 研究 / ETL の多くの関数は `target_date` を明示的に受け取り、実行時の現在時刻を参照しない設計です。バックテストや再現性が必要な場合は date を明示してください。
- 冪等性:
  - ETL 保存処理（save_*）は ON CONFLICT による冪等更新を行いますが、外部からの DB 変更やスキーマ変更時の互換性に注意してください。
- リトライ・レート制御:
  - J-Quants API の呼び出しはレートリミットとリトライを実装していますが、環境や API 変更により挙動が変わる可能性があります。監視を導入してください。
- セキュリティ:
  - news_collector は SSRF 対策・トラッキング除去・サイズ制限・defusedxml の利用などを行っていますが、公開環境での外部 URL 処理では追加の安全対策（プロキシ、タイムアウト監視）を推奨します。

---

もし README に追加してほしい利用例（起動スクリプト、cron 設定例、Slack 通知の実例など）があれば教えてください。必要に応じてサンプル .env.example も作成します。