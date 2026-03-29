# KabuSys — 日本株自動売買基盤

KabuSys は日本株向けのデータプラットフォームと研究・自動売買基盤のライブラリ群です。  
J-Quants / RSS / OpenAI 等の外部データソースからデータを取り込み、品質チェック・特徴量生成・ニュース NLP・市場レジーム判定・監査ログ等の機能を提供します。

主な利用用途:
- 日次 ETL による株価 / 財務 / 市場カレンダーの取得と保存（DuckDB）
- ニュース収集・NLP による銘柄単位のセンチメント付与（OpenAI）
- マーケットレジーム判定（ETF とマクロニュースを組合せ）
- 研究用途のファクター計算・特徴量探索
- 監査ログ（signal → order → execution のトレーサビリティ）

---

## 機能一覧

- 環境変数 / .env の自動読み込みと設定管理（kabusys.config）
- J-Quants API クライアント（取得／保存／リトライ・レート制御） — kabusys.data.jquants_client
- 日次 ETL パイプライン（市場カレンダー・株価・財務の差分更新） — kabusys.data.pipeline
- データ品質チェック（欠損・スパイク・重複・日付不整合） — kabusys.data.quality
- カレンダー管理（営業日判定・next/prev 等） — kabusys.data.calendar_management
- ニュース収集（RSS 正規化・SSRF 対策・保存） — kabusys.data.news_collector
- ニュース NLP（OpenAI を使った銘柄ごとのセンチメント付与） — kabusys.ai.news_nlp
- マーケットレジーム判定（ETF MA と LLM によるマクロセンチメント合成） — kabusys.ai.regime_detector
- 研究用モジュール（モメンタム・ボラティリティ・バリュー等） — kabusys.research
- 統計ユーティリティ（Zスコア正規化 等） — kabusys.data.stats
- 監査ログ用スキーマ作成・初期化（DuckDB） — kabusys.data.audit

---

## 前提 / 必要環境

- Python 3.10+
- 外部ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

（requirements.txt がある場合はそれを参照してください。リポジトリにない場合は以下で個別インストール可能です）
```bash
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <repository-url>
cd <repository-dir>
```

2. パッケージを開発モードでインストール（任意）
```bash
pip install -e .
```

3. 環境変数の設定
プロジェクトルートに `.env`（およびローカル上書き用の `.env.local`）を作成します。自動ロードは以下の順序で行われます（OS 環境変数 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 呼び出し時に使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携等で使用）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（モニタリング等で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト `data/monitoring.db`）
- KABUSYS_ENV: `development | paper_trading | live`（デフォルト `development`）
- LOG_LEVEL: `DEBUG | INFO | WARNING | ERROR | CRITICAL`（デフォルト `INFO`）

例 `.env`（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. DuckDB 初期化（任意）
監査ログ用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（主要な呼び出し例）

Python からライブラリを直接利用する想定です。以下は代表的な呼び出し例です。

- 日次 ETL を実行（DuckDB 接続を渡す）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（指定日のウィンドウで raw_news / news_symbols を参照して ai_scores に書き込む）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written: {written}銘柄")
```

- マーケットレジーム判定（ETF 1321 の MA とマクロニュースの LLM 評価を合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- RSS フィードの取得（news_collector の低レベル関数）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

- 監査ログスキーマを既存 DB に適用
```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

注意点:
- OpenAI 呼び出しは API キーが必須（関数引数で渡すか `OPENAI_API_KEY` を環境変数としてセット）。
- DuckDB の接続は呼び出し側で管理します（ファイルパスは `DUCKDB_PATH` で指定可能）。

---

## よく使う API（サマリ）

- kabusys.config.settings — 環境設定アクセス
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl, ETLResult
- kabusys.data.quality
  - run_all_checks（品質チェック一括実行）
- kabusys.data.news_collector
  - fetch_rss（RSS 取得）
- kabusys.ai.news_nlp
  - score_news（銘柄単位のニュース NLP＋ai_scores 書込）
- kabusys.ai.regime_detector
  - score_regime（market_regime テーブルにレジーム判定を書き込む）
- kabusys.data.audit
  - init_audit_schema / init_audit_db（監査ログ初期化）

---

## 環境変数詳細（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（gpt 呼び出しに使用）
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値が設定されていれば無効）

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内 `src/kabusys` 以下の主要なファイル・モジュール構成です（抜粋）。

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
      - calendar_management.py
      - stats.py
      - quality.py
      - audit.py
      - (その他: schema / clients / helpers が想定される)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/ (他モジュール)
    - (strategy/, execution/, monitoring/ は __all__ に含まれる設計上の名前空間として存在する可能性あり)

各モジュールには docstring と実装上の設計方針（Look-ahead バイアス対策、冪等性、ロギング、リトライ）が含まれています。実運用では DuckDB のスキーマ作成や適切な権限・トークン管理を行ってください。

---

## 開発・テストのヒント

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。テスト時に自動読み込みを抑えるには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは内部で `_call_openai_api` を経由しているため、ユニットテストでは対象関数を patch / mock して API 呼び出しを差し替え可能です（各モジュール内でドキュメントあり）。
- DuckDB をインメモリで使う場合は `":memory:"` を渡せます（例: `duckdb.connect(":memory:")`）。
- ニュース収集では defusedxml を使って XML関連の脆弱性対策を行っています。RSS の取得処理は SSRF 対策も含まれます。

---

## 参考・注意点

- 本ライブラリはデータ取得・研究・監査ログのための基盤コンポーネント群であり、実際の発注ロジック（kabu ステーションとの発注送信や資金管理ルール）を含む場合は追加実装が必要です。
- 本番（live）環境での利用時は `KABUSYS_ENV=live` を設定し、ログレベルやシークレット管理に注意してください。
- 外部 API の呼び出し（J-Quants / OpenAI）は利用規約や課金に留意して実行してください。

---

もし README に含めて欲しい追加の使い方（CI 設定、具体的なスキーマ定義、バックテスト用ユーティリティのドキュメント等）があれば教えてください。必要に応じてサンプル .env.example や簡易スキーマ作成スクリプトも作成します。