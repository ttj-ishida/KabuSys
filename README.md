# KabuSys

日本株自動売買システムのコアライブラリ（パッケージ）です。  
このリポジトリは、マーケットデータの格納（DuckDB スキーマ）、環境変数による設定管理、監査ログ（トレーサビリティ）などの基盤機能を提供します。戦略、発注（execution）、監視（monitoring）などの上位モジュールはこの基盤の上で実装されます。

---
目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数一覧（.env 例）
- ディレクトリ構成と各ファイル説明
- 補足 / 注意点

---

## プロジェクト概要
KabuSys は日本株の自動売買プラットフォーム向けの基盤ライブラリです。  
主要な役割は以下の通りです。
- 環境変数・設定の集中管理（自動 .env ロード対応）
- DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution 層）のスキーマ定義と初期化
- 発注フローを完全にトレース可能にする監査ログ（監査テーブル）の初期化
- strategy / execution / monitoring など上位層のための名前空間を提供

パッケージ名: kabusys  
バージョン: 0.1.0

---

## 機能一覧
- 設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み（無効化可）
  - 必須設定の取得 API（例: settings.jquants_refresh_token）
  - 環境（development / paper_trading / live）やログレベル検証
- データスキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の各テーブル DDL を定義
  - インデックス定義、テーブル作成の冪等初期化関数: init_schema(db_path)
  - 既存 DB へ接続: get_connection(db_path)
- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定 までを UUID 連鎖でトレースする監査テーブルを定義
  - init_audit_schema(conn) / init_audit_db(db_path) を提供
  - すべての TIMESTAMP は UTC 保存（init_audit_schema は TimeZone を UTC に設定）
- パッケージ構成上のプレースホルダモジュール: strategy, execution, monitoring（上位実装用）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 型表記を使用しているため）
- pip が利用可能

推奨手順（ローカル開発環境）
1. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate
2. 必要パッケージをインストール
   - 最低限: duckdb が必要です
     - pip install duckdb
   - 実際の運用では J-Quants API クライアントや kabu API クライアント、Slack 通知等の追加依存が必要になる想定です（本パッケージに含まれていません）。
3. （任意）このプロジェクトを開発インストール
   - pip install -e .
   - （pyproject.toml / setup.py がある場合に有効）

環境変数の自動ロード
- パッケージ読み込み時に、プロジェクトルート (.git または pyproject.toml を基準) を探して .env を自動読み込みします（続けて .env.local を上書き読み込み）。
- 自動ロードを無効化するには環境変数を設定:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（簡易サンプル）

1) 設定を読み取る
```python
from kabusys.config import settings

# 必須項目は設定されていなければ ValueError が発生する
print("env:", settings.env)
print("is_live:", settings.is_live)
print("duckdb path:", settings.duckdb_path)
```

2) DuckDB スキーマを初期化する（ファイル DB）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # デフォルト path: data/kabusys.duckdb
# conn は duckdb の接続オブジェクト（DuckDBPyConnection）
```

3) 監査ログテーブルを既存接続に追加
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # conn は init_schema の戻り値でも可
```

4) 監査ログ専用 DB を作る場合
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

5) 自動 .env 読み込みを無効にして、手動で環境を読みたい場合
```python
import os
os.environ["KABUSYS_DISABLE_AUTO_ENV_LOAD"] = "1"
# その後に必要な環境変数を手動でセット
```

---

## 環境変数一覧（.env 例）
以下は本パッケージで参照される主な環境変数（必須 / 任意）です。実際の運用では .env.example をベースに .env を作成してください。

必須（例）
- JQUANTS_REFRESH_TOKEN
  - J-Quants API 用のリフレッシュトークン
- KABU_API_PASSWORD
  - kabu ステーション API のパスワード
- SLACK_BOT_TOKEN
  - Slack 通知用ボットトークン
- SLACK_CHANNEL_ID
  - 通知先 Slack チャンネル ID

任意（デフォルトあり）
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL) — デフォルト: INFO

.env の例:
```
# .env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成（主要ファイルと説明）
以下はこのリポジトリの主要なファイル・モジュールです（src/kabusys 配下）。

- src/kabusys/__init__.py
  - パッケージメタ情報（__version__）と公開モジュール一覧

- src/kabusys/config.py
  - 環境変数の自動読み込みロジック（.env / .env.local）
  - Settings クラス（settings インスタンス）: アプリケーション設定の読み取り API
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能
  - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して決定

- src/kabusys/data/schema.py
  - DuckDB 用の DDL を定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) : DB ファイルの親ディレクトリを自動作成してテーブル・インデックスを生成
  - get_connection(db_path) : 既存 DB に接続（スキーマ初期化は行わない）

- src/kabusys/data/audit.py
  - 発注フローの監査ログ（signal_events, order_requests, executions）を定義
  - init_audit_schema(conn) : 既存の DuckDB 接続へ監査テーブルを追加（UTC タイムゾーンを設定）
  - init_audit_db(db_path) : 監査専用 DB を作成して初期化

- src/kabusys/data/__init__.py
  - data パッケージのプレースホルダ

- src/kabusys/execution/__init__.py
  - execution パッケージのプレースホルダ（発注ロジック等を格納）

- src/kabusys/strategy/__init__.py
  - strategy パッケージのプレースホルダ（戦略実装）

- src/kabusys/monitoring/__init__.py
  - monitoring パッケージのプレースホルダ（監視・アラート等）

---

## 補足 / 注意点
- Python バージョン: 本コードは Python 3.10+ の構文 (X | Y 型表記など) を用いています。3.10 未満では動作しません。
- 依存: DuckDB (pip package: duckdb) が必須です。運用環境では J-Quants、kabu API クライアント、Slack SDK 等の追加依存が必要になる場合があります（このリポジトリには含まれていません）。
- .env の読み込みルール:
  - プロジェクトルートを探し .env を先に読み込む（未設定のキーのみセット）
  - .env.local を上書き読み込み（既存の OS 環境変数は保護される）
  - export 付きの行やクォート、インラインコメントなどの一般的な .env パターンに対応
- 監査ログ:
  - すべての TIMESTAMP は UTC で保存されることを想定（init_audit_schema で TimeZone を UTC に設定）
  - 監査ログは通常削除しない前提で設計されている（FK は ON DELETE RESTRICT）

---

必要であれば、README により詳しいインストール手順（pyproject / requirements ファイルに合わせた）や、サンプル戦略・発注フローのテンプレート、運用時の監視・ロギング設定例などを追加できます。どの情報を優先して追記しますか？