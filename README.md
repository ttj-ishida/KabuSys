# KabuSys

日本株向け自動売買・データプラットフォーム（ライブラリ）です。  
J-Quants / JPX からのデータ取得・ETL、ニュース収集・NLP、LLM を用いたセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）、および取引ロジックに関する補助ユーティリティを含みます。

---

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から株価・財務・カレンダー等のデータを差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と前処理（raw_news / news_symbols テーブル）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄単位）およびマクロセンチメントと価格指標を組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal / order_request / executions）を格納する監査スキーマ初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針として、ルックアヘッドバイアス回避、冪等性（ON CONFLICT 等）、API レート制御・リトライ、フェイルセーフ（API失敗時はスキップ・デフォルト値を利用）を重視しています。

---

## 主な機能一覧

- データ ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）：レート制御・トークンリフレッシュ・ページネーション対応
- ニュース収集
  - RSS 取得・前処理・SSRF対策（kabusys.data.news_collector）
- ニュース NLP / AI
  - 銘柄ごとのニュースセンチメント算出（kabusys.ai.news_nlp.score_news）
  - マクロセンチメント + ETF MA を合成した市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- 研究ツール
  - ファクター計算（momentum / value / volatility）および特徴量探索・IC 計算（kabusys.research）
  - Zスコア正規化などの統計ユーティリティ（kabusys.data.stats）
- データ品質チェック（kabusys.data.quality）
- 監査ログ初期化 / 監査 DB ユーティリティ（kabusys.data.audit）
- 設定管理（kabusys.config）: .env 自動読み込み、環境変数アクセスラッパー

---

## セットアップ手順（開発環境）

前提
- Python 3.10+
- インターネット接続（J-Quants / OpenAI / RSS 等）

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（プロジェクトに requirements.txt が無い場合の例）
   - pip install duckdb openai defusedxml

   実際のプロジェクトでは setuptools / poetry を用いてパッケージをインストールしてください。
   例: pip install -e .

3. 環境変数（.env）を準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動でロードされます（kabusys.config）。
   - 自動ロードを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定してください（テスト等で利用）。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI系機能を実行する場合は必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視系）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境（development / paper_trading / live のいずれか）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

   .env の例（.env.example として保存）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB データベースの準備
   - デフォルトパスは `data/kabusys.duckdb`（settings.duckdb_path）。
   - 監査ログ専用 DB を初期化する例（kabusys.data.audit を使用）:

   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # :memory: も可
   ```

---

## 使い方（簡単なコード例）

以下はライブラリをプログラムから利用する例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定してください。

1) 日次 ETL の実行（市場カレンダー・株価・財務を差分取得して保存）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（銘柄単位）のスコアリング

- OpenAI API キーは環境変数 OPENAI_API_KEY で指定できます。明示的に渡すことも可能。

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))  # ai_scores テーブルに書き込む
print("書き込み銘柄数:", n_written)
```

3) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM 評価を合成）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルへ結果を書き込みます
```

4) 監査スキーマを初期化する

```python
import duckdb
from kabusys.data.audit import init_audit_schema

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

5) ニュース RSS を取得して raw_news に保存する（news_collector を直接呼ぶユーティリティはプロジェクトにより異なるため、fetch_rss を利用して DB へ挿入する処理を実装してください）

```python
from kabusys.data.news_collector import fetch_rss
from datetime import datetime

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注:
- 上記 API は DuckDB のコネクション（kabusys では duckdb.DuckDBPyConnection）を受け取ります。適切なテーブルスキーマ（raw_prices / raw_financials / raw_news / news_symbols / ai_scores / market_regime など）が存在することを前提とします。初期スキーマはプロジェクトの別スクリプト（schema 初期化）で用意してください。
- OpenAI 呼び出しはレートや課金に注意してください。

---

## 設定管理（kabusys.config の挙動）

- 起動時にプロジェクトルート（.git または pyproject.toml を親ディレクトリから探索）を特定し、プロジェクトルートの `.env` と `.env.local` を自動読み込みします（OS 環境 > .env.local > .env の優先順）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須変数は Settings プロパティ経由で取得され、未設定の場合は ValueError が発生します。
  - settings.jquants_refresh_token（J-Quants）
  - settings.kabu_api_password
  - settings.slack_bot_token / settings.slack_channel_id
  - settings.duckdb_path / settings.sqlite_path（デフォルト値あり）
  - settings.env（development / paper_trading / live）
  - settings.log_level（DEBUG/INFO/...）

---

## ディレクトリ構成（主要ファイル）

（src 以下を基準）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           # 銘柄別ニュース NLP（score_news）
    - regime_detector.py    # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - jquants_client.py     # J-Quants API クライアント（fetch_*/save_*）
    - news_collector.py     # RSS 収集・前処理
    - stats.py              # 統計ユーティリティ（zscore_normalize）
    - quality.py            # データ品質チェック
    - audit.py              # 監査ログスキーマ初期化
    - etl.py                # ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py    # モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py# forward returns, IC, factor summary, rank
  - ai, research 等からの公開 API をパッケージ化

この README はコード内のドキュメント（docstring）を要約したものです。詳細な仕様やスキーマ定義、運用上の注意点（API レート制御、キー管理、トークンリフレッシュ、監査方針等）は該当モジュールの docstring を参照してください。

---

必要であれば、README に以下を追加できます：
- テーブルスキーマ一覧（CREATE TABLE 文）
- 実運用手順（cron / バッチスケジューラ例）
- テストの実行方法とモックの利用方法（OpenAI / HTTP のモック）