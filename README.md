# KabuSys

日本株の自動売買およびデータ基盤ライブラリ（KabuSys）。J-Quants や RSS を用いた市場データ収集、DuckDB ベースのスキーマ、ETL パイプライン、品質チェック、ニュース収集、監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含みます。

- J-Quants API を用いた株価（OHLCV）、財務データ、JPX マーケットカレンダーの取得
- RSS からのニュース収集と銘柄紐付け
- DuckDB による 3 層（Raw / Processed / Feature）データスキーマと初期化
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- 市場カレンダー管理（営業日判定、翌営業日/前営業日の計算）
- 監査（signal → order_request → executions のトレーサビリティ）用スキーマ
- データ品質チェック（欠損、重複、スパイク、日付不整合）

設計上の要点:
- API レート制御（J-Quants: 120 req/min）とリトライ/トークンリフレッシュ実装
- DuckDB への保存は冪等（ON CONFLICT ... DO UPDATE / DO NOTHING）
- ニュース収集は SSRF 対策、XML インジェクション対策、受信サイズ制限などセキュリティに配慮

---

## 主な機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB 保存: 冪等）
  - レート制限・リトライ・トークン自動リフレッシュ
- data.news_collector
  - RSS フィード取得（gzip 対応、SSRF/プライベートホストチェック）
  - 記事正規化、記事ID生成（URL 正規化 → SHA-256 の先頭 32 文字）
  - raw_news / news_symbols への保存（チャンク/トランザクション）
  - 銘柄コード抽出（4桁数字）
- data.schema
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path)／get_connection(db_path)
- data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl（差分取得・バックフィル・品質チェック）
- data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- data.audit
  - 監査用テーブルの初期化（init_audit_schema / init_audit_db）
- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks

---

## 必要環境 / 依存ライブラリ

最低限の推奨環境:
- Python 3.9+（型注釈や Path 機能を利用）
- 必須パッケージ（例）:
  - duckdb
  - defusedxml

開発環境や他のランタイム依存はプロジェクトに合わせて追加してください。

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージをローカル開発モードでインストールする場合:
pip install -e .
```

（requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）

---

## 環境変数 / 設定

KabuSys は .env ファイルまたは OS 環境変数から設定を読み込みます（自動読み込み機能あり）。読み込み順は OS 環境変数 > .env.local > .env です。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（モニタリング等用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

settings は `from kabusys.config import settings` でアクセスできます。

---

## セットアップ手順（手順例）

1. リポジトリをクローン
2. 仮想環境の作成と有効化
3. 必要パッケージをインストール（上記参照）
4. .env を作成して必要な環境変数を設定（.env.example を参考）
5. DuckDB スキーマ初期化

例:
```bash
git clone <repo_url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml

# .env を作成（例）
cat > .env <<EOF
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=zzzzz
SLACK_CHANNEL_ID=CH12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
EOF

# Python REPL またはスクリプトで DB 初期化
python -c "from kabusys.data import schema; schema.init_schema('data/kabusys.duckdb')"
```

---

## 使い方（代表的な例）

以下は主要機能の呼び出し例です。アプリケーション内のスクリプトや cron / Airflow タスクとして利用できます。

- DuckDB スキーマの初期化:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 監査ログ DB の初期化:
```python
from kabusys.data import audit
conn_audit = audit.init_audit_db("data/audit.duckdb")
```

- 日次 ETL の実行（市場カレンダー、株価、財務データ、品質チェックをまとめて実行）:
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブの実行:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄候補セット（抽出用）
known_codes = {"7203", "6758", "9984"}
stats = run_news_collection(conn, known_codes=known_codes)
print(stats)
```

- カレンダー更新バッチ（夜間ジョブ）:
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

- J-Quants から直接データ取得と保存（低レベル例）:
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# トークン省略で settings から読み込み・自動リフレッシュします
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

- 品質チェック単体実行:
```python
from kabusys.data import quality
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 運用に関する注意点 / 実装メモ

- J-Quants クライアントは 120 req/min のレート制限を満たすよう固定スロットリングを実装しています。大量リクエストを並列で投げないでください。
- HTTP エラー（408/429/5xx）は自動リトライ（指数バックオフ、最大3回）されます。401 は自動でリフレッシュを試みます（1回のみ）。
- ニュース収集は SSRF、XML Bomb、大容量レスポンス対策を行っています。RSS URL は必ず http/https スキームである必要があります。
- DuckDB への保存は多くが ON CONFLICT ... DO UPDATE/DO NOTHING を使うため冪等です。ETL は差分取得・バックフィルを行います。
- market_calendar が未取得のときは曜日ベース（土日除外）でフォールバックするため、完全なカレンダーを事前に取得しておくと正確な営業日判定が可能です。
- settings.env の値は "development" / "paper_trading" / "live" のいずれかを指定します。live 実行時は特に十分なテストと安全確認を行ってください。

---

## ディレクトリ構成

（抜粋）ソースは `src/kabusys` 配下に配置されています。主要ファイル:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存）
    - news_collector.py        — RSS ニュース収集・保存・銘柄抽出
    - schema.py                — DuckDB スキーマ定義・初期化
    - pipeline.py              — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py   — カレンダー管理（営業日判定、更新ジョブ）
    - audit.py                 — 監査ログスキーマ初期化
    - quality.py               — データ品質チェック
  - strategy/                   — 戦略モジュール（雛形）
  - execution/                  — 発注／約定管理（雛形）
  - monitoring/                 — 監視・モニタリング（雛形）

---

## よくあるユースケース

- 日次バッチ（Cron / Airflow）で run_daily_etl を実行してデータ基盤を最新化
- RSS 定期収集で raw_news を蓄積し、記事ごとに銘柄を紐付け
- 監査 DB（audit）に signal / order_request / execution の履歴を保存してトレーサビリティを担保
- ETL 後に品質チェック結果を Slack 等に通知して運用アラートを構築

---

## 開発 / 貢献

- 新しい機能や修正は feature ブランチで Pull Request を提出してください。
- 自動テスト、静的解析、型チェック（mypy など）を CI に組み込むことを推奨します。

---

README に記載のない詳細（例: 外部サービスの利用方法、証券会社 API の実装、Slack 通知実装など）は個別に実装してください。必要があれば、サンプルスクリプトや運用ガイドの追記を作成します。