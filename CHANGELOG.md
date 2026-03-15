# Changelog

すべての重大な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従います。セマンティックバージョニングを採用しています。

## [Unreleased]

### Added
- （なし）

---

## [0.1.0] - 2026-03-15

### Added
- パッケージの初期リリース。モジュール構成を追加。
  - kabusys パッケージ初期化: バージョン情報と主要サブモジュール（data, strategy, execution, monitoring）を公開（src/kabusys/__init__.py）。
  - 空のパッケージ初期化ファイルを配置（src/kabusys/data/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/monitoring/__init__.py）。

- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出: 現在ファイル位置を起点に親ディレクトリを探索し、.git または pyproject.toml を基準にルートを特定。これにより CWD に依存しない自動ロードが可能。
    - 読み込み順序: OS 環境変数 > .env.local > .env。 .env.local は .env の上書き用。
    - 自動ロードの無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを停止可能（テスト用途を想定）。
    - OS の既存環境変数は保護（protected）され、デフォルトでは上書きされない。
  - .env パーサを実装:
    - 空行・コメント行（# で始まる）を無視。
    - "export KEY=val" 形式に対応。
    - シングル/ダブルクォートされた値を考慮し、バックスラッシュによるエスケープを処理して対応する閉じクォートまでを値として取り込む（以降の inline コメントは無視）。
    - クォートされていない値では、'#' の前がスペースまたはタブのときのみコメントとして扱う（一般的な .env の挙動に近づける）。
  - Settings クラスを提供（settings インスタンスを公開）。
    - J-Quants, kabuステーション, Slack, データベースパスなどのプロパティを取得する便利なアクセサを提供。
    - 必須設定が未設定の場合は ValueError を送出する _require() を実装（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - デフォルト値: KABUS_API_BASE_URL, DUCKDB_PATH（data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）をサポート。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の値検証:
      - KABUSYS_ENV の有効値: development, paper_trading, live
      - LOG_LEVEL の有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
    - is_live / is_paper / is_dev のヘルパープロパティを追加。

- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）。
  - データレイヤを想定した 3 層＋実行レイヤのテーブル群を定義（Raw / Processed / Feature / Execution）。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions（取得した生データ格納）。
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols（整形済み市場データ）。
    - Feature Layer: features, ai_scores（戦略／AI 用特徴量）。
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance（シグナル・発注・約定・ポジション管理）。
  - 各テーブルに対して適切なカラム型、チェック制約、主キー、外部キー（必要箇所）を定義。
  - 代表的なクエリパターンを考慮したインデックスを作成（銘柄×日付スキャンやステータス検索向け）。
  - テーブル作成順は外部キー依存を考慮した順序で実行。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定したパスで DuckDB を初期化し、全テーブルとインデックスを作成して接続を返す（冪等）。
      - db_path の親ディレクトリが存在しない場合は自動作成。
      - ":memory:" を指定してインメモリ DB を使用可能。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を利用）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

## 追加情報 / マイグレーション / 使用上の注意

- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  これらが未設定の場合、settings の該当プロパティアクセス時に ValueError が発生します。

- .env の自動ロードについて:
  - プロジェクトルートが検出できない場合は自動ロードがスキップされます（パッケージ配布後の挙動を安定化）。
  - OS 環境変数は保護され、デフォルトでは .env/.env.local によって上書きされません。明示的に上書きしたい場合は環境側で制御する必要があります。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストでの制御に便利です）。

- DuckDB スキーマ初期化例:
  - from kabusys.config import settings
    from kabusys.data.schema import init_schema
    conn = init_schema(settings.duckdb_path)
  - 初回実行時に data/ ディレクトリ（デフォルト）が自動作成されます。

- ログレベル・実行環境の検証:
  - KABUSYS_ENV は development / paper_trading / live のいずれかを指定してください。設定ミスは ValueError を発生させます。
  - LOG_LEVEL は標準的なログレベル名（DEBUG 等）を使用してください。

--- 

（この CHANGELOG は、リポジトリ内の現行コードからの推測に基づいて作成しています。実際のリリースノートとして公開する場合は、リリースプロセスに合わせて必要な情報を追記してください。）