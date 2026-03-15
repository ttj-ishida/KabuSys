# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ（骨組み）。データ収集・スキーマ定義・環境設定管理・発注/モニタリング用のモジュール群を想定しています（現状は主に設定管理と DuckDB スキーマ初期化を実装）。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムを構築するための共通基盤コードです。本リポジトリでは主に以下を提供します。

- 環境変数/設定の一元管理（.env 自動読み込み、必須変数の検証）
- DuckDB を用いた多層データスキーマ（Raw / Processed / Feature / Execution 層）の定義と初期化関数
- 将来的な戦略（strategy）、発注（execution）、データ（data）、モニタリング（monitoring）モジュールの骨組み

現在の実装は設定管理（config）とデータスキーマ（data/schema）に重点があります。

---

## 機能一覧

- 環境変数の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` をロード
  - `.env.local` は `.env` の上書き（ただし OS 環境変数は保護）
  - 自動ロードを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定可能
  - .env のパースはシングル/ダブルクォート、エスケープ、インラインコメントなどに対応

- Settings クラス
  - J-Quants、kabuステーション、Slack、データベースパス、実行環境（development/paper_trading/live）、ログレベル等の取得
  - 必須パラメータ未設定時に例外を送出して注意喚起

- DuckDB スキーマ管理（data/schema）
  - Raw / Processed / Feature / Execution の各層に対応するテーブル DDL を定義
  - インデックス作成
  - init_schema(db_path) による初期化（冪等）
  - get_connection(db_path) による既存 DB への接続取得
  - デフォルトの DuckDB パス: `data/kabusys.duckdb`

---

## 前提条件

- Python >= 3.10（ソース内での型注釈に Union 演算子 `|` を使用）
- duckdb（DuckDB Python パッケージ）
- （任意）その他 API 接続や通知に必要なライブラリ（kabu API クライアント、Slack SDK 等）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境を作成して有効化（推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 依存パッケージをインストール
   - 最低限 DuckDB をインストールしてください:
     ```
     pip install duckdb
     ```
   - 開発時はプロジェクトルートに pyproject.toml や requirements.txt があればそれに従ってください。
   - 開発インストール（パッケージ化済みの場合）:
     ```
     pip install -e .
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env`（と必要であれば `.env.local`）を作成してください。
   - 必須環境変数（Settings により参照されます）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意:
     - KABU_API_BASE_URL（デフォルト: `http://localhost:18080/kabusapi`）
     - DUCKDB_PATH（デフォルト: `data/kabusys.duckdb`）
     - SQLITE_PATH（デフォルト: `data/monitoring.db`）
     - KABUSYS_ENV（`development` / `paper_trading` / `live`、デフォルト: `development`）
     - LOG_LEVEL（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`、デフォルト: `INFO`）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD（自動 .env ロードを無効化する場合は `1` を設定）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（クイックスタート）

- 設定オブジェクトの利用例
  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)  # 未設定なら ValueError
  print(settings.duckdb_path)            # Path オブジェクト
  print(settings.is_live, settings.env)
  ```

- DuckDB スキーマの初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリを作成して初期化
  # conn は duckdb.DuckDBPyConnection
  ```

- 既存 DB へ接続（スキーマ初期化は行わない）
  ```python
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  ```

- .env 自動ロードを無効にする（テスト時など）
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定するか、プロセス起動時に指定してください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py              # 環境変数・Settings 管理、.env 自動読み込みロジック
  - data/
    - __init__.py
    - schema.py            # DuckDB スキーマ定義と初期化関数（init_schema, get_connection）
  - strategy/
    - __init__.py          # 戦略モジュールのプレースホルダ
  - execution/
    - __init__.py          # 発注ロジックのプレースホルダ
  - monitoring/
    - __init__.py          # モニタリング用プレースホルダ

主要なファイルの説明:
- config.py: .env のパースやロード優先度（OS 環境変数 > .env.local > .env）、必須値チェックを実装しています。
- data/schema.py: Raw/Processed/Feature/Execution の各層のテーブル定義（DDL）を持ち、init_schema() によりテーブルとインデックスを作成します。

---

## 注意点 / 実装上の備考

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml の存在）を基準に行います。配布済みパッケージやインストール後でプロジェクトルートが検出できない場合は自動ロードをスキップします。
- Settings._require() は必須変数が未設定の場合に ValueError を送出します。サービス起動前に必要な環境変数が設定されているか確認してください。
- DuckDB のファイルパスが ":memory:" の場合はインメモリ DB として初期化されます。
- 今後、strategy / execution / monitoring の各モジュールに機能を追加していくことを想定しています。

---

## 貢献・ライセンス

貢献やライセンスについてはリポジトリのトップレベルにある CONTRIBUTING.md / LICENSE を参照してください（まだ用意されていない場合は issue を立ててください）。

---

何か追加で README に含めたい情報（CI、デプロイ手順、API 仕様の詳細など）があれば教えてください。