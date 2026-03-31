# KabuSys

日本株の自動売買・データプラットフォームライブラリです。  
データ収集（J-Quants）、ETL、ニュース収集・NLP、AI を使ったニュース／市場レジーム評価、リサーチ用ファクター計算、監査ログ（発注→約定トレーサビリティ）などを提供します。

---

## 概要

KabuSys は日本株向けのデータ基盤と研究・自動売買コンポーネント群をまとめた Python パッケージです。主な特徴は以下の通りです。

- J-Quants API による株価 / 財務 / 市場カレンダーの差分 ETL（レート制限・リトライ・トークン自動リフレッシュ対応）
- DuckDB をバックエンドとした ETL・品質チェック機能
- RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）と市場レジーム判定
- 研究用ファクター計算（Momentum / Value / Volatility など）と統計ユーティリティ（Zスコア正規化、IC 計算等）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
- 実運用向けの設定管理（.env 自動読み込み、環境別モード、ログレベル等）

---

## 主な機能一覧

- ETL
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェックの一括差分処理
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別ジョブ
- J-Quants クライアント
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_* 系で DuckDB に冪等保存
- ニュース
  - fetch_rss（RSS 取得、前処理、安全対策）
  - news_nlp.score_news：銘柄別ニュースセンチメントを ai_scores に書き込み
- AI
  - ai.regime_detector.score_regime：ETF（1321）MA200 とマクロ記事センチメントを合成して market_regime を更新
  - ai.news_nlp.score_news：OpenAI による銘柄ごとのニュースセンチメント
- リサーチ
  - research.calc_momentum / calc_value / calc_volatility
  - research.feature_exploration（将来リターン、IC、統計サマリ）
- データ品質
  - data.quality.run_all_checks（欠損・スパイク・重複・日付不整合チェック）
- 監査ログ
  - data.audit.init_audit_db / init_audit_schema（監査用 DuckDB 初期化）
- カレンダー管理
  - data.calendar_management.{is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job}

---

## 必要条件

- Python 3.10 以上
- 必須 Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 実行する機能に応じて外部 API のキーや追加パッケージが必要
  - J-Quants リフレッシュトークン
  - OpenAI API キー（ai モジュールを利用する場合）
  - kabu ステーション API パスワード（発注連携を行う場合）
  - Slack トークン（モニタリング通知等）

pip の一例:
```
pip install duckdb openai defusedxml
# （運用で Slack 等を使う場合は slack-sdk 等を追加）
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトし、package をインストール（開発モード推奨）
   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数を用意する（.env をプロジェクトルートに置くと自動読み込みされます）
   - 自動ロードはデフォルトで有効（.env → .env.local の順で読み込む）
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

   推奨する環境変数（.env の例）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   OPENAI_API_KEY=...
   KABU_API_PASSWORD=...
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PID_FILE_PATH=data/execution.pid
   CPU_THRESHOLD_PCT=90.0
   MEMORY_THRESHOLD_PCT=85.0
   DISK_THRESHOLD_PCT=90.0
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

4. DuckDB データベースの用意（デフォルトは data/kabusys.duckdb）
   - パスは settings.duckdb_path で制御（環境変数 DUCKDB_PATH）

---

## 使い方（簡易例）

以下は主要ユースケースの最小例です。実際はログやエラーハンドリングを適切に行ってください。

- DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> env OPENAI_API_KEY を使用
print(f"scored {count} codes")
```

- 市場レジームをスコアリング
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成
```

- RSS フィードを取得（ニュースコレクタ）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## 主要 API / エントリポイント

- ETL / データ
  - kabusys.data.pipeline.run_daily_etl(...)
  - kabusys.data.pipeline.run_prices_etl(...)
  - kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
  - kabusys.data.jquants_client.fetch_financial_statements / save_financial_statements
  - kabusys.data.jquants_client.fetch_market_calendar / save_market_calendar

- ニュース / AI
  - kabusys.data.news_collector.fetch_rss(...)
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- 研究
  - kabusys.research.calc_momentum / calc_value / calc_volatility
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary

- 監査
  - kabusys.data.audit.init_audit_db(path)
  - kabusys.data.audit.init_audit_schema(conn)

- 品質チェック
  - kabusys.data.quality.run_all_checks(conn, target_date=..., reference_date=...)

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必要）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注時）
- KABU_API_BASE_URL: kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite (監視) DB パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: 環境 (development, paper_trading, live)
- LOG_LEVEL: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

.env の自動パースは .env/.env.local のクォートやコメントに対して堅牢に実装されています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（1321 + マクロ）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + 保存処理
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL の公開インターフェース（ETLResult）
    - news_collector.py      — RSS ニュース収集（SSRF 対策等）
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py — マーケットカレンダー管理
    - audit.py               — 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Value/Volatility 計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ等

---

## 開発・テスト

- 自動ロードされる .env を使うとテストが環境依存になるため、ユニットテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するか、settings オブジェクトをモックしてください。
- OpenAI 呼び出し部分は内部で _call_openai_api 関数をラップしているため、テストではこの関数を patch して外部 API 呼び出しを差し替えられます。
- news_collector._urlopen などもモック可能です。

---

## 注意事項

- OpenAI の利用はコストが発生します。score_news/score_regime を実行する際は API キーと利用量に注意してください。
- 実運用（live 環境）での発注・約定処理は十分な安全対策（リスク管理、発注冪等性、ログ監査）を行ってから行ってください。KABUSYS_ENV を正しく設定してください（live と paper_trading の違い）。
- .env ファイルに秘密情報を直接置く場合はファイル保護（git 管理除外等）を徹底してください。
- J-Quants / OpenAI / kabu API のレート制限や認証要件に従って運用してください。

---

必要であれば README に使い方のより具体的なコード例（ETL を定期実行する cron / systemd ユニット例、Slack 通知連携例、kabu ステーション発注ワークフローのテンプレート等）を追加します。どの部分の詳細を優先してほしいか教えてください。