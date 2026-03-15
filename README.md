# KabuSys

KabuSys は日本株向けの自動売買フレームワーク（ライブラリ）です。データ収集・保持、特徴量生成、シグナル管理、発注監査までを想定した土台を提供します。本リポジトリはコアの設定管理、DuckDB ベースのスキーマ初期化、監査ログ（トレーサビリティ）機能を含みます。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## 主な機能

- 環境変数 / 設定管理
  - .env / .env.local からの自動ロード（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須設定の取得と検証（例: JQUANTS_REFRESH_TOKEN 等）
  - 環境（development / paper_trading / live）やログレベルの検証メソッド

- データベーススキーマ（DuckDB）
  - 層構造によるテーブル定義（Raw / Processed / Feature / Execution）
  - 各種テーブルの作成を行う初期化 API（冪等）
  - パフォーマンス向けインデックス定義

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティを残す監査テーブル群
  - 冪等キー（order_request_id）や各種ステータス管理
  - UTC タイムスタンプ保存ポリシー
  - DuckDB 接続に監査テーブルを追加する API

- プレースホルダーパッケージ
  - strategy/, execution/, monitoring/ はフレームワークの拡張ポイントとして用意（実装はこれから）

---

## 動作要件

- Python 3.10 以上（型アノテーションで | 演算子を使用）
- 依存パッケージ:
  - duckdb

（その他は標準ライブラリのみ）

---

## インストール

1. 仮想環境を作成することを推奨します。

```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate      # Windows
```

2. パッケージと依存をインストール：

（プロジェクトが pip インストール可能な形式である前提）
```bash
pip install duckdb
pip install -e .   # 開発インストール（setup による）
```

または、依存が duckdb のみであれば最低限:
```bash
pip install duckdb
```

---

## 環境変数（.env）

config モジュールは .env を自動ロードします（プロジェクトルートを探索）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（必須は明示）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 動作環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

例（.env）:
```
JQUANTS_REFRESH_TOKEN=YOUR_JQUANTS_REFRESH_TOKEN
KABU_API_PASSWORD=YOUR_KABU_API_PASSWORD
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（DB 初期化など）

DuckDB スキーマを初期化する基本例:

Python スクリプトや REPL で以下を実行します。

```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# デフォルトパスを settings から取得する例
db_path = settings.duckdb_path  # Path オブジェクト
conn = init_schema(db_path)     # テーブルとインデックスを作成して接続を返す

# 既存 DB へ接続する場合は:
conn2 = get_connection(db_path)
```

監査ログ（audit）を既存の DuckDB 接続に追加する場合:

```python
from kabusys.data.audit import init_audit_schema
# conn は init_schema の戻り値など既存の duckdb 接続
init_audit_schema(conn)
```

監査専用 DB を作る場合:

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

注意:
- init_schema / init_audit_db は冪等（既に存在するテーブルはスキップ）です。
- ファイルパスの親ディレクトリが無ければ自動で作成されます。
- 監査テーブルは UTC タイムゾーン保存を前提とします（init_audit_schema は接続に対して TimeZone='UTC' を実行します）。

---

## 使い方（コード例）

設定を取得する:

```python
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path
```

DB 初期化 + シンプルなクエリ例:

```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# DuckDB の接続オブジェクト経由で SQL 実行
rows = conn.execute("SELECT name FROM sqlite_master").fetchall()  # 例: 任意のクエリ
```

監査イベントを記録するテーブルを初期化してから運用側で INSERT していく想定です（実装例はアプリ側で行います）。

---

## 自動 .env ロードの挙動（詳細）

- プロジェクトルートの自動検出:
  - 起点は kabusys/config.py の __file__。親ディレクトリ群を調べ、`.git` または `pyproject.toml` が見つかったディレクトリをプロジェクトルートとします。
  - 見つからない場合、自動ロードはスキップします（テストや配布後の挙動安定のため）。

- 読み込み順序:
  1. OS 環境変数（既存のものは .env によって上書きされない）
  2. .env（プロジェクトルート）
  3. .env.local（存在すれば .env の上書き）

- 無効化:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを停止します。

- .env のパース:
  - コメント行と空行をスキップ
  - export キーワードに対応（例: export KEY=val）
  - シングル/ダブルクォート内のエスケープ対応
  - 行中のコメント（#）は条件により無視／切り捨て

---

## ディレクトリ構成

リポジトリ内の主要ファイル/ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                - 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py              - DuckDB スキーマ作成（init_schema / get_connection）
    - audit.py               - 監査ログ（signal / order_request / executions）の定義と初期化
    - audit のテーブルはトレーサビリティを目的に設計
  - strategy/
    - __init__.py            - 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py            - 発注・実行モジュール（拡張ポイント）
  - monitoring/
    - __init__.py            - 監視 / アラート機能（拡張ポイント）

主要ソース:
- src/kabusys/config.py
- src/kabusys/data/schema.py
- src/kabusys/data/audit.py

---

## 注意事項 / 補足

- このリポジトリはフレームワークの基盤（設定、データスキーマ、監査）を提供します。実際のデータ取得、特徴量計算、戦略ロジック、ブローカー連携の実装はアプリケーション側で行ってください。
- 監査ログは削除しないことを前提とした設計です（FK は ON DELETE RESTRICT などを採用）。
- DuckDB を使っているため、軽量で高速なローカル分析 DB をそのまま履歴保存に利用できます。大規模な運用では別途永続ストレージやバックアップを検討してください。
- Python バージョンが要件に満たない場合、型アノテーションの文法（Union 演算子 |）でエラーになります。Python 3.10 以上を使用してください。

---

もし README に追加したい内容（例えば API リファレンス、具体的な戦略のサンプル、CI / テスト手順、Docker サポートなど）があれば教えてください。必要に応じて追記・整備します。