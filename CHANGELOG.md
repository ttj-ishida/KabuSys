CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  
リリースは SemVer に従います。

[unreleased]: https://example.com/compare/v0.1.0...HEAD

## [0.1.0] - 2026-03-15

### 追加
- 初回公開: KabuSys パッケージを追加。
  - パッケージバージョンを src/kabusys/__init__.py の __version__ = "0.1.0" で定義。
  - パッケージ公開 API として data, strategy, execution, monitoring を __all__ に登録。

- 環境設定管理モジュールを追加 (src/kabusys/config.py)。
  - .env ファイルおよびOS環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルート検出は __file__ を起点に親ディレクトリを走査し、.git または pyproject.toml を基準に判定（配布後も CWD に依存しない動作）。
  - .env パーサ実装:
    - 空行・コメント行（先頭 #）を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートで囲まれた値をバックスラッシュエスケープを考慮して正しくパース（内部の # はコメント扱いにならない）。
    - クォートなし値では、直前がスペースまたはタブの # をコメントと判定して切り落とす処理を実装。
  - .env 読み込みの上書き挙動:
    - override=False: 未設定のキーのみ設定。
    - override=True: protected（起動時の OS 環境変数キー集合で保護）に含まれないキーは上書き。
  - 必須キー取得用の _require() を提供し、未設定時は ValueError を送出。

  - Settings クラスを公開 (settings インスタンス):
    - J-Quants / kabuステーション / Slack / データベース設定等のプロパティを提供:
      - jquants_refresh_token (JQUANTS_REFRESH_TOKEN 必須)
      - kabu_api_password (KABU_API_PASSWORD 必須)
      - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
      - slack_bot_token (SLACK_BOT_TOKEN 必須)
      - slack_channel_id (SLACK_CHANNEL_ID 必須)
      - duckdb_path (デフォルト: data/kabusys.duckdb)
      - sqlite_path (デフォルト: data/monitoring.db)
    - システム設定:
      - env: KABUSYS_ENV を読み取り、"development", "paper_trading", "live" のいずれかでなければ ValueError を投げる。デフォルトは "development"。
      - log_level: LOG_LEVEL を読み取り、"DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれかでなければ ValueError を投げる。デフォルトは "INFO"。
      - is_live / is_paper / is_dev の判定プロパティを提供。

- DuckDB スキーマ管理モジュールを追加 (src/kabusys/data/schema.py)。
  - 「Raw / Processed / Feature / Execution」の 4 層に分かれたテーブル定義を実装。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - テーブル定義は各カラムの型・チェック制約（CHECK）、主キー（PRIMARY KEY）、外部キー（FOREIGN KEY）を含むDDLで定義。
  - 検索に備えたインデックスを複数定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - テーブル作成順を外部キー依存に基づき管理。
  - 公開 API:
    - init_schema(db_path): 指定された DuckDB ファイルを初期化し、全テーブルとインデックスを作成して DuckDB 接続を返す。
      - ":memory:" を指定するとインメモリ DB を使用。
      - ファイルパス指定時は親ディレクトリを自動作成（存在しない場合）。
      - DDL は冪等（既存テーブルはスキップ）。
    - get_connection(db_path): 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を推奨）。

- 空のサブパッケージ初期化ファイルを追加:
  - src/kabusys/data/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/monitoring/__init__.py

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### セキュリティ
- （該当なし）

注記
- schema モジュールのテーブル設計や DataSchema.md を参照する想定の設計意図がコードコメントに残されています。
- 環境変数の自動読み込みは実行環境に依存するため、ユニットテストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを避けることを推奨します。