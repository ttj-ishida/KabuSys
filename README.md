# KabuSys

日本株向けの自動売買プラットフォームの基盤ライブラリです。データ管理（DuckDB スキーマ）、環境設定管理、監査ログ（トレーサビリティ）用のモジュールを提供します。戦略（strategy）、発注/実行（execution）、モニタリング（monitoring）用のパッケージ構成を想定した設計になっています。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような要件を満たすためのコア機能を実装しています。

- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）のスキーマ定義と初期化
- 発注から約定に至る監査ログ（トレーサビリティ）用スキーマの定義と初期化
- 環境変数 / .env 管理（自動読み込み機能、保護された OS 環境変数の扱い）
- 設定値を一元的に取得する `settings` オブジェクト

本リポジトリはライブラリ化を前提としており、戦略実装やブローカー接続等は別モジュール／上位アプリケーションで実装します。

---

## 主な機能一覧

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）
  - クォートやコメントを考慮した .env パース実装
  - 必須環境変数チェック（未設定時は例外）
  - `settings` オブジェクトによるプロパティアクセス（API トークン、DB パス、環境モードなど）
  - 自動読み込み無効化用フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- データスキーマ（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution レイヤのテーブル群を定義
  - インデックス作成（頻出クエリを想定）
  - `init_schema(db_path)` で DuckDB を初期化（冪等）
  - `get_connection(db_path)` で既存 DB へ接続

- 監査ログ（src/kabusys/data/audit.py）
  - シグナル -> 発注要求 -> 約定 のトレーサビリティを保証するテーブル群
  - 冪等キー（order_request_id）、broker 側の一意キー管理
  - UTC タイムゾーンでの TIMESTAMP 保存を想定（初期化時に SET TimeZone='UTC' を設定）
  - `init_audit_schema(conn)` / `init_audit_db(db_path)` を提供

- パッケージ構成の拡張ポイント
  - strategy, execution, monitoring 向けのパッケージ入口を用意（今後拡張可能）

---

## 必要条件

- Python 3.10+
  - 型注釈（X | Y 形式）を使用しているため 3.10 以上を推奨します
- duckdb Python パッケージ

インストール例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
```

プロジェクトをパッケージとしてセットアップする場合（pyproject.toml がある想定）:
```bash
pip install -e .
pip install duckdb
```

---

## 環境変数（.env）

主に次の環境変数を使用します（最低限必要なものは README に記載のうち必須として .env に設定してください）:

必須（アクセス時に未設定だと例外）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルト値あり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

自動ロードに関するフラグ:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、自動的な .env/.env.local の読み込みを無効化できます（テスト等で利用）。

.env のパーサは以下の特徴を持ちます:
- export KEY=val 形式に対応
- 先頭の # 行や空行は無視
- シングル/ダブルクォートで囲った値はエスケープシーケンスを考慮してパース
- クォート無しの行では、スペース直前の '#' をコメントとして扱う

例（.env）:
```
JQUANTS_REFRESH_TOKEN="xxxx"
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xxxx
SLACK_CHANNEL_ID=YYYYYYY
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存パッケージインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb
   # 必要に応じて他の依存（HTTP クライアント等）を追加
   ```

3. .env を作成（リポジトリルートに配置）
   - 上記「環境変数」セクションを参考に作成してください
   - `.env.local` は `.env` の上書き用に使えます（自動で両方が読み込まれます）

4. データベーススキーマを初期化
   - DuckDB を使用する場合は、次のように Python から初期化します（詳細は次節「使い方」参照）。

---

## 使い方（基本例）

- 設定値の取得:
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)   # 必須: 未設定だと ValueError
print(settings.duckdb_path)             # Path オブジェクト
print(settings.is_live)                 # 環境フラグ
```

- DuckDB スキーマの初期化（アプリ起動時に一度実行）:
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# 初回・または初期化したい場合
conn = init_schema(settings.duckdb_path)  # ファイルを自動作成し、全テーブル・インデックスを作成

# 既存 DB に接続するだけの場合
conn2 = get_connection(settings.duckdb_path)
```

- 監査ログ（audit）スキーマの追加初期化:
```python
from kabusys.data.audit import init_audit_schema, init_audit_db
from kabusys.config import settings

# 既存の DuckDB 接続に監査テーブルを追加する
conn = init_schema(settings.duckdb_path)
init_audit_schema(conn)

# 監査専用 DB を別に初期化する場合
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意点:
- init_schema は冪等（既に存在するテーブルは上書きしない）ため、何度呼んでも安全です。
- init_audit_schema は接続（conn）上で UTC タイムゾーンを設定します（SET TimeZone='UTC'）。

---

## ディレクトリ構成

リポジトリ内の主なファイル・ディレクトリ（省略可能なファイルは含めていません）:

- src/
  - kabusys/
    - __init__.py
    - config.py              # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py            # DuckDB スキーマ定義・初期化
      - audit.py             # 監査ログ（トレーサビリティ）定義・初期化
      - audit.py
      - audit.py
      - audit.py
      - audit.py
    - strategy/
      - __init__.py          # 戦略モジュール（拡張ポイント）
    - execution/
      - __init__.py          # 発注/実行モジュール（拡張ポイント）
    - monitoring/
      - __init__.py          # モニタリングモジュール（拡張ポイント）

主なモジュール:
- kabusys.config: settings オブジェクトと .env 自動ロード機能
- kabusys.data.schema: データ層の DDL（Raw/Processed/Feature/Execution）とインデックス、init_schema / get_connection
- kabusys.data.audit: 監査ログ用 DDL と init_audit_schema / init_audit_db

（注意）実際のアプリケーションコード（戦略、発注ロジック、ブローカー連携、Slack 通知等）はこのライブラリの上に実装してください。

---

## 設計上の要点・注意事項

- スキーマはレイヤ化（Raw / Processed / Feature / Execution / Audit）されており、データの由来と用途を明確化しています。
- 監査ログは削除を想定しない設計（ON DELETE RESTRICT 等）で、発注の冪等性・トレーサビリティを重視しています。
- すべての TIMESTAMP は UTC 保存を前提（監査スキーマ初期化で明示的に設定）。
- .env の自動読み込みはプロジェクトルート（.git / pyproject.toml）を基準とするため、実行時のカレントディレクトリに依存しません。
- 環境変数の自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで利用）。

---

## 今後の拡張案（参考）

- strategy パッケージに戦略実装のテンプレートを追加
- execution パッケージにブローカー抽象化レイヤ（kabu API / 他証券）を実装
- monitoring パッケージに Slack 通知やメトリクス収集の実装
- マイグレーション管理（スキーマのバージョン管理）導入

---

必要があれば README に入れるサンプル .env.example、CI 設定、パッケージ配布手順（pyproject.toml の例）なども作成します。どの内容を追加したいか教えてください。