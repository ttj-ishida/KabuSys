# KabuSys

KabuSys は日本株向けの自動売買システムの基盤ライブラリです。市場データの格納・スキーマ定義、環境変数管理、戦略/実行/監視のためのモジュール構成を提供します。

現在のバージョン: 0.1.0

## 概要
- DuckDB を使った三層（Raw / Processed / Feature）＋実行レイヤーのスキーマ定義と初期化機能を提供します。
- 環境変数を .env / .env.local / OS 環境変数から自動読み込みし、アプリケーション設定オブジェクト（`settings`）経由で設定値を取得できます。
- J-Quants、kabuステーション API、Slack など外部サービス向けの設定を想定したキーを定義しています。
- `strategy`, `execution`, `monitoring` 等のパッケージ領域を確保しており、上に戦略や発注ロジックを実装して拡張できます。

## 主な機能一覧
- 環境変数 / 設定管理
  - .env / .env.local の自動読み込み（優先順位: OS 環境 > .env.local > .env）
  - 複雑な .env 行のパース（`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント取り扱い）
  - 必須項目の取得時に未設定なら例外を投げる `settings` オブジェクト
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`
- DuckDB スキーマ
  - Raw / Processed / Feature / Execution 各種テーブル定義（価格、決算情報、ニュース、シグナル、注文、約定、ポジション等）
  - インデックス定義（よく使うクエリパターンを想定）
  - 冪等なスキーマ初期化関数 `init_schema(db_path)`
  - 既存 DB への接続 `get_connection(db_path)`

## 環境変数（主なキー）
必須（未設定だと settings プロパティで ValueError）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — ログレベル。`DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: `data/monitoring.db`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（値を設定すれば無効）

※ .env.example を参照して .env を作成することを想定しています（プロジェクトに .env.example があれば参照してください）。

## セットアップ手順

前提:
- Python 3.10 以上（型注釈に Union 演算子 `|` を使用）
- pip が利用可能

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストール
   - 最低限 DuckDB が必要です。パッケージや extras があればプロジェクトの setup/pyproject を参照してインストールしてください。
   ```
   pip install duckdb
   # またはパッケージ配布形式がある場合:
   pip install -e .
   ```

4. 設定ファイル (.env) を作成
   プロジェクトルートに `.env`（および必要に応じて `.env.local`）を置き、必要な環境変数を定義します。例:
   ```
   JQUANTS_REFRESH_TOKEN="your_jquants_token"
   KABU_API_PASSWORD="your_kabu_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C0123456789"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

   自動読み込みを無効にしたい場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

## 使い方（基本例）

- 設定を取得する
  ```python
  from kabusys.config import settings

  print(settings.env)
  print(settings.duckdb_path)
  token = settings.jquants_refresh_token  # 未設定なら例外
  ```

- DuckDB スキーマを初期化する
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  # conn は duckdb の接続オブジェクト (DuckDBPyConnection)
  ```

- 既存 DB に接続する（スキーマ初期化はしない）
  ```python
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  ```

- 自動 .env 読み込みを抑制して手動で環境を設定する
  ```python
  import os
  os.environ["KABUSYS_DISABLE_AUTO_ENV_LOAD"] = "1"
  # 以降で kabusys を import すると自動ロードは行われません
  ```

注意:
- `settings` の必須プロパティにアクセスするとき、該当環境変数が未設定の場合は ValueError が発生します。実行前に必須変数を設定してください。

## ディレクトリ構成

プロジェクト（抜粋）:
```
src/
  kabusys/
    __init__.py          # パッケージ初期化 (バージョン等)
    config.py            # 環境変数・設定管理
    data/
      __init__.py
      schema.py          # DuckDB スキーマ定義と init_schema/get_connection
    strategy/
      __init__.py        # 戦略用プレースホルダ
    execution/
      __init__.py        # 発注/実行用プレースホルダ
    monitoring/
      __init__.py        # 監視用プレースホルダ
```

主なファイルの役割:
- src/kabusys/config.py: .env 自動読み込みロジック、`Settings` クラスと `settings` インスタンス
- src/kabusys/data/schema.py: 全テーブルの DDL、インデックス、スキーマ初期化 API
- strategy / execution / monitoring パッケージは拡張用の領域として用意されています。

## 実装上の注意点・設計メモ
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。テストや特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD` で抑制できます。
- .env のパースはシェル風の書式にある程度対応しています（export フォーマット、クォート・エスケープ、コメント取り扱い等）。
- DuckDB スキーマ初期化は冪等（既存テーブルがあればスキップ）で、`db_path` の親ディレクトリがなければ自動作成されます。メモリ DB を使う場合は `":memory:"` を指定できます。

## 今後の拡張案
- strategy / execution / monitoring の具体的な実装（シグナル生成、注文送信、約定管理、Slack 通知等）
- マイグレーション機能やスキーマ変更に対するバージョニング
- テスト用のモック・フィクスチャ、CI の整備

---

不明点や README に追加したい内容（例: 実際の .env.example、依存パッケージ一覧、使い方のより詳しい例など）があれば教えてください。README を更新して反映します。