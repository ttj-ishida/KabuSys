# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL・データ品質チェック・ニュース収集・LLMによるニュースセンチメント、ファクター計算、監査ログなど、トレーディングシステムに必要な基盤処理を提供します。

バージョン: 0.1.0

---

## 主要コンセプト / 概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API などからの株価・財務・カレンダー等の差分 ETL（DuckDB へ保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）とニュース→銘柄マッピング
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント（ai_scores）生成
- 市場レジーム判定（MA200乖離 + マクロニュースセンチメントの合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（signal → order_request → execution トレース用のスキーマ初期化）
- 設定管理（.env 自動ロード / 環境変数）

設計方針の多くは「ルックアヘッドバイアス回避」「冪等性」「フォールセーフ」を重視しています。

---

## 機能一覧

- 環境変数／.env 自動読み込み（プロジェクトルートを検出）
- J-Quants API クライアント（ページネーション・レート制御・自動リフレッシュ・保存用ユーティリティ）
- ETL パイプライン（run_daily_etl で calendar/prices/financials の差分取得と品質チェック）
- データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
- ニュース収集（RSS の正規化・SSRF 対策・トラッキングパラメータ除去）
- OpenAI を用いたニュース NLP（銘柄別センチメント score_news、マクロセンチメントを含む score_regime）
- 市場カレンダー管理（営業日判定・next/prev_trading_day 等）
- 研究（ファクター計算、将来リターン計算、IC 計算、統計サマリ）
- 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）

---

## 必要条件（概略）

- Python 3.10+（型ヒントに union | を多用しているため）
- ライブラリ:
  - duckdb
  - openai
  - defusedxml

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトの requirements.txt がある場合はそれを使用
# pip install -r requirements.txt
```

---

## 環境変数 / .env

自動でプロジェクトルート（.git または pyproject.toml を探索）を見つけ `.env` / `.env.local` を読み込みます（優先度: OS 環境 > .env.local > .env）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に使用される環境変数（必須 / デフォルトあり）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（ai 関連関数で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視設定
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

例（.env.example）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（簡易）

1. Python 仮想環境を作成してアクティベート
2. 依存ライブラリをインストール（上記参照）
3. プロジェクトルートに `.env` を用意（.env.example を参考）
4. DuckDB ファイル保存先ディレクトリを作成（例: data/）
5. 必要に応じて監査 DB の初期化等を実行

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL から呼び出す例です。

1) DuckDB 接続を作って日次 ETL を実行（run_daily_etl）:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを生成（ai/news_nlp.score_news）:
```python
import duckdb
from kabusys.ai.news_nlp import score_news
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("書き込み銘柄数:", n_written)
```

3) 市場レジームスコアを算出（ai/regime_detector.score_regime）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

# conn は DuckDB 接続（prices_daily, raw_news, market_regime を参照）
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査 DB の初期化:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# 以後 conn_audit を使って監査ログを書き込む
```

5) RSS 取得（ニュース収集の一部）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## 主要 API（抜粋）

- kabusys.config.settings — 環境設定アクセス
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.news_collector
  - fetch_rss, preprocess_text
- kabusys.ai.news_nlp.score_news
- kabusys.ai.regime_detector.score_regime
- kabusys.research.* — factor 計算・解析関数
- kabusys.data.audit.init_audit_schema / init_audit_db

設計上、AI 呼び出し部分（OpenAI API）はテスト用に内部呼び出し関数をモックできるようになっています（例: kabusys.ai.news_nlp._call_openai_api）。

---

## ディレクトリ構成

（主要なファイル／モジュール）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env ロード / settings
  - ai/
    - __init__.py
    - news_nlp.py — 銘柄別ニュースセンチメント生成
    - regime_detector.py — MA200 + マクロセンチメントで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + DuckDB 保存ロジック
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult 再エクスポート
    - news_collector.py — RSS 収集・正規化
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - stats.py — zscore 正規化等の統計ユーティリティ
    - quality.py — データ品質チェック
    - audit.py — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 等
    - feature_exploration.py — 将来リターン / IC / 統計サマリ 等
  - (その他: strategy, execution, monitoring などを想定するエントリ)

---

## 運用上の注意 / 実装に関する補足

- ルックアヘッドバイアス対策:
  - 各 AI / 研究モジュールは内部で date.today() を直接参照せず、必ず target_date を引数で明示します。
- 冪等性:
  - J-Quants からの保存は ON CONFLICT DO UPDATE を用いているため再実行可能。
  - ニュース記事 ID は正規化URLの SHA-256 を利用して冪等性を担保。
- フェイルセーフ:
  - OpenAI 呼び出し失敗時はスコアを 0.0 にフォールバックする処理や、該当銘柄をスキップする処理などを入れているため、AI 障害で ETL 全体が停止しないよう配慮されています。
- テスト:
  - OpenAI 呼び出し関数や HTTP オープン処理はモック可能（内部で関数参照しているため unittest.mock.patch で差し替えられます）。
- 監査 DB のタイムゾーンは UTC に固定されます（init_audit_schema が SET TimeZone='UTC' を実行）。

---

## 貢献・拡張

- 新しい ETL 対象やニュースソースの追加は jquants_client / news_collector を拡張してください。
- 実行スケジューラ（cron / systemd timer / Airflow 等）から run_daily_etl を定期実行するのが想定ユースケースです。
- 監視・通知（Slack 連携）は設定変数を用いて実装を追加できます。

---

README は以上です。具体的な使い方やデプロイ手順（CI/CD、コンテナ化、運用 runbook など）を追加したい場合は、運用要件に合わせてサンプルを作成します。必要なら追記してください。