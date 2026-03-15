# KabuSys

日本株向けの自動売買システム（骨組み）。  
本リポジトリはデータ管理・スキーマ定義・環境設定のユーティリティを提供します。  
戦略（strategy）や発注（execution）、監視（monitoring）のための基盤コードを含みます。

## 概要
- プロジェクト名: KabuSys
- 目的: 日本株の自動売買システムを構築するための基盤ライブラリ
- 提供機能:
  - 環境変数・設定管理（.env 自動読み込みを含む）
  - DuckDB を用いた多層データスキーマ（Raw / Processed / Feature / Execution）
  - スキーマ初期化ユーティリティ
  - settings オブジェクトによる型付けされた設定アクセス

## 主な機能一覧
- 自動環境変数読み込み
  - プロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動で読み込み
  - OS 環境変数を保護するための上書き規則
  - 自動読み込みを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- 型付き設定オブジェクト (`kabusys.config.settings`)
  - 必須変数は未設定時に例外を投げる（_require による検証）
  - 環境モード（development / paper_trading / live）・ログレベルのバリデーション
- DuckDB スキーマ定義と初期化 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution の多層データモデルを DDL で定義
  - インデックス、外部キー、制約を含むテーブル群
  - `init_schema(db_path)` でデータベースの初期化（冪等）
  - in-memory DB（":memory:"）にも対応
- パッケージ構造の雛形（strategy / execution / monitoring の入り口）

## セットアップ手順（開発環境）
以下は最低限のセットアップ例です。環境や運用方法に合わせて調整してください。

1. Python 環境を用意
   - 推奨: Python 3.10+
   - 仮想環境を作成・有効化
     - Linux / macOS:
       - python -m venv .venv
       - source .venv/bin/activate
     - Windows:
       - python -m venv .venv
       - .venv\Scripts\activate

2. 依存パッケージをインストール
   - 必要最小限の依存: duckdb
   - 例:
     - pip install duckdb

   （プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください。）

3. パッケージのインストール（開発向け）
   - プロジェクトルートに pyproject.toml がある想定で:
     - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定してください。
   - 自動読み込みの動作:
     - OS 環境変数が最優先
     - 次に `.env`（既存の OS 環境変数は上書きされない）
     - 次に `.env.local`（`.env.local` は上書きする）
     - 自動読み込みを抑止する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

   - 代表的な環境変数（README 用サンプル）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルトあり）
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb  # デフォルト
     - SQLITE_PATH=data/monitoring.db  # デフォルト
     - KABUSYS_ENV=development | paper_trading | live
     - LOG_LEVEL=INFO | DEBUG | WARNING | ERROR | CRITICAL

## 使い方（主要 API）
以下は本パッケージの代表的な使い方例です。

1. 設定へのアクセス
   - Python から settings を使う:
     - from kabusys.config import settings
     - token = settings.jquants_refresh_token
     - db_path = settings.duckdb_path
     - if settings.is_live: ...

   - 設定はプロパティとして提供され、必須項目未設定時はエラーになります。

2. DuckDB スキーマの初期化
   - 例: ファイル DB を初期化する
     - from kabusys.data.schema import init_schema
     - from kabusys.config import settings
     - conn = init_schema(settings.duckdb_path)

   - in-memory DB を使う場合:
     - conn = init_schema(":memory:")

   - 既にスキーマが存在する場合は安全にスキップされます（冪等）。

3. 既存 DB への接続（スキーマ初期化は行わない）
   - from kabusys.data.schema import get_connection
   - conn = get_connection("data/kabusys.duckdb")

4. .env のパース仕様（注意点）
   - 行頭の `#` はコメントとして無視
   - export FOO=bar 形式に対応
   - シングル/ダブルクォートで囲まれた値は内部のバックスラッシュエスケープを処理
   - クォートなしの場合、`#` が直前に空白またはタブがある場合はその `#`以降をコメントとして扱う

## ディレクトリ構成
（リポジトリ内の主要ファイル/ディレクトリを示します）

- src/
  - kabusys/
    - __init__.py                 # パッケージ初期化（__version__ 等）
    - config.py                   # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py                 # DuckDB スキーマ定義・初期化（init_schema, get_connection）
    - strategy/
      - __init__.py               # 戦略モジュール用エントリ（未実装の雛形）
    - execution/
      - __init__.py               # 発注/実行モジュール用エントリ（未実装の雛形）
    - monitoring/
      - __init__.py               # 監視・モニタリング用エントリ（未実装の雛形）

## データモデル（概要）
DuckDB のスキーマは次の層で構成されています。

- Raw Layer
  - raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer
  - features, ai_scores
- Execution Layer
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

各テーブルは主キーや CHECK 制約、必要に応じて外部キーやインデックスを持っています。詳細は `src/kabusys/data/schema.py` の DDL コメントを参照してください。

## 注意事項 / ヒント
- settings のプロパティは必須値が未設定の場合 ValueError を投げます。運用時には必ず必要な環境変数を設定してください。
- `.env` 自動読み込みはプロジェクトルート（.git または pyproject.toml）が存在する場合にのみ行われます。パッケージ配布後やテスト時に異なる挙動が必要な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- DuckDB ファイルの保存先ディレクトリが存在しない場合、`init_schema` が自動で親ディレクトリを作成します。
- 本リポジトリはコア機能（設定・スキーマ）を提供します。実際のトレーディングロジック、発注ドライバ、監視ロジックは strategy / execution / monitoring 以下に実装してください。

---

ご質問や追加してほしいセクション（例: CI、テスト手順、デプロイ例など）があれば教えてください。README に追記します。