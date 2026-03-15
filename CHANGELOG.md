# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このプロジェクトはセマンティックバージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムのコア基盤を実装。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名、バージョン (`__version__ = "0.1.0"`) および公開モジュールリスト (`__all__ = ["data", "strategy", "execution", "monitoring"]`) を定義。

- 環境変数・設定管理モジュール
  - src/kabusys/config.py を追加。
  - .env ファイルまたは OS 環境変数から設定値を自動読み込みする機能を提供。
    - プロジェクトルートの自動検出: 現在ファイルの親階層から `.git` または `pyproject.toml` を探索してプロジェクトルートを特定。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
    - .env ファイルの読み込みは安全に行い、読み込み失敗時は警告を発行。
  - .env パーサを実装（_parse_env_line）。
    - コメント行（#）や空行を無視。
    - export プレフィックス（`export KEY=val`）に対応。
    - クォート付き値（シングル/ダブル）とバックスラッシュエスケープに対応し、インラインコメントを正しく扱う。
    - クォート無しの値については '#' の前にスペース/タブがあればコメントとして扱う。
  - 上書き振る舞い制御:
    - _load_env_file で override フラグと protected キー集合を利用し、OS 環境変数（protected）を上書きしないよう保護。
    - .env と .env.local の読み込み時に .env.local が上書きされる挙動を採用。
  - Settings クラスを提供（settings インスタンスを公開）。
    - J-Quants、kabuステーション API、Slack、データベースパス、システム設定等のプロパティを定義。
    - 必須値未設定時は _require() により ValueError を送出。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の値検証（許容値はそれぞれ {"development","paper_trading","live"} と {"DEBUG","INFO","WARNING","ERROR","CRITICAL"}）。
    - duckdb と sqlite のデフォルトパス（"data/kabusys.duckdb" / "data/monitoring.db"）をサポート（Path.expanduser を利用）。

- DuckDB スキーマ定義・初期化
  - src/kabusys/data/schema.py を追加。
  - DataLayer を意識したテーブル定義（Raw / Processed / Feature / Execution）を実装。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な型、PRIMARY KEY、CHECK 制約、外部キー制約（news_symbols→news_articles, orders→signal_queue, trades→orders）を定義。
  - 頻出クエリ向けのインデックスを作成（例: idx_prices_daily_code_date, idx_features_code_date, idx_signal_queue_status 等）。
  - テーブル作成順を依存関係（外部キー）を考慮して定義。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定した DuckDB ファイルを初期化し、全テーブルとインデックスを作成。
      - 冪等であり、既存テーブルはスキップ。
      - db_path の親ディレクトリが存在しない場合は自動作成。
      - ":memory:" をサポート。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を使用すること）。

- サブパッケージの雛形
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を追加（各機能の実装を今後追加予定）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の自動ロード時に OS 環境変数を保護する仕組みを導入（protected セットを利用し、意図せず重要な環境変数を上書きしない）。

Notes
- 初回リリースであり、上記は基盤実装です。戦略ロジック、注文送信処理、監視機能等はサブパッケージの中で今後追加・拡張されます。
- .env パース挙動や Settings の必須キー、DuckDB スキーマ等は仕様に応じて後続のリリースで変更される可能性があります。必要に応じてマイグレーション手順を提供予定です。