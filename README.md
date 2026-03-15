# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買基盤のコアライブラリです。データ取得・永続化、スキーマ定義、監査ログなどの基盤機能を提供し、戦略・発注・モニタリング層の実装を支援します。

主な設計方針:
- データ取得の冪等性とトレーサビリティ（取得時刻を UTC で記録）
- API レート制限の遵守と堅牢なリトライロジック
- DuckDB を用いたオンディスク / インメモリ DB によるデータ永続化
- 発注から約定までを追跡できる監査ログ（UUID を使った連鎖）

---

## 機能一覧

- 環境変数 / .env 管理（自動読み込み、保護機能、必須チェック）
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を適用
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants API クライアント（data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得
  - レートリミッタ（120 req/min）、リトライ（指数バックオフ）、トークン自動リフレッシュ（401 時）
  - 取得データに fetched_at（UTC）を付与
  - DuckDB へ保存するための save_* ユーティリティ（冪等 INSERT / ON CONFLICT）
- DuckDB スキーマ定義と初期化（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブルを定義
  - インデックス定義やテーブル作成順を考慮した init_schema(db_path)
- 監査ログ（data.audit）
  - signal_events / order_requests / executions の監査テーブルを提供
  - order_request_id を冪等キーとして二重発注防止
  - すべての TIMESTAMP を UTC で扱う（init_audit_schema は SET TimeZone='UTC' を実行）
- パッケージ構造の雛形（strategy, execution, monitoring モジュールのための名前空間）

---

## 要求環境・依存

- Python 3.10+
  - 型注釈で `X | None`（PEP 604）を使用しているため 3.10 以上を想定
- 依存ライブラリ（主に DuckDB）
  - duckdb
- 標準ライブラリの urllib, json, logging 等を使用

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# ローカル開発用にパッケージを編集可能インストールする場合
pip install -e .
```

（プロジェクトに requirements ファイルがある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数の設定
   - プロジェクトルートに `.env` を置くことで自動読み込みされます（.git または pyproject.toml のあるディレクトリがプロジェクトルートと見なされます）。
   - 自動ロードを無効にするには、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。
4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite 用パス（省略時: data/monitoring.db）
   - KABUSYS_ENV: 開発モード（development / paper_trading / live、デフォルト: development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）

サンプル .env（例）
```
JQUANTS_REFRESH_TOKEN="xxxxxxxxxxxxxxxx"
KABU_API_PASSWORD="password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C12345678"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV="development"
LOG_LEVEL="INFO"
```

---

## 使い方（基本例）

以下は主要機能の利用例です。実行前に必須の環境変数が設定されていることを確認してください。

1. 設定値の取得
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必須: なければ ValueError
print(settings.duckdb_path)            # Path オブジェクト
print(settings.is_dev)
```

2. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# 初回: スキーマ作成
conn = init_schema(settings.duckdb_path)

# 既存 DB へ接続するだけなら
conn2 = get_connection(settings.duckdb_path)
```

3. J-Quants からデータを取得して保存する（株価日足の例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings

# DB 初期化（なければ作成）
conn = init_schema(settings.duckdb_path)

# データ取得（id_token は省略可能。内部キャッシュと自動リフレッシュあり）
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# DuckDB に保存（冪等）
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

4. 財務データ・マーケットカレンダーの取得と保存
```python
from kabusys.data.jquants_client import (
    fetch_financial_statements, save_financial_statements,
    fetch_market_calendar, save_market_calendar,
)
# fetch_financial_statements / save_financial_statements
fin = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin)

# 市場カレンダー
cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

5. 監査ログの初期化（監査専用テーブルの追加）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
init_audit_schema(conn)  # audit テーブルを追加（UTC タイムゾーン設定）
```

---

## 実装上の注意点 / 補足

- J-Quants クライアントの特徴
  - レート制限: 120 req/min を実装内で守る（固定間隔スロットリング）
  - リトライ: 最大 3 回（408, 429, 5xx を対象）。429 の場合は Retry-After ヘッダを優先
  - 401 を受けた場合はリフレッシュを試みて1回だけ再試行
  - 取得データに fetched_at を付与し、Look-ahead Bias を防ぐ設計
- DuckDB スキーマは冪等（CREATE TABLE IF NOT EXISTS / ON CONFLICT）で作られているため、何度でも初期化を呼べます
- 監査ログは削除しない前提（FK は ON DELETE RESTRICT）で設計されています
- すべての TIMESTAMP は UTC で扱うことを前提にしている（監査テーブル初期化時に SET TimeZone='UTC' を実行）

---

## ディレクトリ構成

下記は主要ファイル／モジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数／設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存ユーティリティ）
    - schema.py              # DuckDB スキーマ定義・初期化
    - audit.py               # 監査ログ（signal / order_request / executions）
    - audit.py
    - その他のデータ関連モジュール
  - strategy/
    - __init__.py            # 戦略関連の名前空間（実装はここに追加）
  - execution/
    - __init__.py            # 発注・約定処理の名前空間（実装はここに追加）
  - monitoring/
    - __init__.py            # モニタリング関連の名前空間（実装はここに追加）

---

## 今後の拡張案（参考）

- kabu ステーション API 用の発注実装（execution 層）
- 戦略モジュールのサンプル実装（strategy 層）
- Slack 通知・監視用の実装（monitoring）
- CI / テストスイートと .env.example などの提供

---

必要であれば、README に含めるサンプル .env.example、より詳しい API 使用例、または戦略／発注のサンプル実装を追加できます。どの項目を拡張したいか教えてください。