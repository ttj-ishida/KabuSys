# KabuSys

日本株自動売買システムのコアライブラリ（骨組み）。  
このリポジトリはデータ管理、スキーム定義、環境設定、実行・監視モジュールの土台を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けの共通モジュール群です。主に以下を提供します。

- 環境変数／設定の管理（.env 自動ロード、必須設定の検証）
- DuckDB によるデータスキーマ定義と初期化（Raw / Processed / Feature / Execution の多層スキーマ）
- 戦略（strategy）、発注／実行（execution）、監視（monitoring）、データ（data）用のパッケージ構成（骨組み）
- Slack 等への通知や外部 API の接続情報を環境変数で一元管理

このリポジトリはフル実装というよりは、システムを構築するための基盤部分を提供します。

---

## 機能一覧

- 設定管理 (kabusys.config)
  - .env/.env.local の自動ロード（プロジェクトルートの判定は .git / pyproject.toml）
  - 必須環境変数の取得（未設定時は例外を投げる）
  - 環境（development / paper_trading / live）判定、ログレベル検証
  - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- データスキーマ管理 (kabusys.data.schema)
  - DuckDB にテーブル群を作成する init_schema(db_path)
  - テーブルは Raw / Processed / Feature / Execution の層で分離
  - 頻出クエリ向けのインデックスを作成
  - ":memory:" でインメモリ DB を使える

- パッケージ構成
  - kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring の各モジュール（骨組み）

---

## 必要な環境変数（代表）

以下はこのライブラリで参照される主要な環境変数です。実行環境や利用する機能に応じて追加の設定が必要になる可能性があります。

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB）パス（省略時: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ('development'|'paper_trading'|'live'), 省略時 'development'
- LOG_LEVEL — ログレベル ('DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL'), 省略時 'INFO'

.example（.env のテンプレート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. Python と依存ライブラリを準備
   - Python のバージョンはプロジェクト要件に合わせてください（本リポジトリでは duckdb が必要です）。
   - 例:
     pip install duckdb

2. リポジトリをクローン／チェックアウト

3. プロジェクトルートに `.env` を作成
   - 上のテンプレートを参考に必須環境変数を設定してください。
   - `.env.local` を使ってローカル固有の設定（シークレットや上書き）を置くこともできます。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

4. パッケージのインストール（開発時）
   - 開発環境で参照する場合:
     pip install -e .

   （パッケージ配布手順は別途 pyproject.toml 等で設定してください）

---

## 使い方（簡易例）

- 設定値の取得
```python
from kabusys.config import settings

# 必須値は未設定だと ValueError を投げます
token = settings.jquants_refresh_token
kabu_pass = settings.kabu_api_password
is_live = settings.is_live
db_path = settings.duckdb_path
```

- DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# ファイル DB を初期化
conn = init_schema(settings.duckdb_path)

# インメモリ DB を使う場合
mem_conn = init_schema(":memory:")
```

- 既存 DB へ接続（スキーマ初期化は行わない）
```python
from kabusys.data.schema import get_connection
conn = get_connection(settings.duckdb_path)
```

- .env の自動ロード挙動
  - プロジェクトルートはこのライブラリのファイル位置から親ディレクトリを遡って `.git` または `pyproject.toml` を基準に判定します。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - .env のパースはシェル風の簡易実装（export 対応、クォートとエスケープ、コメント処理）を行います。

---

## ディレクトリ構成

リポジトリ内の主要ファイル／ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py                # パッケージエントリ（__version__ = "0.1.0"）
    - config.py                  # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py                # DuckDB スキーマ定義・初期化（init_schema, get_connection）
    - strategy/
      - __init__.py              # 戦略モジュール（拡張ポイント）
    - execution/
      - __init__.py              # 発注／実行モジュール（拡張ポイント）
    - monitoring/
      - __init__.py              # 監視モジュール（拡張ポイント）

主要な DB テーブル（schema.py に定義）
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

---

## 開発／拡張ポイント

- strategy、execution、monitoring パッケージは骨組みだけなので、ここに具体的な戦略ロジック、注文送信ロジック、監視/通知ロジックを実装します。
- schema.py のスキーマは DataSchema.md（存在する場合）に基づいた初期版です。要件に合わせてカラムやインデックスを拡張してください。
- 環境変数ロードの挙動は config.py 内で実装されているため、必要ならパースルールや優先順位を調整できます。

---

## トラブルシュート

- .env が読み込まれない
  - プロジェクトルートが判定できない場合（.git や pyproject.toml が無い）自動ロードはスキップされます。手動で環境変数を設定するか、`KABUSYS_DISABLE_AUTO_ENV_LOAD` を見直してください。
- 必須の設定が無い場合
  - settings の各プロパティ（例: settings.jquants_refresh_token）は未設定だと ValueError を投げます。.env を用意してください。
- DuckDB の初期化でディレクトリがない
  - init_schema は親ディレクトリを自動作成します。パスが正しいか確認してください。

---

必要に応じて README を拡張します。README に含めたい追加情報（CI、セットアップスクリプト、利用上の注意点など）があれば教えてください。