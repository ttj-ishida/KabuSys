# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
J-Quants や kabuステーション、OpenAI を組み合わせてデータ取得・ETL、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログ（トレーサビリティ）などを行うためのモジュール群を提供します。

主な設計方針は「バックテストでのルックアヘッドバイアス防止」「DuckDB を中心とした冪等 ETL」「外部 API の堅牢なリトライ／レート制御」「監査・トレーサビリティの強化」です。

---

## 機能一覧

- 環境変数 / 設定管理
  - 自動的にプロジェクトルートの `.env` / `.env.local` を読み込み（上書き順あり）
  - 必須設定の取得・検証（Settings クラス）

- データプラットフォーム（kabusys.data）
  - J-Quants API クライアント（認証、ページネーション、レート制御、再試行、DuckDB 保存）
  - ETL パイプライン（株価、財務、カレンダーの差分取得・保存・品質チェック）
  - 市場カレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS → raw_news、SSRF / XML パース / サイズ検査あり）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ（signal / order_request / execution テーブルの初期化・ユーティリティ）
  - 汎用統計ユーティリティ（Zスコア正規化 等）

- AI（kabusys.ai）
  - ニュース NLP（gpt-4o-mini を使った銘柄別センチメント集約と ai_scores への書き込み）
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成）

- Research（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. Python 仮想環境を作成・有効化（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実行環境によっては追加パッケージが必要になる可能性があります。プロジェクトに requirements.txt があればそれを使用してください。

4. 環境変数の用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を配置すると自動で読み込まれます。
   - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化できます（テスト用途）。

   代表的な環境変数（必須のものは README 内でも明記）:

   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
   - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
   - SLACK_CHANNEL_ID (必須) — Slack チャネル ID
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV — 環境（development / paper_trading / live、デフォルト: development）
   - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

   .env の簡単な例（.env.example）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化（監査用など）
   - DuckDB のスキーマ作成や監査テーブル初期化はコード上のユーティリティで実行します（後述の使用例参照）。

---

## 使い方（基本例）

以下は Python スクリプト / REPL からの利用例です。日付は datetime.date 型を使います。

- DuckDB に接続して日次 ETL を実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP による銘柄スコアリング（ai_scores へ書き込む）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"wrote {n_written} scores")
```

- 市場レジームスコア算出
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査用 DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って注文監査ログを記録・参照できます
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意:
- OpenAI 呼び出しには API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必要です。
- 多くの関数は「ルックアヘッドバイアス防止」のため内部で date.today() を直接参照しません。必ず target_date を明示することが推奨されます。

---

## 重要な設計・運用上の注意

- 自動環境変数読み込み:
  - パッケージロード時にプロジェクトルートの `.env` → `.env.local` を読み込みます。OS 環境変数を保護しつつローカル上書きを許容する仕様です。無効化は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- OpenAI 呼び出し:
  - gpt-4o-mini を想定した JSON Mode を利用。429 / ネットワーク断 / タイムアウト / 5xx 等に対して指数バックオフでリトライします。API キー未提供時は例外を投げます。

- J-Quants クライアント:
  - レート制限（120 req/min）を守るための RateLimiter を実装。
  - 401 を検知した場合はリフレッシュトークンで ID トークンを更新してリトライします。
  - DuckDB への保存は ON CONFLICT DO UPDATE を使って冪等性を確保。

- ニュース収集:
  - RSS に対して SSRF 対策（ホストのプライベートチェック、リダイレクト検査）、XML の安全パーサ（defusedxml）、最大レスポンスバイト数チェックを行います。

- データ品質:
  - 欠損（OHLC）、重複、スパイク、将来日付や市場カレンダーとの不整合を検出するチェック群があります。ETL はチェックでエラーが出ても基本的に続行し、呼び出し元で対処を行う設計です。

---

## ディレクトリ構成

主要なファイル / モジュール:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - pipeline.py (ETLResult 再エクスポート)
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- src/kabusys/research/*（ファクター・探索ユーティリティ）

（上記はこのリポジトリ内に含まれる主要モジュールの一覧です）

---

## 付録：よく使うユーティリティ関数一覧

- Settings（kabusys.config.settings）:
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.kabu_api_base_url
  - settings.slack_bot_token
  - settings.slack_channel_id
  - settings.duckdb_path
  - settings.sqlite_path
  - settings.env / is_live / is_paper / is_dev
  - settings.log_level

- ETL / Data:
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)

- AI:
  - score_news(conn, target_date, api_key=None)
  - score_regime(conn, target_date, api_key=None)

- Data utilities:
  - init_audit_db(db_path)
  - init_audit_schema(conn, transactional=False)

---

この README はコードベースの主要機能と使い方の概要をまとめたものです。詳細な API やパラメータ、戻り値の仕様は各モジュールの docstring を参照してください。必要であればサンプルスクリプトや運用手順（cron ジョブ、監視、Slack 通知の設定例など）も追記できます。どの部分を深掘りしますか？