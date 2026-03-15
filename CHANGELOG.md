Keep a Changelogの形式に準拠した CHANGELOG.md を以下に作成しました。コード内容から推測して記載しています。

CHANGELOG.md
=============

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に従い、セマンティックバージョニングを使用します。

Unreleased
----------

（現時点では未リリースの変更はありません）

0.1.0 - 2026-03-15
-----------------

Added
- 初回リリースとしてパッケージの基本構成を追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py にて定義）

- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートの検出は __file__ を起点に親ディレクトリを探索し、.git または pyproject.toml を基準に判定（CWD に依存しない挙動）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト時等に利用可能）。
    - .env 読み込みに失敗した場合は警告を出力して処理を継続。
  - .env パーサを実装:
    - 空行・コメント（# 単独行）を無視。
    - export KEY=val 形式に対応。
    - シングル／ダブルクォートで囲まれた値のエスケープ（バックスラッシュ）に対応し、対応する閉じクォートまでを値として取り込む実装。
    - クォートなしの場合のインラインコメント扱いは '#' の直前がスペースまたはタブの場合にのみコメントと認識する繊細な挙動。
  - 環境変数の上書き挙動:
    - _load_env_file() に override と protected 引数を用意。OS由来の既存環境変数を protected として保護し、.env.local による明示的上書きをサポート。
  - Settings クラスを提供（settings = Settings() でインスタンスを公開）。
    - J-Quants / kabuステーション / Slack / データベース（DuckDB・SQLite）などの設定プロパティを定義。
    - 必須設定は _require() により未設定時は ValueError を送出する安全設計。
    - KABUSYS_ENV（development / paper_trading / live）の検証と簡易判定プロパティ（is_live, is_paper, is_dev）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - デフォルトの DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"（ホーム展開対応）。

- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）。
  - Data Lake の 3 層＋実行レイヤーを想定したテーブル定義を提供。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な型、CHECK 制約、主キー／外部キー制約を設定。
  - よく使われるクエリを想定したインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - テーブル作成順は外部キー依存を考慮して管理。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定したパスに対して冪等的にテーブル・インデックスを作成。
      - db_path の親ディレクトリを自動作成（":memory:" はインメモリ DB として対応）。
      - 初期化済みの DuckDB 接続を返す。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続取得（スキーマ初期化は行わない。初回は init_schema を推奨）。

- パッケージ構成の雛形を追加（空のサブパッケージ __init__.py を配置）。
  - src/kabusys/data/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/monitoring/__init__.py

Changed
- （該当なし：初回リリース）

Fixed
- （該当なし：初回リリース）

Security
- 環境変数の自動上書きを防ぐため、OS 環境変数を protected として扱う実装を導入（.env/.env.local 読み込み時の安全性向上）。

Notes / 実装上の補足
- .env パーサは Bash と完全互換を目指したものではなく、一般的なケース（export プレフィックス、クォート、エスケープ、簡易インラインコメント）に対応しています。特殊なケースでは期待どおりに動作しない可能性があります。
- Settings の必須項目（例えば JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）は環境変数が未設定の場合に起動時に例外を投げます。開発時は .env.example を参考に .env を用意してください。
- DuckDB スキーマは初期段階の設計に基づいたものです。将来的に列追加や制約の変更が発生する可能性があります（マイグレーション戦略の導入を推奨）。

Authors
- 初回実装（推測に基づく CHANGELOG 記載）

以上。必要であれば、リリースノート項目の文言や日付を調整したり、各テーブル／設定項目の説明をさらに詳細化します。