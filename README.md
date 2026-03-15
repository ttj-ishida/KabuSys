# KabuSys

日本株自動売買システムのコアライブラリ（ライブラリ形態の部分実装）。  
本リポジトリはデータ層（DuckDB スキーマ定義・初期化）、環境設定管理、および監査ログ用スキーマを提供します。バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムの基盤となる共通モジュール群を提供します。主に次を目的とします。

- 市場データ・財務データ・ニュース等の保存用 DuckDB スキーマ定義と初期化
- 注文／約定／ポジション等の実行関連テーブル定義（Execution Layer）
- 戦略で生成したシグナルから発注・約定までを完全にトレースする監査ログ（audit）
- 環境変数ベースの設定管理（.env の自動読み込みを含む）
- 将来的に strategy / execution / monitoring モジュール群を収容するパッケージ構成

---

## 主な機能一覧

- DuckDB 用スキーマ作成（data.schema.init_schema）
  - Raw / Processed / Feature / Execution レイヤーのテーブル群
  - 検索用インデックスの作成
- 監査ログスキーマ（data.audit）
  - signal_events, order_requests, executions のテーブル、インデックス
  - 冪等キー（order_request_id, broker_execution_id 等）を考慮
  - タイムゾーンは UTC 保存
- 環境設定（config）
  - .env / .env.local をプロジェクトルートから自動読み込み（OS環境変数優先）
  - 必須設定を取得する Settings クラス（プロパティ経由でアクセス）
  - KABUSYS_ENV / LOG_LEVEL の検証
- モジュール構成の公開インターフェース（kabusys.__all__）

---

## 要件

- Python 3.10+
  - ソースで PEP 604 の型記法（`X | Y`）を使用しているため
- パッケージ依存
  - duckdb

インストール例（仮にパッケージ化されている場合）:
```bash
pip install duckdb
# 開発中はローカルソースを editable インストール
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトする。
2. 必要な Python 環境（3.10+）を準備し、依存ライブラリをインストールする（少なくとも duckdb）。
3. プロジェクトルートに `.env`（必要に応じて `.env.local`）を作成して環境変数を設定する。

推奨する重要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（省略時は http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)（デフォルト: INFO）

自動 .env ロードを無効化するには:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

.env 読み込みの優先順位:
OS 環境変数 > .env.local > .env

---

## 使い方（クイックスタート）

- 設定値にアクセスする（必須環境変数が未設定の場合は ValueError が発生します）:

```python
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path  # pathlib.Path
```

- DuckDB スキーマを初期化して接続を取得する:

```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリがなければ自動作成）
conn = init_schema("data/kabusys.duckdb")

# またはインメモリ DB
conn = init_schema(":memory:")
```

- 既存 DB へ接続する（スキーマ初期化はしない）:

```python
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
```

- 監査ログテーブルを既存の接続へ追加する:

```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # conn は duckdb 接続
```

- 監査ログ専用 DB を初期化する:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/monitoring.db")
```

メモ:
- init_schema / init_audit_db は既存テーブルがある場合も冪等的に動作します。
- init_audit_schema は接続に対して TimeZone を UTC にセットします（すべての TIMESTAMP は UTC 保存想定）。

---

## 環境変数のパース挙動（補足）

- .env 中の行はコメント行や空行を無視します。
- export KEY=val の形式にも対応します。
- 値がシングル／ダブルクォートで囲まれている場合はエスケープ処理を考慮してパースします。
- クォートなしの行では、`#` の直前が空白／タブのときそれ以降をコメントとして扱います。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src 配下）の主要ファイル一覧と簡単な説明:

- src/kabusys/
  - __init__.py
    - パッケージ公開名およびバージョン定義（__version__ = "0.1.0"）
  - config.py
    - 環境変数の自動読み込み・Settings クラス
  - data/
    - __init__.py
    - schema.py
      - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）
      - init_schema(db_path) / get_connection(db_path)
    - audit.py
      - 監査ログ用テーブル定義（signal_events / order_requests / executions）
      - init_audit_schema(conn) / init_audit_db(db_path)
    - (その他) audit と schema がデータ永続化の中核
  - strategy/
    - __init__.py (将来的に戦略実装を配置)
  - execution/
    - __init__.py (将来的に発注ロジック等を配置)
  - monitoring/
    - __init__.py (将来的に監視・メトリクス集計を配置)

---

## 注意事項 / 今後の拡張点

- strategy / execution / monitoring は現状トップレベルのパッケージとして用意されていますが、実ロジックは未実装です。システム全体を組み上げるには各モジュールを実装してください。
- セキュリティ: .env にシークレットを平文で保管するため、適切なアクセス制御を行ってください。CI や本番環境ではシークレットマネージャを利用することを検討してください。
- DuckDB は単ファイル DB のため、複数プロセスでの同時書き込みやロック挙動に注意してください。運用設計に応じて DB 選定を行ってください。

---

もし README に追加したい利用例（戦略の仮実装、Slack 通知サンプル、運用フロー図など）があれば教えてください。必要に応じて追記・テンプレート化します。