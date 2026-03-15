# KabuSys

日本株向けの自動売買（バックテスト / 実運用）基盤ライブラリです。マーケットデータの収集・保存、特徴量生成、シグナル管理、発注・約定・ポジション管理などのための共通機能とスキーマを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は DuckDB を利用したローカルデータベースと、環境変数ベースの設定管理を備えた小さなフレームワークです。

主な目的は以下です。

- 市場データ・決算・ニュース・発注/約定情報などの原データ（Raw Layer）保存
- 整形済み市場データ（Processed Layer）と特徴量（Feature Layer）管理
- 発注・トレード・ポジション管理（Execution Layer）スキーマ定義
- 環境変数からの設定一元管理（自動 .env ロード機能）

コードベースは戦略（strategy）、発注（execution）、監視（monitoring）を実装するための土台を提供します。

---

## 機能一覧

- 環境変数 / .env ファイルの自動読み込み
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込む
  - 読み込み優先順位: OS環境変数 > .env.local > .env
  - export プレフィックス、クォート、エスケープ、インラインコメント等に対応
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- Settings クラスによる型付きアクセス（必須変数は未設定時にエラー）
  - J-Quants、kabuステーション、Slack、DBパス、環境モードなど
- DuckDB ベースのスキーマ定義と初期化
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス作成
  - init_schema(db_path) による冪等な初期化と接続取得
  - get_connection(db_path) による既存 DB 接続
- パッケージ構成は strategy / execution / monitoring 用の拡張ポイントを想定

---

## 要件

- Python 3.10 以上（型ヒントの union 型（|）を利用）
- duckdb Python パッケージ

推奨:
- 仮想環境（venv / virtualenv / conda 等）

---

## インストール

1. 仮想環境を作成・有効化（任意）
2. 必要パッケージをインストール:

```bash
python -m pip install duckdb
# 開発時にパッケージとして編集可能にインストールする場合:
# python -m pip install -e .
```

（プロジェクトに pyproject/requirements ファイルがあればそこからインストールしてください。）

---

## セットアップ手順（.env と DB 初期化）

1. プロジェクトルートに `.env`（と必要なら`.env.local`）を作成する。例:

```
# .env (例)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# オプション
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABU_API_BASE_URL=http://localhost:18080/kabusapi
```

- 自動ロードはデフォルトで有効です。テストなどで無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境変数に設定します。
- 読み込み順は OS > .env.local > .env です。OS 環境変数は上書きされません。

2. DB スキーマの初期化（例）:

Python スクリプトや REPL で:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Path オブジェクトを返します
conn = init_schema(settings.duckdb_path)
# またはインメモリ:
# conn = init_schema(":memory:")
```

init_schema() は指定したパスの親ディレクトリを自動で作成し、全テーブルとインデックスを作ります（冪等）。

---

## 使い方（簡単な例）

- 設定値の参照:

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)
print(settings.is_live)
```

- DuckDB 接続（初回にスキーマを作成）:

```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# 初期化して接続を取得
conn = init_schema(settings.duckdb_path)

# 既存 DB に接続（スキーマ初期化は行わない）
conn2 = get_connection(settings.duckdb_path)
```

- パッケージ情報:

```python
import kabusys
print(kabusys.__version__)
```

- 拡張ポイント:
  - src/kabusys/strategy: 戦略ロジックと特徴量生成
  - src/kabusys/execution: 発注・約定処理、kabu API ラッパー
  - src/kabusys/monitoring: Slack などを使った監視・アラート

---

## 環境変数一覧（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルトあり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live、デフォルト: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL、デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 にすると .env 自動ロードを無効化)

注意:
- Settings クラスは必須キーが未設定の場合 ValueError を送出します。

---

## ディレクトリ構成

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py           # パッケージ定義, __version__
│     ├─ config.py             # 環境変数 / 設定管理
│     ├─ data/
│     │  ├─ __init__.py
│     │  └─ schema.py          # DuckDB スキーマ定義と初期化 API
│     ├─ strategy/
│     │  └─ __init__.py        # 戦略ロジック用（拡張ポイント）
│     ├─ execution/
│     │  └─ __init__.py        # 発注 / 実行ロジック用（拡張ポイント）
│     └─ monitoring/
│        └─ __init__.py        # 監視 / 通知用（拡張ポイント）
├─ pyproject.toml (想定)
├─ .git/ (想定)
└─ .env, .env.local (利用者が追加)
```

---

## 開発メモ・注意点

- .env のパースは独自実装です。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応していますが、極端なケースは想定外の振る舞いをする可能性があります。
- 自動環境読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。パッケージ配布後でも CWD に依存せず動作するよう設計されています。
- DuckDB の初期化は冪等です。既存テーブルがあれば上書きしませんが、DDL を変更した場合は手動でのマイグレーションが必要です。
- Strategy / Execution / Monitoring モジュールは雛形のままです。実際の売買ロジックや API クライアント、監視処理はプロジェクト固有に実装してください。

---

必要があれば README の英語版や、.env.example、簡単なサンプル戦略コード、DuckDB によるクエリ例も追加します。どれを優先しますか？