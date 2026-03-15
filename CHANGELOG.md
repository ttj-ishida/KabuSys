# Changelog

すべての重要な変更を記録します。  
このファイルは Keep a Changelog の慣例に従って記載されています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース

### Added
- パッケージ初期構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - モジュール公開: data, strategy, execution, monitoring を __all__ として公開

- 環境設定・ロード機能を追加 (src/kabusys/config.py)
  - プロジェクトルートの自動検出:
    - .git または pyproject.toml を基準にプロジェクトルートを特定する機能を追加（__file__ 基準の探索で配布後も安定）。
  - .env ファイルパーサー実装:
    - 空行・コメント行の無視、`export KEY=val` 形式対応。
    - シングル/ダブルクォート付き値のバックスラッシュエスケープ処理に対応。
    - クォートなし値に対するインラインコメントの取り扱い（直前がスペース/タブの場合のみコメントと判定）。
  - .env ファイルのロードロジック:
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 読み込み時に既存 OS 環境変数を保護する protected セットを導入し、.env.local で上書き可能だが OS 環境変数は保護される。
    - ファイル読み込み失敗時に警告を出すように実装。
    - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途など）。
  - 必須環境変数取得ヘルパー:
    - _require() により未設定時は ValueError を送出。例示として JQUANTS_REFRESH_TOKEN 等を必須として使用。
  - Settings クラスを追加（settings インスタンスをエクスポート）:
    - J-Quants、kabuステーション、Slack、DB パスなど各種設定をプロパティで提供。
    - デフォルト値: KABUSYS_API_BASE_URL のデフォルト、DuckDB/SQLite のデフォルトパス (data/ 下) を提供。
    - KABUSYS_ENV の値検証: 有効値は development, paper_trading, live。
    - LOG_LEVEL の値検証: 有効値は DEBUG, INFO, WARNING, ERROR, CRITICAL。
    - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- DuckDB スキーマ・初期化モジュールを追加 (src/kabusys/data/schema.py)
  - 3 層構造（Raw / Processed / Feature / Execution）に基づくテーブル定義を追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型制約と CHECK 制約、PRIMARY/FOREIGN KEY を定義。
  - 頻出クエリを想定したインデックス群を作成（例: code/date 検索、status 検索など）。
  - テーブル作成順を外部キー依存に配慮して定義。
  - init_schema(db_path) を提供:
    - 指定した DuckDB ファイルを初期化し、全テーブルとインデックスを作成（冪等）。
    - db_path の親ディレクトリが無ければ自動作成。
    - ":memory:" を指定してインメモリ DB を利用可能。
    - 初期化後に DuckDB 接続オブジェクトを返す。
  - get_connection(db_path) を提供:
    - 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を推奨）。

- パッケージの空モジュールを用意
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を追加し、将来の拡張に備えた骨組みを提供。

### Changed
- N/A

### Fixed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Security
- N/A

補足:
- DataSchema.md に基づくテーブル設計を想定しており、コメントやドキュメンテーション文字列で設計意図を明記しています。
- 実運用においては .env ファイルや必須環境変数の管理に注意してください（特に API トークンやパスワード類）。