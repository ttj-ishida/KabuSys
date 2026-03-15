# KabuSys

日本株向けの自動売買システム（ライブラリ基盤）。データ取得・加工（Raw → Processed → Feature 層）、戦略、発注・約定・ポジション管理、モニタリングを想定したモジュール群を提供します。  
（このリポジトリはコアライブラリの一部を含みます：環境設定、DuckDB スキーマ定義、設定管理など）

## 主な特徴
- 環境変数ベースの設定管理（.env / .env.local の自動読み込みをサポート）
  - export 形式、クォート文字、インラインコメントなどの柔軟なパース処理に対応
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env を自動探索
  - OS 環境変数優先、.env.local は .env を上書き
  - 自動ロードの無効化フラグ：`KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- アプリケーション設定オブジェクト（settings）経由で所要の環境変数を参照
  - J-Quants, kabuステーション, Slack, DB パス等の設定項目を提供
- DuckDB を用いた永続データレイヤーのスキーマ定義と初期化
  - Raw / Processed / Feature / Execution の多層スキーマを提供
  - 冪等なテーブル作成（既存テーブルがあればスキップ）
  - インデックス定義や外部キー整合を考慮した作成順を実装
  - `init_schema()` で DB を初期化、`get_connection()` で接続取得
- 軽量で拡張しやすいディレクトリ構成（strategy / execution / monitoring モジュールのプレースホルダあり）

## 必要条件
- Python 3.10 以上（型アノテーションに `X | Y` を使用）
- duckdb（データベース操作に使用）
- （運用時）kabuステーション API、J-Quants API、Slack などの外部サービスの認証情報

## インストール（開発環境）
1. 仮想環境を作る（例）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate
2. 必要パッケージをインストール
   - pip install duckdb
3. （パッケージ化されている場合）プロジェクトを editable インストール
   - pip install -e .

※ pyproject.toml / requirements.txt がプロジェクトルートにある想定です。環境依存ライブラリはそれらに追記してください。

## 環境変数（.env）
このプロジェクトは環境変数から設定を読み込みます。必須の主なキー（Settings クラスで参照）：
- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- SLACK_BOT_TOKEN（必須） — Slack ボットトークン
- SLACK_CHANNEL_ID（必須） — Slack チャネル ID

オプション / デフォルト値:
- KABUSYS_ENV — "development"（有効値: development, paper_trading, live）
- LOG_LEVEL — "INFO"（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

例 (.env)
```
JQUANTS_REFRESH_TOKEN="your_jquants_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

読み込み動作:
- 自動読み込み順: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- プロジェクトルートは .git または pyproject.toml を基準に自動検出（CWD に依存しない）

## データベース初期化
DuckDB スキーマを作成するためのユーティリティが提供されています。

例（対話的に初期化する）:
```
python -c "from kabusys.config import settings; from kabusys.data.schema import init_schema; init_schema(settings.duckdb_path)"
```

API:
- init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
  - 指定したパスの DuckDB を初期化（親ディレクトリがなければ作成）
  - ":memory:" を渡すとインメモリ DB
- get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
  - 既存 DB に接続する（スキーマ初期化は行わない）

初期化処理は冪等（既存テーブルがあれば作成しない）なので、本番・開発ともに安全に再実行できます。

## 簡単な使い方（コード例）
設定オブジェクトの取得、DB 初期化、接続取得の例:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection

# settings 経由で環境設定にアクセス
db_path = settings.duckdb_path

# スキーマが未作成なら初期化
conn = init_schema(db_path)

# 以降、conn.execute(...) でクエリを実行
# 別の箇所では既存 DB に接続
conn2 = get_connection(db_path)
```

設定値参照例:
```python
from kabusys.config import settings
print(settings.is_live)        # 本番環境か
print(settings.kabu_api_base_url)
```

自動ロードのスキップ例（テスト等）:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print('loaded')"
```

## ディレクトリ構成（抜粋）
以下はこのリポジトリに含まれる主要ファイル・ディレクトリの構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定管理（自動 .env ロード、Settings）
    - data/
      - __init__.py
      - schema.py               — DuckDB スキーマ定義と init_schema/get_connection
    - strategy/
      - __init__.py             — 戦略ロジック用プレースホルダ
    - execution/
      - __init__.py             — 発注・実行ロジック用プレースホルダ
    - monitoring/
      - __init__.py             — モニタリング用プレースホルダ
- .env.example (想定)           — 必要環境変数の例（プロジェクトルートに置く想定）
- pyproject.toml / setup.cfg 等（プロジェクトルートに存在する想定）

主要ファイルの説明:
- config.py
  - プロジェクトルートの自動検出（.git または pyproject.toml）
  - .env / .env.local のパースとロード（エスケープやクォート対応）
  - Settings クラスでアプリケーション設定を提供（必須キーは未設定時に例外）
- data/schema.py
  - Raw / Processed / Feature / Execution 層のテーブル定義（DDL）
  - インデックスと外部キーを考慮したテーブル作成順
  - init_schema() によりディレクトリ自動作成とテーブル初期化を行う

## 開発・拡張のヒント
- strategy, execution, monitoring パッケージは現在プレースホルダです。ここに戦略アルゴリズム、注文送信ロジック、監視ジョブ等を実装してください。
- DB スキーマは duckdb の DDL を直接実行しているため、カラム追加やインデックス追加は同じモジュールを更新してデプロイすれば良いです（既存カラムの削除や型変更は注意して行ってください）。
- 設定は Settings クラスを通して取得することで、環境変数の参照を一元化できます。ユニットテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使い、必要な環境変数をテスト内で注入してください。

--- 
この README はコードベースの現状（config.py, data/schema.py 等）をもとに作成しています。実際の運用では API クライアント、戦略実装、注文実行の安全性（例：送信前の確認、サーキットブレーカー、ログ・監査）など追加実装を検討してください。