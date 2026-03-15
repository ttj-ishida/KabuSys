# KabuSys

日本株自動売買システムのライブラリ/基盤コンポーネント集です。  
データ取得、DuckDB スキーマ定義、監査ログ、環境設定周りのユーティリティを含み、戦略/発注/監視モジュールの基盤を提供します。

バージョン: 0.1.0

---

## 主な特徴

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）を厳守する内部 RateLimiter
  - 再試行（指数バックオフ、最大 3 回）、401 時は自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB へ冪等に保存（ON CONFLICT DO UPDATE）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層を含むスキーマ定義と初期化機能
  - 検索効率を考慮したインデックス定義

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレースを UUID チェーンで保証
  - 発注要求に冪等キー（order_request_id）を採用して二重発注を防止
  - 全てのタイムスタンプは UTC に統一

- 環境変数／設定管理
  - .env / .env.local を自動ロード（プロジェクトルートは .git または pyproject.toml を基準に探索）
  - 必須値は Settings クラスから取得（未設定時は明示的なエラー）

---

## 依存関係・動作環境

- Python 3.10 以上（| 型注釈を使用しているため）
- duckdb（DuckDB 用 Python バインディング）
- 標準ライブラリ（urllib, json, logging など）

インストール（最低限）:
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
# 開発環境ではパッケージを editable インストール:
pip install -e .
```

（プロジェクトに requirements.txt があれば適宜 pip install -r requirements.txt を使用してください）

---

## 環境変数（.env）

必須の環境変数：
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : 通知先 Slack チャンネル ID

任意 / デフォルトあり：
- KABUSYS_ENV : 実行環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL   : ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）デフォルト: INFO
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化する場合は `1` をセット

自動ロードの挙動:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` → `.env.local` の順で読み込む
- OS 環境変数が優先され、`.env.local` は既存の OS 環境変数を上書きしない（ただし override=True の動作により `.env.local` は `.env` より優先）

簡易 .env.example:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

Settings の取得例:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

未設定の必須キーを参照すると ValueError が発生します。

---

## セットアップ手順（短縮）

1. リポジトリをクローン
2. 仮想環境の作成・有効化
3. 依存パッケージをインストール（少なくとも duckdb）
4. .env をプロジェクトルートに配置して必要な環境変数を設定
5. DuckDB スキーマを初期化

例:
```bash
git clone <repo_url>
cd <repo_root>
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# 開発時:
pip install -e .

# .env を配置したら Python からスキーマ初期化
python - <<'PY'
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
print("initialized")
PY
```

監査ログ専用 DB を初期化する場合:
```python
from kabusys.data.audit import init_audit_db
init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主な API とサンプル）

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # :memory: でインメモリ可
```

- J-Quants から日足を取得して保存
```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
n = save_daily_quotes(conn, records)
print(f"saved {n} records")
```

- 財務データ / マーケットカレンダーの取得も同様:
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)

- 認証トークン取得（通常は内部で自動的に行われる）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用
```

- 監査ログの初期化（既存 conn に追加）
```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")  # あるいは get_connection(...)
init_audit_schema(conn)  # 監査テーブルを追加
```

注意点:
- J-Quants クライアントは内部で API レート制限・リトライ・トークンリフレッシュを行いますが、業務要件に応じた追加のリスク管理（並列数制限など）が必要です。
- save_* 関数は冪等性を保つよう設計されています（ON CONFLICT で更新）。

---

## ディレクトリ構成

以下はパッケージ内の主要ファイル群です（src/layout）。

- src/kabusys/
  - __init__.py
    - パッケージメタ情報（__version__ 等）
  - config.py
    - 環境変数 / Settings 管理、自動 .env ロードロジック
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック、レート制御、リトライ、トークン管理）
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）の定義と初期化
    - (other data modules placeholder)
  - strategy/
    - __init__.py (戦略モジュール用プレースホルダ)
  - execution/
    - __init__.py (発注/ブローカー連携用プレースホルダ)
  - monitoring/
    - __init__.py (監視/モニタリング用プレースホルダ)

---

## 実装上の設計メモ（主要ポイント）

- 時刻は基本的に UTC で扱う（fetched_at / created_at 等）
- DuckDB に保存する際は冪等性を保つため INSERT ... ON CONFLICT DO UPDATE を使用
- J-Quants API のレートは 120 req/min に合わせ、固定間隔スロットリングで制御
- HTTP エラー 401 はトークン更新を試みて 1 回リトライ。408/429/5xx は指数バックオフでリトライ
- .env 自動ロードはテストのために無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）

---

## 今後の拡張案（参考）

- kabuステーションとの発注ラッパの実装（execution 層）
- strategy パッケージに戦略テンプレートとバックテスト機能
- monitoring: Prometheus / Slack 連携、アラートルール
- CI でのスキーマ/SQL lint、unit テスト追加

---

不明点や README に追加したい使い方（例: 発注フローや Slack 通知の利用例）があれば教えてください。README をそれに合わせて拡張します。