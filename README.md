# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）。  
J-Quants API・RSSニュース・DuckDB を利用したデータ取得・ETL・品質チェック、監査ログやマーケットカレンダー管理、発注/実行関連のスキーマを提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- RSS フィードからのニュース収集と銘柄紐付け（SSRF/XML攻撃対策・トラッキング除去）
- DuckDB ベースの三層データレイヤ（Raw / Processed / Feature）と実行・監査テーブル定義
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理、監査ログ初期化機能
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴：
- API レート制御（J-Quants: 120 req/min）
- 冪等性を意識した保存（ON CONFLICT / RETURNING を活用）
- Look-ahead bias を防ぐための fetched_at/UTC 時刻管理
- セキュリティ対策（defusedxml、SSRF チェック、受信サイズ制限 など）

---

## 機能一覧

主なモジュールと機能（抜粋）:

- kabusys.config
  - 環境変数の自動ロード（`.env` / `.env.local`、ただしプロジェクトルート検出あり）
  - settings オブジェクト経由で設定取得（必須トークンの強制チェック）
  - 主要 env 名: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンからの idToken 取得）
  - save_* 系関数で DuckDB へ冪等格納

- kabusys.data.news_collector
  - fetch_rss / preprocess_text / save_raw_news / save_news_symbols / run_news_collection
  - RSS パースは defusedxml を利用、URL 正規化・トラッキング除去、記事 ID を SHA256 で生成

- kabusys.data.schema
  - init_schema(db_path) : DuckDB に全テーブル・インデックスを作成
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, ...) : カレンダー → 株価 → 財務 → 品質チェック の日次 ETL
  - run_prices_etl / run_financials_etl / run_calendar_etl 等

- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job

- kabusys.data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - QualityIssue データクラスで結果を返す

- kabusys.data.audit
  - init_audit_schema / init_audit_db : 監査ログ用スキーマ（signal_events, order_requests, executions）初期化

その他: execution / strategy / monitoring 用のパッケージ用意（インターフェースや拡張を想定）

---

## セットアップ手順

前提: Python 3.9+（コードの typing 構文より）を想定。プロジェクトルートに pyproject.toml や .git があると自動 .env ロードが働きます。

1. 仮想環境と依存のインストール（例）
   - 仮想環境作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - 必要パッケージ（最低限）:
     - pip install duckdb defusedxml

   補足: 実行環境に応じて追加ライブラリ（slack-sdk など）をインストールしてください。

2. 環境変数の準備
   プロジェクトルートに `.env`（または `.env.local`）を置くと kabusys.config が自動読み込みします。例:

   ```
   # .env の例（機密情報は実運用で安全に管理してください）
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

3. データベース初期化
   - DuckDB スキーマを初期化する例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ用 DB 初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（簡易ガイド）

以下は典型的なワークフローのサンプルコードです。

- settings を使う（環境変数取得）
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 未設定なら例外
print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（最小例）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を明示することも可能
print(result.to_dict())
```

- ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は既知銘柄コードの集合（例: {"7203", "6758", ...}）
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)  # {source_name: 新規保存数}
```

- J-Quants 直接利用（ID トークン取得・フェッチ）
```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # refresh token は settings を参照
records = jq.fetch_daily_quotes(id_token=id_token, code="7203", date_from=..., date_to=...)
jq.save_daily_quotes(conn, records)
```

- 品質チェックだけ実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=...)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

- マーケットカレンダー判定
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
print(is_trading_day(conn, date(2026, 1, 1)))
print(next_trading_day(conn, date(2026, 1, 1)))
```

注意点:
- J-Quants API はレート上限があり、jquants_client は内部でスロットリング・リトライを行います。
- get_id_token はリフレッシュトークンに基づいて idToken を取得します（settings.jquants_refresh_token を利用）。
- news_collector は SSRF や XML Bomb を防ぐ対策を含みます。外部に URL を渡す際は注意してください。

---

## ディレクトリ構成

（リポジトリの主要ファイル構成の概略）

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py
   │  ├─ news_collector.py
   │  ├─ schema.py
   │  ├─ pipeline.py
   │  ├─ calendar_management.py
   │  ├─ audit.py
   │  └─ quality.py
   ├─ strategy/
   │  └─ __init__.py
   ├─ execution/
   │  └─ __init__.py
   └─ monitoring/
      └─ __init__.py
```

主要ファイルの説明:
- config.py: 環境変数ロードと Settings オブジェクト
- data/*.py: データ取得、ETL、スキーマ、品質チェック、ニュース収集、監査スキーマ
- strategy/, execution/, monitoring/: 将来の戦略・発注・監視ロジック用パッケージ（インターフェース層）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーションAPI パスワード
- KABU_API_BASE_URL (任意) — デフォルト "http://localhost:18080/kabusapi"
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH (任意) — デフォルト "data/kabusys.duckdb"
- SQLITE_PATH (任意) — デフォルト "data/monitoring.db"
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

---

## 開発上の注意 / ベストプラクティス

- 秘密情報（トークン等）は `.env` に置く場合でもアクセス権限を制御し、CI/CD ではシークレット管理を使用してください。
- 自動 .env ロードはプロジェクトルート検出に依存します。テスト時など自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB はファイルベースで軽量に扱えますが、バックアップやバージョン管理は運用方針に合わせてください。
- 実運用での発注（live）の際は KABUSYS_ENV を `live` にし、安全なテスト（paper_trading）を十分に行ってください。

---

## ライセンス / 貢献

（ここにライセンス情報や貢献手順を追記してください）

---

README は以上です。必要であればサンプルスクリプト（cron 用、systemd 用、Docker 用）や追加の環境変数例、CI 用セットアップ手順も作成します。どの形式が良いか教えてください。