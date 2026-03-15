# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の規約に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現在未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-15

初回リリース。日本株の自動売買システム基盤となる以下の機能を追加しました。

### 追加 (Added)
- パッケージ初期化情報
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - パッケージの公開モジュールとして data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを追加。
  - 必須環境変数取得用のヘルパー _require() を提供し、未設定時は ValueError を送出。
  - サポートされる設定項目（プロパティ）を実装:
    - J-Quants: jquants_refresh_token (必須)
    - kabuステーション: kabu_api_password (必須)、kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - Slack: slack_bot_token (必須)、slack_channel_id (必須)
    - データベースパス: duckdb_path（デフォルト: data/kabusys.duckdb）、sqlite_path（デフォルト: data/monitoring.db）
    - 実行環境: env (development, paper_trading, live)、log_level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
    - 環境チェック: is_live, is_paper, is_dev のヘルパープロパティ
  - 環境変数自動ロード機能:
    - プロジェクトルート（.git または pyproject.toml）を起点に .env と .env.local を自動読み込み。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - OS の既存環境変数は保護され、.env/.env.local により上書きされない（ただし .env.local は override=True）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途等）。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなしの場合はインラインコメントの判定（直前が空白またはタブの '#' をコメントとみなす）を実装。
    - 無効行やコメント行を無視。

- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - データレイク / データ層のスキーマを定義（Raw / Processed / Feature / Execution の4層構成）。
  - 各種テーブルの DDL を実装（主なテーブル）:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェックを各カラムに追加（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY 等）。
  - 利便性のためのインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - 依存関係を考慮したテーブル作成順を管理。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb connection
      - データベースファイルの親ディレクトリを自動作成し、必要な全テーブルとインデックスを作成（冪等）。
      - ":memory:" によるインメモリ DB をサポート。
    - get_connection(db_path: str | Path) -> duckdb connection
      - 既存 DB へ接続（スキーマ初期化は行わない。初回は init_schema を推奨）。

### 変更 (Changed)
- なし（初回リリースのため過去からの変更はないことを明記）

### 修正 (Fixed)
- なし（初回リリース）

### 注意事項 / マイグレーション
- 初回起動時は必ず init_schema(settings.duckdb_path) を呼び出して DuckDB のスキーマを作成してください。  
  例: from kabusys.data.schema import init_schema; init_schema(settings.duckdb_path)
- .env の自動ロードはプロジェクトルートの検出に依存します。パッケージを配布・導入した環境でプロジェクトルートが検出できない場合は自動ロードはスキップされます（必要に応じて明示的に環境変数を設定してください）。
- 機密情報（API トークン等）は OS 環境変数として設定することを推奨します。.env.local は開発用の上書きに使えますが、OS 環境変数が優先されます。

---

署名:
- 初版実装: 環境設定管理、.env パーシング強化、DuckDB ベースのスキーマ/初期化機能、およびパッケージの基本構成を提供しました。