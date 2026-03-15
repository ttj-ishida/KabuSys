Keep a Changelog 準拠の CHANGELOG.md（日本語）
※コードベース（初回リリース）の内容から推測して作成しています。

All notable changes to this project will be documented in this file.

The format is based on "Keep a Changelog" and this project adheres to Semantic Versioning.

## [Unreleased]


## [0.1.0] - 2026-03-15
初回リリース。内部モジュールや DB スキーマ、環境設定機構を実装。

### Added
- パッケージ基盤
  - パッケージ初期化と公開 API を追加（src/kabusys/__init__.py）。
    - __version__ = 0.1.0
    - __all__ = ["data", "strategy", "execution", "monitoring"]
- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロードの優先度: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト用途など）。
  - プロジェクトルート探索: .git または pyproject.toml を起点に探索する _find_project_root() を実装し、CWD に依存しない自動ロードを実現。
  - .env パーサを実装（_parse_env_line）
    - コメント行、空行を無視
    - "export KEY=val" 形式に対応
    - シングル/ダブルクォート付き値の取り扱い（バックスラッシュによるエスケープ対応）
    - クォートなし値におけるインラインコメント判定（直前がスペース／タブの場合に '#' をコメントとして扱う）
  - .env の読み込みロジックを実装（_load_env_file）
    - override フラグで既存環境変数の上書きを制御
    - protected 引数で上書き禁止のキーを指定（OS 環境変数保護）
  - Settings クラスを追加し、アプリケーションで利用する設定値をプロパティとして提供
    - 必須設定の取得時に未設定であれば ValueError を送出する _require() を実装
    - 実装済みの設定（例）:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（有効値: development, paper_trading, live。デフォルト: development）
      - LOG_LEVEL（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO）
    - Settings に環境判定ユーティリティを追加（is_live, is_paper, is_dev）
- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の 4 層を想定したテーブル群を定義
    - Raw Layer:
      - raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer:
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer:
      - features, ai_scores
    - Execution Layer:
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 主な制約と型を定義（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY など）
  - 利用頻度を想定したインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status など）
  - init_schema(db_path) を実装
    - 指定した DuckDB ファイルに対してテーブルとインデックスを作成（冪等）
    - db_path が ":memory:" であればインメモリ DB を使用
    - DB ファイルの親ディレクトリが存在しない場合は自動作成
    - 初回のスキーマ構築に使用することを想定
  - get_connection(db_path) を実装（既存 DB への接続。スキーマ初期化は行わない）
- 空のサブパッケージプレースホルダ
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/data/__init__.py
  - src/kabusys/monitoring/__init__.py
  - （将来の拡張用にモジュール構成を準備）

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Migration
- 初回利用時は必ず init_schema() を呼んで DuckDB スキーマを初期化してください（例: kabusys.data.schema.init_schema(settings.duckdb_path)）。
- 必須環境変数が未設定の場合、Settings の該当プロパティ呼び出しで ValueError が発生します。デプロイ前に .env を作成するか OS 環境変数を設定してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。配布後に CWD が異なっても想定どおり動作するよう設計されています。

---

参考（このリリースで期待される主要環境変数）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト data/monitoring.db)
- KABUSYS_ENV (任意, 有効値: development, paper_trading, live)
- LOG_LEVEL (任意, 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意, 値を設定すると .env 自動読み込みを抑止)

（以上）