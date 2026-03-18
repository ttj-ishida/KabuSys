# KabuSys

KabuSys は日本株の自動売買およびデータプラットフォーム用のライブラリ群です。  
J-Quants などの API から市場データ・財務データ・ニュースを取得して DuckDB に蓄積し、ETL、品質チェック、監査ログ、カレンダー管理など自動売買システムに必要な基盤処理を提供します。

バージョン: 0.1.0

---

## 主要機能

- 環境変数/設定管理
  - .env ファイル自動読み込み（プロジェクトルート検出）
  - 必須項目チェック（settings オブジェクト経由）
- データ取得（J-Quants API クライアント）
  - 株価日足（OHLCV）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
  - レート制限管理、リトライ（指数バックオフ）、トークン自動リフレッシュ、fetched_at 記録、冪等保存（ON CONFLICT）
- ニュース収集
  - RSS 取得（SSRF 対策、gzip 対応、XML 安全パース）
  - URL 正規化・記事 ID (SHA-256) 生成
  - DuckDB へ冪等保存（INSERT ... RETURNING）
  - テキスト前処理・銘柄コード抽出
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス作成
  - 監査ログ（signal / order_request / executions）スキーマの初期化
- ETL パイプライン
  - 差分更新（最終取得日ベース）、バックフィル、カレンダー先読み
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL エントリポイント
- マーケットカレンダー管理
  - 営業日判定、次/前営業日取得、期間内営業日取得
  - 夜間カレンダー更新ジョブ
- データ品質チェック
  - 複数チェックをまとめて実行、QualityIssue 型で結果を返却
- 監視・発注・戦略レイヤーのための基盤（strategy / execution / monitoring 向けのモジュール枠組み）

---

## 前提条件 / 要件

- Python 3.10 以上（型アノテーションに Path | None などを使用）
- 必要な Python ライブラリ（例）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API 等）および適切な API トークン

実際のプロジェクトで使用する場合は pyproject.toml / requirements.txt を参照し、追加ライブラリを導入してください。

---

## インストール

開発リポジトリをチェックアウトした後、仮想環境を作成して依存をインストールします（例）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# 依存パッケージをインストール（プロジェクトの requirements.txt / pyproject.toml に従ってください）
pip install duckdb defusedxml
# 開発インストール（プロジェクトルートに pyproject.toml がある場合）
pip install -e .
```

---

## 環境変数（.env）

プロジェクトはプロジェクトルート（.git または pyproject.toml）を基準に `.env` と `.env.local` を自動で読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（例）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

例 (.env):

```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=xxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

settings は kabusys.config.settings から利用できます。必須項目が未設定の場合は ValueError が発生します。

---

## セットアップ手順（簡易ガイド）

1. リポジトリをクローンし仮想環境を作成、依存をインストールする。
2. .env を作成して必要なキーを設定する。
3. DuckDB スキーマを初期化する。

Python での例:

```python
from kabusys.data import schema

# ファイルを作成してスキーマを初期化（親ディレクトリがなければ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

監査ログ用 DB を別に作る場合:

```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方

以下に主要なユースケースのコード例を示します。

- J-Quants のトークン取得:

```python
from kabusys.data import jquants_client as jq

# settings.jquants_refresh_token を使って id_token を取得
id_token = jq.get_id_token()
```

- 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）:

```python
from kabusys.data import pipeline, schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- RSS ニュース収集と保存:

```python
from kabusys.data import news_collector as nc, schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
# 既定のソースから収集して保存
stats = nc.run_news_collection(conn, known_codes={"7203", "6758"})
print(stats)  # {source_name: saved_count}
```

- 個別 API 取得関数の利用例:

```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
# 銘柄 7203 の過去 7 日の株価を取得して保存
records = jq.fetch_daily_quotes(code="7203", date_from=date(2026,3,1), date_to=date(2026,3,7))
saved = jq.save_daily_quotes(conn, records)
```

- 品質チェックの実行:

```python
from kabusys.data import quality, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today())
for issue in issues:
    print(issue)
```

注意点:
- API 呼び出しは rate limit を守る設計ですが、実際の運用では外部制約（ネットワーク、API 利用規約）を確認してください。
- ETL 関数では例外を個別に捕捉して処理を継続する仕様です。戻り値の ETLResult でエラー・品質問題を確認してください。

---

## ディレクトリ構成

主要ファイル/ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存）
    - news_collector.py        — RSS ニュース収集 / 前処理 / 保存
    - schema.py                — DuckDB スキーマ定義と初期化
    - pipeline.py              — ETL パイプライン（差分更新、日次 ETL）
    - calendar_management.py   — マーケットカレンダー管理（営業日ロジック）
    - audit.py                 — 監査ログ・トレーサビリティ用スキーマ初期化
    - quality.py               — データ品質チェック
  - strategy/                  — 戦略モジュール用のパッケージ（枠組み）
  - execution/                 — 発注・約定処理用のパッケージ（枠組み）
  - monitoring/                — 監視用のパッケージ（枠組み）

ファイル名は README 作成時点の実装を反映しています。プロジェクト拡張時に追加のモジュールが入ります。

---

## よくあるトラブルシューティング

- ValueError: 環境変数が設定されていない
  - settings のプロパティは必須キーが無ければ ValueError を発生させます。`.env` に必要なキーを追加してください。

- DuckDB に接続できない / パスのディレクトリがない
  - schema.init_schema() は親ディレクトリを自動作成しますが、パーミッション等で失敗することがあります。書き込み権限を確認してください。

- RSS のパースに失敗してデータが取れない
  - 不正な XML や大きすぎるレスポンスは安全のためスキップされます。ログ（logger）を確認して原因を特定してください。

- API レート制限や 401 エラー
  - jquants_client はレート制御・リトライ・トークン自動リフレッシュを備えています。トークンが無効な場合は refresh token を確認してください。

---

## 貢献 / 拡張

- strategy, execution, monitoring モジュールは枠組みを提供しており、ここに具体的な戦略ロジックやブローカー連携、監視ダッシュボードを実装していく想定です。
- ETL や品質チェックの追加、ニュースソースの拡張、監査スキーマの拡張などは既存の設計方針（冪等性・トレーサビリティ・セキュリティ）に従って実装してください。

---

詳しい API や内部設計（DataPlatform.md 等の設計ドキュメント）がある場合は併せて参照してください。README に記載の使い方は最小限の入門例です。運用時はログ設定や例外処理、バックアップ、機密情報の管理等に注意してください。