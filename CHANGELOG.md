# CHANGELOG

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-03-15
初回リリース。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にパッケージメタ情報を追加（バージョン "0.1.0"、公開モジュール指定: data, strategy, execution, monitoring）。

- 環境変数／設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは .git または pyproject.toml を基準に自動検出（ファイル位置起点の探索により CWD に依存しない）。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - OS 環境変数は保護（.env による上書きを防止）。.env.local は override=True で上書き可能（保護キーを除く）。
  - .env パーサーの実装
    - 空行、コメント（先頭#）の無視
    - export KEY=val 形式に対応
    - 単一/二重クォートを含む値のエスケープ解釈（バックスラッシュエスケープを考慮）
    - クォートなしの場合、コメント（#）は直前がスペース/タブの場合のみコメントとして扱う（値中の#を尊重）
  - Settings クラスを提供（settings = Settings()）
    - J-Quants / kabuステーション / Slack / DB / システム設定（env, log_level 等）をプロパティとして取得
    - 必須設定が未設定の場合は ValueError を送出する _require() を利用
    - デフォルト値:
      - KABUS_API_BASE_URL: "http://localhost:18080/kabusapi"
      - DUCKDB_PATH: "data/kabusys.duckdb"
      - SQLITE_PATH: "data/monitoring.db"
      - KABUSYS_ENV デフォルト: "development"
      - LOG_LEVEL デフォルト: "INFO"
    - env 値の検証（許可値: development, paper_trading, live）
    - log_level 値の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - ヘルパープロパティ: is_live, is_paper, is_dev

- DuckDB スキーマ定義／初期化モジュールを追加（src/kabusys/data/schema.py）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を実装
    - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
    - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature レイヤー: features, ai_scores
    - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（NOT NULL、CHECK、PRIMARY KEY、外部キー等）を設定
  - 頻出クエリ向けインデックス定義を追加（例: prices_daily(code, date), signal_queue(status), orders(status) など）
  - テーブル作成順を外部キー依存に合わせて定義（冪等性を確保）
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定 DB を初期化して全テーブル／インデックスを作成。親ディレクトリが無ければ自動作成。":memory:" をサポート。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB へ接続（スキーマ初期化は行わない。初回は init_schema を推奨）

- モジュールプレースホルダ（空パッケージ）を追加
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/data/__init__.py
  - src/kabusys/monitoring/__init__.py

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Removed
- なし（初回リリース）

### Security
- なし（初回リリース）

---

使用メモ / 移行ガイド
- 初回セットアップ
  - .env をプロジェクトルートに配置（.env.example を参考に必要な環境変数を設定）。
  - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）が未設定だと Settings の対応プロパティ呼び出し時に例外が発生します。
- DB 初期化例
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
- 自動 .env ロード無効化
  - テスト等で自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env の取り扱いに関する挙動
  - 値にクォートを含める場合、エスケープ (\) を使用して内部のクォート等を表現できます。
  - クォートなしの値内の # は、直前がスペース/タブでない限りコメントとみなされません（値の一部として扱われます）。

貢献者 / 著者
- 初回実装（コードベースより推測）