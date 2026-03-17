# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants API や RSS を用いたデータ収集から、DuckDB によるスキーマ管理、日次 ETL、品質チェック、監査ログまでを一貫して提供します。

主な設計方針は「冪等性」「トレーサビリティ」「運用安全性（SSRF/DoS対策・APIレート制御）」です。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（サンプル）
- 環境変数
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買やデータ基盤のためのユーティリティ群です。主に次の領域をカバーします。

- J-Quants API クライアント（株価・財務・マーケットカレンダー取得）
  - レート制御、リトライ、ID トークン自動リフレッシュを実装
- RSS ベースのニュース収集（トラッキングパラメータ除去、SSRF 対策、gzip/サイズ制限）
- DuckDB を用いたスキーマ定義と初期化（Raw/Processed/Feature/Execution/Audit 層）
- ETL パイプライン（日次差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定・次/前営業日検索）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- 監査ログ（signal → order_request → executions のトレーサビリティ）

目的：データの取得から品質管理、戦略の入出力、発注監査まで運用を想定した堅牢な基盤を提供すること。

---

## 機能一覧

- J-Quants クライアント
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - RateLimiter（120 req/min）、指数バックオフリトライ、401時のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）

- ニュース収集
  - RSS フィード取得（defusedxml による安全な XML パース）
  - URL 正規化（utm 等トラッキング除去）、SHA-256 ベースの記事 ID（先頭32文字）
  - SSRF 対策（スキーム検証、プライベートIP拒否、リダイレクト検査）
  - レスポンスサイズ制限、gzip 解凍時の検査
  - DuckDB へのバルク冪等保存（INSERT ... RETURNING を利用）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス作成、初期化関数（init_schema / init_audit_db）

- ETL パイプライン
  - 差分更新 (最終取得日からの差分取得)
  - backfill による後出し修正の吸収
  - 日次一括処理 run_daily_etl（カレンダー → 株価 → 財務 → 品質チェック）

- 品質チェック
  - 欠損データ、主キー重複、スパイク（前日比閾値）、日付不整合（未来日 / 非営業日のデータ）

- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間バッチ更新

- 監査ログ（audit）
  - signal_events, order_requests, executions テーブル等による完全なトレーサビリティ
  - UTC タイムゾーン固定、冪等キー（order_request_id / broker_execution_id）設計

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに `X | None` を使用しているため）
- DuckDB を利用（ローカルファイルまたは :memory:）

1. リポジトリをクローン / ソースを取得
   - 例: git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な最低限の外部パッケージ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数の準備
   - プロジェクトルートに .env ファイルを置くと自動で読み込まれます（自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数は README の「環境変数」セクション参照。

5. DuckDB スキーマ初期化（サンプル）
   - Python REPL またはスクリプトで:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")

6. 監査用スキーマを追加（必要に応じて）
   - from kabusys.data.audit import init_audit_db
   - audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   - もしくは既存 conn に init_audit_schema(conn)

---

## 使い方（サンプル）

以下は基本的な利用例です。適宜ログ設定や例外処理を追加してください。

- スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行（J-Quants トークンは settings が環境変数から取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードセット（例: {"7203", "6758"}）を渡すと抽出・紐付けを実行
stats = run_news_collection(conn, known_codes={"7203", "6758"})
print(stats)  # {source_name: saved_count, ...}
```

- カレンダー夜間更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} calendar rows")
```

- 品質チェック単体実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

- J-Quants トークン取得（明示的に使用する場合）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.JQUANTS_REFRESH_TOKEN を使用
```

---

## 環境変数

KabuSys は .env ファイルまたは OS 環境変数から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` と `.env.local` を順に読み込みます。

必須
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabu API 用パスワード（kabuステーション連携用）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV           : one of {"development", "paper_trading", "live"} （デフォルト: development）
- LOG_LEVEL             : one of {"DEBUG","INFO","WARNING","ERROR","CRITICAL"} （デフォルト: INFO）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite モニタリング DB（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : "1" を設定すると .env 自動読み込みを無効化

※ .env.example を参考に .env を作成してください（プロジェクトに .env.example があれば併せてご利用ください）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（取得・保存）
      - news_collector.py      # RSS ニュース収集器（SSRF対策・正規化・保存）
      - schema.py              # DuckDB スキーマ定義・初期化
      - pipeline.py            # ETL パイプライン（差分更新・日次ETL）
      - calendar_management.py # マーケットカレンダー管理
      - audit.py               # 監査ログ用スキーマ初期化
      - quality.py             # データ品質チェック
    - strategy/
      - __init__.py            # 戦略関連（拡張ポイント）
    - execution/
      - __init__.py            # 発注・実行関連（拡張ポイント）
    - monitoring/
      - __init__.py            # 監視・メトリクス用（拡張ポイント）

上記のモジュール群は、戦略や発注ロジックを別途実装して組み合わせることを想定しています。データ収集・品質管理・監査はこのライブラリで担保し、strategy / execution 層は運用チームが実装して接続します。

---

補足・運用上の注意
- J-Quants API のレート制限（120 req/min）を尊重してください。ライブラリは内部でスロットリングを行いますが、大量並列呼び出しは避けてください。
- DuckDB のファイルを共有する場合、排他制御や接続設計に注意してください（運用環境の要件に応じて接続戦略を設計してください）。
- ニュース収集時は外部 RSS を定期取得するため、ソースの安定性や利用規約を確認してください。
- テスト時に .env の自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

ライセンス・貢献
- （このリポジトリに LICENSE があればそちらを参照してください）
- バグ報告・機能追加は Issue / PR でお寄せください。

---

以上が README の概要です。必要であれば、インストール・デプロイの具体的な CI/CD 例や systemd ジョブ / cron 設定、より詳細な API リファレンス（各関数の引数/戻り値例）を追加で作成します。どの情報を拡張しますか？