# KabuSys

日本株自動売買システムのコアライブラリ（データ収集・ETL・品質チェック・監査ログ・戦略・発注基盤の下地）

このリポジトリは、J-Quants や RSS 等からのデータ収集、DuckDB によるデータ保管、日次 ETL、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）など、自動売買システムに必要な基盤機能を提供します。

主な設計方針
- 冪等性（DB 保存は ON CONFLICT を活用）
- レート制御・リトライ・トークン自動更新（API 呼び出しでの安定性確保）
- Look-ahead bias 回避のため取得時刻（fetched_at）を記録
- セキュリティ対策（RSS の SSRF 対策、defusedxml による XML 攻撃防止、レスポンスサイズ制限 等）
- ETL と品質チェックは独立したエラーハンドリングで継続処理を優先

---

## 機能一覧

- 環境設定
  - .env / .env.local 自動読み込み（プロジェクトルートは .git または pyproject.toml を探索）
  - 必須・デフォルト設定の管理（Settings クラス）
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- データ取得（J-Quants）
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レートリミット（120 req/min）、指数バックオフによるリトライ、401 時のトークン自動リフレッシュ
  - ページネーション対応、取得時刻（UTC）記録

- ニュース収集（RSS）
  - RSS フィード取得、記事の前処理（URL 除去・空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証・リダイレクト検査・内部アドレス拒否）
  - レスポンスサイズ上限（デフォルト 10MB）、gzip 解凍と Gzip bomb 対策
  - DuckDB に冪等保存（INSERT ... ON CONFLICT / RETURNING）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義および初期化
  - インデックス定義、外部キー順のテーブル作成
  - audit 用スキーマ（signal_events / order_requests / executions）

- ETL パイプライン
  - 日次 ETL（市場カレンダー→株価→財務→品質チェック）
  - 差分更新（最終取得日を基に必要分のみ取得）、backfill による後出し修正吸収
  - 品質チェックはエラー／警告を収集して返す（呼び出し元が判断）

- 品質チェック
  - 欠損（OHLC 欠損）、重複、スパイク（前日比）、日付不整合（未来日付／非営業日）を検出
  - QualityIssue オブジェクトで詳細を返す

- 監査ログ（トレーサビリティ）
  - シグナル→発注要求→約定 の階層を UUID で追跡
  - 発注要求は冪等キー（order_request_id）を持ち重複送信を防止
  - すべて UTC タイムスタンプで保存

---

## 必要条件 / 依存関係

- Python 3.10+（型構文に | を使用）
- 必須ライブラリ（例）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

プロジェクトによっては追加パッケージ（Slack 連携など）を利用する可能性があります。requirements.txt がある場合はそちらを利用してください。

---

## セットアップ手順

1. リポジトリをクローンする

```bash
git clone <repo-url>
cd <repo-dir>
```

2. Python 仮想環境を作成して依存パッケージをインストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

3. 環境変数ファイルを作成

プロジェクトルートに `.env` を置くと自動的に読み込まれます（`.env.local` は優先して上書きされます）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必要な主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略可、デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（省略可、デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. DuckDB スキーマ初期化

Python コンソールまたはスクリプトで実行します。

```python
from kabusys.data.schema import init_schema, get_connection
conn = init_schema("data/kabusys.duckdb")
# 既存 DB に接続するだけなら:
# conn = get_connection("data/kabusys.duckdb")
```

監査ログ（audit）を追加で初期化する場合:

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

---

## 使い方（主要 API / 例）

- 設定取得

```python
from kabusys.config import settings
token = settings.jquants_refresh_token
print(settings.env, settings.is_live)
```

- J-Quants から日次株価を取得して保存（DuckDB 接続を渡す）

```python
from kabusys.data import jquants_client as jq
import duckdb
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved", saved)
```

- 日次 ETL を実行（カレンダー取得→株価→財務→品質チェック）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- RSS ニュース収集と保存（既知銘柄セットを渡して銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 既知銘柄コード
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- 品質チェック単体実行

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## ディレクトリ構成

主要ファイル / モジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 定義（自動 .env ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証・取得・保存）
    - news_collector.py
      - RSS 収集、前処理、SSRF 対策、DuckDB への保存
    - schema.py
      - DuckDB スキーマ定義と初期化（Raw/Processed/Feature/Execution）
    - pipeline.py
      - ETL パイプライン（差分取得、保存、品質チェック）
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）定義と初期化
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - strategy/
    - __init__.py （戦略関連エントリポイントを想定）
  - execution/
    - __init__.py （発注実行関連エントリポイントを想定）
  - monitoring/
    - __init__.py （監視・アラート関連を想定）

プロジェクトルートに `.env` / `.env.local` / pyproject.toml / .git 等を置く想定です。

---

## 運用上の注意・ヒント

- 環境ロード
  - パッケージ利用時にプロジェクトが .git または pyproject.toml によってルート検出されると `.env` → `.env.local` の順で自動読み込みされます。テスト等で自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境に設定してください。

- J-Quants トークン
  - get_id_token はリフレッシュトークンから ID トークンを取得します。API 呼び出しは内部でトークンキャッシュと自動更新を行うため、通常は id_token を明示せずに利用できます。

- DuckDB の初期化
  - 初回は必ず schema.init_schema() を呼んでテーブルを作成してください。既存 DB に接続するだけなら get_connection() を使います。

- セキュリティ
  - RSS フィードや外部 URL 取り扱いでは SSRF 対策やレスポンスサイズ制限が入っていますが、運用時はホワイトリスト運用やタイムアウト設定を適切に行ってください。

- ロギング
  - settings.log_level でロギングレベルを制御できます。運用環境（live）では INFO/ WARNING を推奨します。

---

この README はコードベースの概要と主要な使い方を示したものです。詳細な仕様（DataPlatform.md, DataSchema.md 等）や追加の CLI/運用スクリプトがある場合は、それらのドキュメントも参照してください。必要であれば、README にサンプル .env.example やデプロイ手順（systemd / cron / Airflow 等）を追記できます。