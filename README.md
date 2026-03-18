# KabuSys

KabuSys は日本株の自動売買基盤向けに設計された Python パッケージです。J-Quants API や RSS フィードから市場データ／ニュースを取得して DuckDB に保存し、ETL・品質チェック・マーケットカレンダー管理・監査ログを提供します。戦略層や実行（ブローカー連携）層と組み合わせて自動売買システムを構築するための基盤モジュール群が含まれます。

バージョン: 0.1.0

---

## 主な機能

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務諸表、JPX マーケットカレンダー取得
  - レートリミット（120 req/min）対応、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアスを回避

- データ永続化（DuckDB）
  - Raw / Processed / Feature / Execution の層ごとのスキーマ定義
  - 冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）をサポートする保存ユーティリティ

- ETL パイプライン
  - 差分取得（最終取得日からの差分・バックフィル）、保存、品質チェックを統合
  - 日次 ETL エントリポイント（run_daily_etl）

- データ品質チェック
  - 欠損、スパイク（前日比）、重複、日付整合性チェック（run_all_checks）

- ニュース収集
  - RSS フィード取得、XML パース防御（defusedxml）、SSRF 対策、トラッキングパラメータ除去
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等保存
  - 銘柄コード抽出と news_symbols への紐付け

- マーケットカレンダー管理
  - カレンダー差分更新ジョブ（calendar_update_job）
  - 営業日判定・前後営業日取得・期間内営業日リスト取得等のユーティリティ

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティを確保する監査スキーマと初期化ユーティリティ

---

## 前提条件

- Python 3.10 以上（typing の union 型表記（|）などを使用）
- 必要な Python パッケージ（最低限）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# またはプロジェクトに requirements.txt / pyproject.toml があればそれに従ってください
```

---

## 環境変数 / 設定

KabuSys はプロジェクトルート (.git または pyproject.toml があるディレクトリ) にある `.env` / `.env.local` を自動的に読み込みます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須の環境変数（Settings により参照されるもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID — Slack 投稿先チャンネル ID

任意 / デフォルト
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: 必須変数が未設定の場合は Settings の accessor が ValueError を投げます。

---

## セットアップ手順（簡易）

1. リポジトリをクローンし、仮想環境を作成して有効化
2. 必要パッケージをインストール（duckdb, defusedxml など）
3. プロジェクトルートに `.env` を作成して環境変数を設定
4. DuckDB スキーマを初期化

例:
```bash
git clone <repo>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml

# .env を作成（上記の必須 vars を設定）
# Python REPL またはスクリプトでスキーマ初期化
python - <<'PY'
from kabusys.config import settings
from kabusys.data.schema import init_schema
conn = init_schema(settings.duckdb_path)
print("DuckDB initialized at", settings.duckdb_path)
conn.close()
PY
```

監査ログ用 DB を別に作る場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
audit_conn.close()
```

---

## 使い方（主要 API）

以下はライブラリの主要な使い方例です。実運用時はログ管理やエラーハンドリングを追加してください。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

- 日次 ETL を実行（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を渡せば任意日で実行可能
print(result.to_dict())
```

- ニュース（RSS）収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードのセット（抽出精度向上のため渡すとよい）
known_codes = {"7203", "6758", "9432"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

- マーケットカレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

- 監査ログ（Audit）初期化（既存 conn にテーブルを追加）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- J-Quants 低レベル呼び出し（テストやカスタム取得に）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 品質チェックを単独実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)  # ここで issues は QualityIssue のリスト
```

---

## 注意点 / 設計上のポイント

- J-Quants API のレート制限（120 req/min）を厳守するため内部で固定間隔スロットリングを実装しています。
- API 呼び出しは最大リトライ（指数バックオフ）を行い、401 時には自動でリフレッシュを試みます（1 回のみ）。
- DuckDB への保存は冪等性を重視しています（ON CONFLICT 句を活用）。
- RSS 収集は SSRF・XML Bomb 等の攻撃に対する防御（スキーム検証、プライベートアドレス拒否、defusedxml、受信サイズ上限）を行っています。
- 日次 ETL は Fail-Fast とせず、可能な限り全データを収集して品質チェック結果を呼び出し元に返す方針です。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定読み込み
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント、取得・保存関数
  - news_collector.py — RSS 収集、保存、銘柄抽出
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - schema.py — DuckDB スキーマ定義と init_schema
  - calendar_management.py — マーケットカレンダー管理
  - quality.py — データ品質チェック
  - audit.py — 監査ログ（信号→発注→約定のトレース）
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

（上記ファイル群が主要なモジュールです。strategy や execution、monitoring はプレースホルダとして用意されています。）

---

## 開発 / テスト

- 自動で .env を読み込む処理は、テスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで無効化できます。
- 各モジュールは外部依存（HTTP・DB）を注入しやすい形で設計されています（例: id_token を引数で渡せる、_urlopen をモックできる等）。ユニットテストでは外部呼び出しをモックして検証してください。

---

## 参考・サポート

- ソースコード内に各機能の設計方針・注意点がコメントで記載されています。実運用での運用ルール（本番環境では KABUSYS_ENV=live、適切なログ設定、Slack 通知設定等）を整備してください。

---

README の内容や使い方で不明点があれば、どの操作（ETL、ニュース収集、監査初期化 など）について詳しく知りたいか教えてください。必要であればサンプルスクリプトや systemd / cron 用の実行例も作成します。