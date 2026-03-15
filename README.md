# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買を想定した基盤パッケージです。市場データの取り込み・加工・特徴量生成から、シグナル管理、発注・約定の監査ログまでを想定したデータ層と設定管理を提供します。

主な目的は、戦略開発・バックテスト・本番運用（paper/live）のための堅牢なデータスキーマと運用上のユーティリティを提供することです。

## 機能一覧

- 環境変数 / 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを基準に探索）
  - 必須設定の取得（未設定時は例外を発生）
  - KABUSYS_ENV / LOG_LEVEL のバリデーション
- データベーススキーマ（DuckDB）
  - 3層（Raw / Processed / Feature）+ Execution 層のテーブル定義
  - 耐久性を配慮したDDL（主キー・チェック制約・インデックスなど）
  - スキーマ初期化ユーティリティ（init_schema）
  - インメモリ（":memory:"）対応
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレース可能な監査テーブル群
  - 冪等キー（order_request_id）や broker_execution_id 等を想定
  - UTC 保存強制（SET TimeZone='UTC'）
  - init_audit_schema / init_audit_db による初期化
- パッケージ構成（strategy / execution / monitoring などの名前空間）

## セットアップ手順

必要な依存パッケージ（最小）:
- Python 3.9+
- duckdb

インストール例（仮にパッケージをローカルで編集する場合）:

```bash
# 仮想環境を作成してアクティベートすることを推奨
python -m venv .venv
source .venv/bin/activate  # Linux / macOS
.venv\Scripts\activate     # Windows

# duckdb をインストール
pip install duckdb

# ローカルパッケージとしてインストールする場合（プロジェクトルートに pyproject.toml がある前提）
pip install -e .
```

環境変数の準備:
- プロジェクトルートに `.env`（と必要に応じて `.env.local`）を置くと、自動的に読み込まれます（OS環境変数が優先）。
- 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨する .env の例:

```
# 必須
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# 任意（デフォルト値あり）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development        # development | paper_trading | live
LOG_LEVEL=INFO                # DEBUG | INFO | WARNING | ERROR | CRITICAL
```

## 使い方

設定の読み取り:
Python コード内で設定にアクセスするには `kabusys.config.settings` を使います。

```python
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path  # pathlib.Path オブジェクト
```

自動 .env 読み込みの振る舞い:
- プロジェクトルートはこのパッケージのファイル位置（__file__）を起点に `.git` または `pyproject.toml` を探索して決定します。これにより CWD に依存しません。
- 読み込む順序: OS 環境変数 > .env.local > .env
- `.env.local` は `.env` の上書き（override=True）を行いますが、既に OS 環境変数に存在するキーは上書きされません（保護）。

DuckDB スキーマ初期化:
データ層全体（Raw / Processed / Feature / Execution）を初期化するには `init_schema` を使用します。

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
conn = schema.init_schema(":memory:")
```

既存の DuckDB に接続するだけなら:

```python
conn = schema.get_connection("data/kabusys.duckdb")
```

監査ログ（Audit）初期化:
既存の DuckDB 接続に監査テーブルを追加する場合:

```python
from kabusys.data import audit, schema
conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

監査専用 DB を新規に作る場合:

```python
conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

注意点:
- すべての TIMESTAMP は UTC で保存されるよう初期化時に TimeZone を設定します。
- init_schema および init_audit_schema は冪等（既に存在するテーブルはスキップ）です。
- DuckDB の DDL には主キー・チェック制約・インデックスが多数定義されています（パフォーマンスとデータ整合性を想定）。

データ / 監査フロー（概要）:
- 戦略層で signal を生成 → signal_events に記録
- オーダー要求（order_requests）は冪等キー（order_request_id）で管理 → 発注処理へ
- 証券会社からの約定は executions に記録（broker_execution_id を冪等キーとして想定）
- 生成された発注 → orders / trades / positions / portfolio_performance 等のテーブルに反映

## ディレクトリ構成

パッケージ配下の主要ファイルと役割（リポジトリのルートが src/ を含む構成を想定）:

- src/
  - kabusys/
    - __init__.py
      - パッケージメタ情報（__version__ = "0.1.0"）
    - config.py
      - 環境変数読込 / Settings クラス（J-Quants, kabu API, Slack, DB パス, 環境種別など）
    - data/
      - __init__.py
      - schema.py
        - DuckDB スキーマ定義と初期化用関数（init_schema, get_connection）
        - Raw / Processed / Feature / Execution 層のテーブル定義
      - audit.py
        - 監査ログ用スキーマ（signal_events, order_requests, executions）と初期化関数（init_audit_schema, init_audit_db）
      - (その他) audit / schema に関連するユーティリティ類
    - strategy/
      - __init__.py
      - （戦略関連モジュールを配置する想定）
    - execution/
      - __init__.py
      - （発注・ブローカー連携ロジックを配置する想定）
    - monitoring/
      - __init__.py
      - （監視・メトリクス記録ロジックを配置する想定）

## 開発・運用上の注意

- 環境変数の自動読み込みは便利ですが、テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して明示的に制御することを推奨します。
- KABUSYS_ENV は以下の値のみ許容されます: `development`, `paper_trading`, `live`。不正な値だと例外が発生します。
- LOG_LEVEL は `DEBUG, INFO, WARNING, ERROR, CRITICAL` のいずれかである必要があります。
- DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）は Settings.duckdb_path で取得できます。必要であれば別の場所に変更してください。
- 監査ログは削除しない前提で設計しています（FK は ON DELETE RESTRICT 等）。ログの永続化ポリシーを運用で定義してください。

---

この README はコードベース（src/kabusys）に基づいて生成しています。詳細な API ドキュメントや運用手順（Slack 通知設定、J-Quants / kabuAPI 実装、実際の戦略コードなど）は別途追記してください。