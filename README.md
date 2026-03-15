# KabuSys

日本株向けの自動売買（投資）システムの骨組みを提供する Python パッケージです。市場データの取り込みから特徴量作成、シグナル生成、発注履歴・ポジション管理までを想定したモジュール構成と、DuckDB ベースのスキーマ初期化機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買システムの基盤ライブラリです。以下の要素に対応するコード構成を提供します。

- 環境変数/設定の管理（.env 自動読み込み機能）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution の 3+1 層）
- 戦略（strategy）、発注/実行（execution）、監視（monitoring）といったモジュールの置き場

設計方針として、データ層は冪等にテーブルを作成でき、実運用（live）とペーパートレード（paper_trading）や開発（development）を切り替えられる設定管理を備えています。

---

## 主な機能一覧

- 環境変数の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）にある `.env`、`.env.local` を自動で読み込み
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能
  - シンプルな .env パーサ（クォート、エスケープ、コメントの取り扱いに対応）
- アプリケーション設定
  - 必須変数は取得時に存在チェックを行い、未設定時は明示的なエラーを出力
  - `KABUSYS_ENV`（development / paper_trading / live）や `LOG_LEVEL` のバリデーション
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution レイヤのテーブル定義を収録
  - インデックス定義を含む。init_schema は冪等（既存テーブルはスキップ）
  - `:memory:` 指定でインメモリ DB を利用可能
- パッケージ基盤（strategy, execution, monitoring モジュールの置き場）

---

## セットアップ手順

1. Python 環境を用意（Python 3.9+ 推奨）
   - 仮想環境を使うことを推奨します:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows では .venv\Scripts\activate)

2. 依存パッケージをインストール
   - プロジェクトに requirements.txt / pyproject.toml がある想定ですが、最低限 DuckDB は必要です:
     - pip install duckdb
   - パッケージを編集可能インストールする場合:
     - pip install -e .

3. 環境変数を設定
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成してください。
   - 自動読み込みはデフォルトで有効です。テストなどで無効にする場合は環境変数で制御できます。

4. データベース初期化（任意）
   - DuckDB スキーマを作成するには次節の「使い方」を参照してください。

---

## 使い方 (例)

以下は基本的な使い方例です。

- 設定を参照する

```python
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path
```

- DuckDB スキーマを初期化する

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path を返します（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection オブジェクト
```

- 既存 DB に接続する（スキーマ初期化は行わない）

```python
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
```

- .env 自動読み込みの振る舞い
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` → `.env.local` の順で読み込まれます。
  - `.env.local` は `.env` のキーを上書きします（既に OS 環境変数に存在するキーは保護され上書きされません）。
  - 自動読み込みを無効にするには:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 環境変数（主要）

コードで参照される主要な環境変数は以下です（必須は明記）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite (monitoring) のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development | paper_trading | live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL。デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 をセット）

サンプル .env（プロジェクトルートに配置）:

```
# .env.example
JQUANTS_REFRESH_TOKEN="your-jquants-refresh-token"
KABU_API_PASSWORD="your-kabu-password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C0123456789"
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## DuckDB スキーマ概略

データベースは 4 層（実際には Raw / Processed / Feature / Execution）で構成され、主要なテーブルを以下のように定義しています（抜粋）:

- Raw Layer
  - raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer
  - features, ai_scores
- Execution Layer
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

init_schema() を呼ぶと上記のテーブルといくつかのインデックスが作成されます（既に存在する場合はスキップします）。

---

## ディレクトリ構成

リポジトリ内のおおまかな構成は次のとおりです（抜粋）。

- src/
  - kabusys/
    - __init__.py  -- パッケージのエントリポイント（__version__ 等）
    - config.py    -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - schema.py  -- DuckDB スキーマ定義と初期化ロジック
    - strategy/
      - __init__.py -- 戦略関連のモジュールを配置するためのパッケージ
    - execution/
      - __init__.py -- 発注・実行関連のモジュールを配置するためのパッケージ
    - monitoring/
      - __init__.py -- 監視・メトリクス保存等を置くパッケージ

上記以外にプロジェクトルートに `.env`, `.env.local`, pyproject.toml / setup.cfg 等が存在する想定です。

---

## 開発・カスタマイズのヒント

- strategy、execution、monitoring の各パッケージは現状プレースホルダになっているため、ここにアルゴリズムや実行ロジック、Slack 通知等を実装してください。
- DuckDB のスキーマを変更する際は、DDL を schema.py に追加し、init_schema() の挙動（冪等性）を保つ形で調整してください。
- テスト時に .env 自動読み込みを無効にしたい場合は、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

もし README に追加したい手順（CI、デプロイ、サンプル戦略、CLI コマンドなど）があれば教えてください。必要に応じて追記します。