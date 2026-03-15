# KabuSys

日本株向け自動売買基盤（ライブラリ）  
バージョン: 0.1.0

短い説明:
KabuSys は日本株のデータ収集・加工・特徴量生成・発注管理までを想定した自動売買システムの基礎ライブラリです。DuckDB を用いたローカルデータベーススキーマ定義、環境変数による設定管理、戦略・実行・モニタリングのためのパッケージ構成を提供します（主要機能はモジュール化済みで今後の実装を想定）。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡単な例）
- 環境変数一覧
- .env の自動読み込み挙動
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の目的で設計されています。

- 市場データ / 財務データ / ニュース / 約定データ等の「原データ (Raw Layer)」の保存
- 日次整形データ（Processed Layer）や特徴量（Feature Layer）、AI スコアなどの管理
- シグナル・オーダー・トレード・ポジション・ポートフォリオ実績などの実行関連データの管理（Execution Layer）
- 環境変数ベースの設定取得（設定は .env ファイルまたは環境変数から読み込み）
- DuckDB による永続化スキーマの初期化ユーティリティ

このリポジトリはライブラリ/基盤部分が中心で、実際の売買ロジック（strategy）や発注処理（execution）、モニタリング（monitoring）はモジュールとして分離されており、ユーザー実装・拡張を想定しています。

---

## 機能一覧

- 環境設定管理
  - Settings オブジェクト経由で必要な設定値を取得
  - 必須環境変数が未設定の場合は ValueError を送出
  - .env / .env.local の自動読み込み（プロジェクトルート判定による）
  - export 形式、クォート、インラインコメントなどを考慮した .env パーサ

- データベーススキーマ（DuckDB）
  - Raw / Processed / Feature / Execution の各レイヤーのテーブル DDL を定義
  - init_schema(db_path) でテーブルとインデックスを作成（冪等）
  - get_connection(db_path) で既存 DB に接続
  - :memory: を指定してインメモリ DB を利用可能

- パッケージ構成（拡張ポイント）
  - data: スキーマ・データ処理
  - strategy: 戦略実装用（プレースホルダ）
  - execution: 発注・取引処理（プレースホルダ）
  - monitoring: モニタリング（プレースホルダ）

---

## セットアップ手順

前提:
- Python 3.9+（typing のユニオン型 | を使用しているため）
- pip が利用可能

1. リポジトリをクローンする（任意）
   git clone <repo-url>

2. パッケージを開発モードでインストール（推奨）
   python -m pip install -e .

   ※ pyproject.toml / setup.cfg があれば上記でインストールできます。ない場合はローカルの src パスを PYTHONPATH に追加するか、直接スクリプトから import してください。

3. 必要なライブラリをインストール
   - 最低依存: duckdb
   - 例:
     python -m pip install duckdb

   （プロジェクトに応じて requests や Slack クライアント等を追加でインストールしてください）

4. 環境変数を準備
   - .env をプロジェクトルートに置くか、シェルの環境変数として設定します。
   - 必須の環境変数は下記「環境変数一覧」を参照してください。

5. データベース初期化（任意）
   - サンプル: Python REPL またはスクリプト内で init_schema を呼び出して DuckDB ファイルを作成します（詳細は次節）。

---

## 使い方（簡単な例）

- Settings を使って環境設定を取得する例:

  from kabusys.config import settings
  token = settings.jquants_refresh_token
  print(settings.env, settings.log_level)

- DuckDB スキーマの初期化:

  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  # デフォルトは settings.duckdb_path （例: data/kabusys.duckdb）
  conn = init_schema(settings.duckdb_path)

  # メモリ DB を使う場合
  conn_mem = init_schema(":memory:")

- 既存 DB に接続するだけの場合:

  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")

注意:
- init_schema は指定したパスの親ディレクトリが存在しない場合、自動で作成します。
- 環境変数に必須キーが無い場合、settings のプロパティアクセス時に ValueError が発生します。

---

## 環境変数一覧

必須（Settings のプロパティで _require を呼ぶもの）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意・デフォルトあり:
- KABUSYS_ENV: "development" (既定), 有効値は "development", "paper_trading", "live"
- LOG_LEVEL: "INFO" (既定), 有効値は "DEBUG","INFO","WARNING","ERROR","CRITICAL"
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" を設定すると自動 .env ロードを無効化
- KABUSYS_API_BASE_URL 等は直接参照されるものは無し（ただし KABU_API_BASE_URL はデフォルト http://localhost:18080/kabusapi を返す）
- DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: デフォルト "data/monitoring.db"

例 (.env):
  JQUANTS_REFRESH_TOKEN=your_token_here
  KABU_API_PASSWORD=your_kabu_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  KABUSYS_ENV=development
  LOG_LEVEL=DEBUG

.env の例ファイル (.env.example) をプロジェクトで用意しておくことを推奨します（ライブラリ内部で参照するわけではありませんが、未設定時のエラーメッセージで参照されています）。

---

## .env 自動読み込みの挙動

- パッケージ起点で .env を自動読み込みします（デフォルトで有効）。
- プロジェクトルートは現在モジュールのファイル位置（__file__）から親方向に探索し、以下いずれかを満たすディレクトリをルートとみなします:
  - .git が存在するディレクトリ
  - pyproject.toml が存在するディレクトリ
- 読み込み順:
  1. OS 環境変数（既に設定済みのもの）
  2. .env（プロジェクトルート内） — override=False （未設定のキーのみ設定）
  3. .env.local — override=True（既存 OS 環境変数は保護され上書きされない）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト向けなど）。
- .env パーサは以下をサポート:
  - export KEY=val 形式
  - シングル/ダブルクォート内のエスケープ処理
  - クォートなしのインラインコメント（#）の扱い（直前が空白/タブの場合のみコメントと判断）

---

## ディレクトリ構成

本リポジトリでの主要ファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py              # パッケージ定義、__version__
    - config.py                # 環境変数・設定管理（Settings）
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ定義 & init_schema / get_connection
    - strategy/
      - __init__.py            # 戦略モジュール（拡張ポイント）
    - execution/
      - __init__.py            # 発注/実行モジュール（拡張ポイント）
    - monitoring/
      - __init__.py            # モニタリング（拡張ポイント）

README に含めていないが重要な点:
- data/schema.py に大量の CREATE TABLE 文が定義されており、Raw / Processed / Feature / Execution の各テーブルとインデックスが準備されています。
- スキーマは外部キーの依存関係を考慮してテーブルを作成します。

---

## トラブルシューティング

- ValueError: 環境変数が足りない
  - settings のプロパティを呼んだ際に必須のキーが未設定だと ValueError が発生します。必要なキーをシェルまたは .env に設定してください。

- .env が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
  - プロジェクトルートの判定は .git または pyproject.toml の存在に依存します。開発環境ではこれらが無い場合は .env を手動で export してください。

- DuckDB に接続できない / ファイルが作れない
  - init_schema は必要に応じて親ディレクトリを作成しますが、権限等で作成できない場合はエラーになります。パスや権限を確認してください。

---

必要に応じて README を拡張します。実際の戦略実装や発注処理、外部 API クライアント（J-Quants / kabuステーション / Slack 等）の使い方を追加したい場合は、どの部分に詳細を追加するか教えてください。