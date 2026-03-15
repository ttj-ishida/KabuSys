# KabuSys

日本株向け自動売買システムのライブラリ（パッケージ）。データ収集・スキーマ定義、特徴量管理、戦略・発注・モニタリングのための基盤を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買に必要な共通基盤を提供する Python パッケージです。  
主に以下を含みます。

- 環境変数・設定管理（.env の自動読み込み、必須・任意設定の取得）
- DuckDB を使ったスキーマ定義と初期化（Raw / Processed / Feature / Execution レイヤ）
- 将来的な戦略（strategy/）、発注（execution/）、監視（monitoring/）のためのモジュール構成

本リポジトリはライブラリ本体であり、戦略の実装や実行フローは各プロジェクトで組み合わせて利用します。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（OS 環境変数を尊重）
  - export 形式、クォートやエスケープ、コメントの扱いに対応
  - 必須環境変数チェック
  - 実行環境判定（development / paper_trading / live）とログレベル設定の検証
- データ層（DuckDB）
  - Raw / Processed / Feature / Execution の多層スキーマを定義
  - テーブル作成は冪等（既存テーブルは上書きされない）
  - インデックス定義
  - init_schema() / get_connection() API を提供

---

## 前提・依存関係

- Python 3.10 以上（型注釈の union 記法などを使用）
- duckdb Python パッケージ
  - インストール例: pip install duckdb

※ 他に各種 API（J-Quants / kabuステーション / Slack）を利用するには、それぞれのクレデンシャルが必要です。

---

## セットアップ手順

1. リポジトリをクローンしてローカルで開発する場合（例）:
   - git clone ...
   - cd <repo>
   - pip install -e .

2. 必要パッケージのインストール（最低限 duckdb）:
   - pip install duckdb

3. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を配置してください（`.env.local` は `.env` を上書きする）。`.env.example` を参考に作成します（リポジトリに例ファイルがある場合）。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境に設定してください（テスト用途など）。

4. 必須環境変数（未設定だと起動時にエラーになります）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

5. 任意・デフォルト値
   - KABU_API_BASE_URL: デフォルト `http://localhost:18080/kabusapi`
   - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
   - SQLITE_PATH: デフォルト `data/monitoring.db`
   - KABUSYS_ENV: デフォルト `development`（有効値: `development`, `paper_trading`, `live`）
   - LOG_LEVEL: デフォルト `INFO`（有効値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）

---

## 使い方（簡単な例）

- 設定値を読み取る
  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)
  print(settings.kabu_api_base_url)
  print(settings.duckdb_path)
  ```

- DuckDB スキーマを初期化して接続を取得する
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.config import settings

  # ファイル DB を初期化（設定の DUCKDB_PATH を使用）
  conn = init_schema(settings.duckdb_path)

  # またはインメモリ DB を使用
  mem_conn = init_schema(":memory:")

  # 既存 DB に接続（スキーマ初期化は実行しない）
  conn2 = get_connection(settings.duckdb_path)
  ```

- .env 自動ロードの挙動
  - 実行時、プロジェクトルート（.git または pyproject.toml を基準）を自動検出します。
  - 読み込み順: OS 環境変数（優先） > .env.local（override=True） > .env（override=False）
  - OS 環境変数は保護され、.env(.local) によって上書きされません。
  - 無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 環境変数ファイルのパース機能
  - `export KEY=val` 形式に対応
  - シングル／ダブルクォート内でのエスケープに対応（バックスラッシュ）
  - クォートなしの値では、`#` の前にスペース/タブがあれば以降をコメントとして無視

---

## ディレクトリ構成

リポジトリの主要ファイル（抜粋）:

- src/
  - kabusys/
    - __init__.py              # パッケージ初期化（__version__, __all__）
    - config.py                # 環境変数・設定管理（自動 .env ロード、settings オブジェクト）
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ定義と init_schema / get_connection
    - strategy/
      - __init__.py            # 戦略モジュール（未実装のスケルトン）
    - execution/
      - __init__.py            # 発注実装（未実装のスケルトン）
    - monitoring/
      - __init__.py            # 監視・モニタリング（未実装のスケルトン）

主要モジュールの目的:
- config.py: アプリ全体の設定・環境変数の取得を集中管理
- data/schema.py: DuckDB 用のテーブル定義（Raw / Processed / Feature / Execution）とインデックス、初期化処理
- strategy / execution / monitoring: 将来的な機能拡張ポイント

---

## その他メモ

- DuckDB のスキーマは外部キー依存を考慮して作成順を管理しています。init_schema() は親ディレクトリがない場合でも自動作成します。
- settings.env の値は検証が行われ、不正な値があると ValueError を投げます（例: KABUSYS_ENV や LOG_LEVEL）。
- 本パッケージは基盤ライブラリです。実際のトレード運用や戦略実装は別モジュール／アプリケーションで行ってください。

---

必要があれば、README に含めるサンプルのコマンドや .env.example のテンプレート、CI/デプロイ手順、開発者向けドキュメントの追加を作成します。どの情報を追加したいか教えてください。