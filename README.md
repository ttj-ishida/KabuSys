# KabuSys

KabuSys は日本株の自動売買基盤のための軽量ライブラリ群です。市場データの保存（DuckDB）、環境設定管理、戦略・発注・監視のための基盤モジュールを提供します。現時点ではコアとなるスキーマ定義と環境設定周りが実装されており、戦略・実行・監視の実装を組み込める構成になっています。

バージョン: 0.1.0

---

## 概要

- 日本株自動売買に必要なデータ層（Raw / Processed / Feature / Execution）の DuckDB スキーマを定義・初期化するモジュールを提供します。
- .env（および .env.local）から環境変数を自動で読み込み、アプリケーション設定を型付きプロパティとして取得できます（Settings）。
- 発注や監視、戦略実装用のパッケージが用意されており、拡張して使える構成です。

---

## 主な機能

- 環境変数読み込みと集中管理
  - .env / .env.local をプロジェクトルートから自動ロード（必要に応じて無効化可能）
  - 必須項目は Settings プロパティ経由で簡単に取得・バリデーション
- DuckDB を用いたスキーマ定義・初期化
  - Raw / Processed / Feature / Execution のレイヤで複数テーブルを定義
  - インデックスや外部キー、制約を含むDDLを冪等に実行
  - ":memory:" を指定してインメモリ DB も可能
- パッケージ構造（strategy / execution / monitoring / data）を用意して、各機能を分離して実装可能

---

## 必要要件

- Python 3.10 以上（型ヒントで `X | Y` の構文を使用しているため）
- duckdb (データベース操作に使用)

その他、実運用で使う場合は以下の外部サービスの認証情報等が必要です（J-Quants、kabuステーション、Slack など）。

---

## インストール

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

2. 必要パッケージをインストール
   - 最低限: duckdb
     - pip install duckdb

3. パッケージを開発モードでインストール（プロジェクトルートに pyproject.toml / setup.py がある想定）
   - pip install -e .

（プロジェクトに requirements.txt や pyproject.toml がある場合はそれらを使ってください。）

---

## 環境変数と設定 (.env)

プロジェクトルートの .env / .env.local を自動で読み込みます（読み込みは OS 環境変数より低優先）。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（Settings で参照されるもの）:

- JQUANTS_REFRESH_TOKEN (必須): J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API のパスワード
- KABU_API_BASE_URL (任意): kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack ボットトークン
- SLACK_CHANNEL_ID (必須): 通知先の Slack チャンネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意): 環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL (任意): ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
KABU_API_BASE_URL="http://localhost:18080/kabusapi"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV="development"
LOG_LEVEL="DEBUG"
```

注意: .env ではシングル/ダブルクォートやエスケープを適切に扱うように実装されています。コメントや export 形式もサポートしています。

---

## スキーマ初期化（DuckDB）

DuckDB スキーマを初期化するには data.schema.init_schema() を使用します。親ディレクトリが存在しない場合は自動で作成されます。":memory:" を指定するとインメモリ DB が使えます。

サンプル:
```py
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクトを返します
conn = init_schema(settings.duckdb_path)
# conn は duckdb の接続オブジェクト（duckdb.DuckDBPyConnection）
```

既にテーブルが存在する場合はスキーマ作成処理はスキップされる（冪等）ため、何度呼んでも安全です。

既存 DB に接続するだけなら:
```py
from kabusys.data.schema import get_connection
conn = get_connection(settings.duckdb_path)
```

---

## 基本の使い方（例）

- 設定値の取得:
```py
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
log_level = settings.log_level
```

- DB 初期化（先の例を参照）:
```py
from kabusys.data.schema import init_schema

# ファイル DB を初期化
conn = init_schema("data/kabusys.duckdb")

# インメモリ DB を初期化（テスト用）
mem_conn = init_schema(":memory:")
```

- 実装の拡張ポイント:
  - kabusys.strategy: 戦略ロジック（特徴量計算、シグナル生成など）
  - kabusys.execution: 発注処理、オーダー管理
  - kabusys.monitoring: 監視・通知・パフォーマンス集計

これらのパッケージは初期化用の __init__.py の準備がされているため、独自実装を追加して利用してください。

---

## ディレクトリ構成

プロジェクト内の主なファイル／ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
    - パッケージのエクスポート（data, strategy, execution, monitoring）
  - config.py
    - .env 自動読み込み、Settings クラス（アプリ設定）
  - data/
    - __init__.py
    - schema.py
      - DuckDB の DDL 定義・初期化関数（init_schema, get_connection）
  - strategy/
    - __init__.py
    - （戦略関連コードを配置）
  - execution/
    - __init__.py
    - （発注・注文管理コードを配置）
  - monitoring/
    - __init__.py
    - （監視・通知・メトリクス関連コードを配置）

補足:
- .env / .env.local はプロジェクトルートに置く想定です（.git もしくは pyproject.toml がプロジェクトルート判定に使われます）。

---

## 開発・テストについて

- 自動で .env をロードする機能はテスト時に影響する場合があるため、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- DuckDB のインメモリモード（":memory:"）を使えばテスト環境で簡単にスキーマ初期化と操作ができます。

---

## 今後の拡張案（参考）

- J-Quants / kabu API クライアントラッパーの追加
- データ取得ジョブ（株価、決算、ニュース）と定期更新処理
- 戦略バックテストフレームワークの追加
- 発注失敗時の再試行・ロールバック処理、監査ログ

---

## ライセンス / コントリビューション

本リポジトリにライセンスやコントリビューションガイドが存在する場合はそれに従ってください。プルリクエストや issue を歓迎します。

---

不明点や README に追加してほしい内容があれば教えてください。必要なら .env.example のテンプレートや具体的な戦略実装の雛形も用意できます。