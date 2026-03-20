# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ集合です。  
DuckDB を中心にデータ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログ管理などを備え、研究（research）と運用（execution）を分離した設計になっています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群からなるパッケージです。

- J-Quants API から株価・財務・マーケットカレンダーを取得（rate limit / retry / token refresh 対応）
- DuckDB によるデータスキーマ・永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 特徴量エンジニアリング（research モジュールで計算した生ファクターの正規化・保存）
- シグナル生成（複数コンポーネントスコアの統合・BUY/SELL 生成）
- ニュース収集（RSS 取得・正規化・銘柄抽出・DB 保存、SSRF 対策）
- マーケットカレンダー管理（営業日判定・next/prev/trading days）
- 監査ログ（signal→order→execution のトレーサビリティ）

設計方針として、ルックアヘッドバイアス排除、冪等性（DB 挿入の ON CONFLICT 対応）、外部 API への適切なリトライ、テスト容易性（id_token 注入等）を重視しています。

---

## 機能一覧（主な提供 API）

- kabusys.config.Settings
  - 環境変数経由の設定取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）
  - 自動 .env ロード（プロジェクトルートの .env / .env.local、無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）
- kabusys.data.schema
  - init_schema(db_path) / get_connection(db_path)
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB への冪等保存）
- kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl（統合日次 ETL）
- kabusys.data.news_collector
  - fetch_rss / save_raw_news / run_news_collection（SSRF 対策・gzip/サイズ制御・ID 正規化）
- kabusys.research
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量探索用）
- kabusys.strategy
  - build_features（Z スコア正規化・ユニバースフィルタ・features テーブルへの upsert）
  - generate_signals（ai_scores と統合して final_score を算出、BUY/SELL を signals テーブルへ upsert）
- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job

---

## セットアップ手順

※ 以下は一般的な開発環境セットアップの例です。プロジェクトに requirements.txt や pyproject.toml がある場合はそちらを優先してください。

1. Python 環境（推奨: 3.9+）を準備
   - 仮想環境の作成（例）:
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - 最低必要ライブラリ（コード参照）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （実運用では logging / その他の補助パッケージも使うことが想定されます）

3. パッケージを開発モードでインストール（任意）
   - プロジェクトルートで:
     - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 の場合は無効）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN (J-Quants の refresh token)
     - KABU_API_PASSWORD (kabuステーション API 用パスワード)
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
     - KABU_API_BASE_URL — kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）

   - .env の例 (.env.example):
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
     - KABU_API_PASSWORD=your_kabu_password_here
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C0123456789
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO
     - DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（代表的な操作例）

以下は Python スクリプトや REPL からの利用例です。

1. DuckDB スキーマの初期化

例: db ファイルを作成して全テーブルを初期化する

```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

2. 日次 ETL を実行する

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3. 特徴量を作成して features テーブルに保存

（research の生ファクターを使って Z スコア正規化等を行います）

```python
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4. シグナルを生成して signals テーブルへ保存

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date.today())
print(f"signals written: {n}")
```

5. ニュース収集ジョブ（RSS）

```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# sources は {source_name: rss_url}。省略時は既定のソースを使用。
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)  # {source_name: saved_count}
```

6. J-Quants からのデータフェッチ（テスト等）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
# id_token を明示的に渡すこともできる
quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

注意:
- 上記はパッケージ内部 API を直接呼ぶ例です。実運用では CLI ラッパーやジョブスケジューラ（cron, systemd, Airflow など）から呼び出すことを推奨します。
- run_daily_etl は各ステップでエラーハンドリングを行い、品質チェックの結果や発生エラーを ETLResult に集約して返します。

---

## 環境変数（主要なキー）

- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
  - KABU_API_PASSWORD — kabuステーション API 接続用パスワード
  - SLACK_BOT_TOKEN — Slack 通知用 Bot Token
  - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

- 任意／デフォルトあり:
  - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
  - LOG_LEVEL — ログレベル（デフォルト INFO）
  - KABU_API_BASE_URL — kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ data/
│     │  ├─ __init__.py
│     │  ├─ schema.py
│     │  ├─ jquants_client.py
│     │  ├─ pipeline.py
│     │  ├─ news_collector.py
│     │  ├─ stats.py
│     │  ├─ calendar_management.py
│     │  └─ audit.py
│     ├─ research/
│     │  ├─ __init__.py
│     │  ├─ factor_research.py
│     │  └─ feature_exploration.py
│     ├─ strategy/
│     │  ├─ __init__.py
│     │  ├─ feature_engineering.py
│     │  └─ signal_generator.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/   # モニタリング関連（placeholder）
└─ README.md
```

---

## 開発・テストのヒント

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml の存在）を基準に行われます。テストで自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化は init_schema() を一度だけ呼べば OK（既存テーブルは無視されるため冪等）。
- network／API 周りのテストは J-Quants 呼び出しをモックするか、id_token を注入して行ってください（jquants_client の関数は id_token 引数を受け取れます）。
- news_collector は外部ネットワークアクセスを行うため、ユニットテストでは fetch_rss / _urlopen をモックしてください。

---

## ライセンス / 責務

本 README はコードベースから抽出した概要・使い方を示すものであり、実運用に際してはテスト・追加の監査・コンプライアンス確認を必ず行ってください。J-Quants や各 API の利用規約に従って使用してください。

---

必要であれば、README に以下を追加できます：
- requirements.txt の推奨セット
- CLI/サンプルスクリプト（cron 用 wrapper）
- .env.example の完全版テンプレート
- 詳細なテーブル定義（DataSchema.md 抜粋）

どれを追加したいか教えてください。