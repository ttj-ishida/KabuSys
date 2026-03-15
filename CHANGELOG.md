# Keep a Changelog
すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。  

## [Unreleased]
- なし

## [0.1.0] - 2026-03-15
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ情報: `kabusys` (バージョン 0.1.0) を追加。パッケージトップでサブパッケージの公開を設定（__all__ = ["data", "strategy", "execution", "monitoring"]）。
  - サブパッケージ用の空の初期化ファイルを追加: `kabusys.execution`, `kabusys.strategy`, `kabusys.data`, `kabusys.monitoring`（将来的な拡張のためのプレースホルダ）。

- 環境変数 / 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルート検出: `pyproject.toml` または `.git` を基準にルートを特定（CWDに依存しない）。
    - 自動ロード無効化オプション: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動読み込みを無効化可能。
  - .env パーサーを実装（`_parse_env_line`）
    - 空行・コメント行の無視、`export KEY=val` 形式の対応。
    - シングル/ダブルクォートに対応、バックスラッシュエスケープ処理を考慮。
    - クォートなし値におけるインラインコメント判定（`#` の直前がスペースまたはタブの場合のみコメント扱い）。
  - .env 読み込みロジック（`_load_env_file`）
    - ファイルが存在しない場合は無視。
    - ファイル読み込み失敗時は警告を発行。
    - override と protected キー（OS環境変数の保護）をサポート。
  - 設定アクセス用インターフェイス `Settings` を導入（`settings` インスタンスを提供）
    - J-Quants / kabuステーション / Slack / DB パスなど各種必須・既定値の設定プロパティを提供:
      - JQUANTS_REFRESH_TOKEN (必須)
      - KABU_API_PASSWORD (必須)
      - KABU_API_BASE_URL (デフォルト: "http://localhost:18080/kabusapi")
      - SLACK_BOT_TOKEN (必須)
      - SLACK_CHANNEL_ID (必須)
      - DUCKDB_PATH (デフォルト: "data/kabusys.duckdb")
      - SQLITE_PATH (デフォルト: "data/monitoring.db")
      - KABUSYS_ENV（"development" / "paper_trading" / "live" のバリデーション）
      - LOG_LEVEL（"DEBUG","INFO","WARNING","ERROR","CRITICAL" のバリデーション）
    - 環境（is_live / is_paper / is_dev）を判定するユーティリティプロパティを追加。
    - 必須環境変数未設定時は明確なエラーメッセージで ValueError を送出。

- データ層スキーマ (`kabusys.data.schema`)
  - DuckDB ベースのスキーマ定義と初期化機能を追加。
  - データレイヤーの設計（文書化）:
    - Raw Layer: 取得した生データ（raw_prices, raw_financials, raw_news, raw_executions）
    - Processed Layer: 整形済み市場データ（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）
    - Feature Layer: 戦略・AI用特徴量（features, ai_scores）
    - Execution Layer: 発注・約定・ポジション管理（signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）
  - 各テーブルに対して堅牢な型・チェック制約・主キー・外部キーを定義（例: price/size の非負チェック、side/status/order_type の ENUM チェックなど）。
  - 頻出クエリ向けのインデックスを定義（例: prices_daily(code, date), features(code, date), signal_queue(status) 等）。
  - スキーマ初期化関数 `init_schema(db_path)` を追加:
    - テーブルとインデックスをすべて作成（冪等）。
    - db_path の親ディレクトリが存在しない場合は自動作成。
    - ":memory:" をサポート（インメモリ DB）。
    - 初期化済みの duckdb 接続オブジェクトを返却。
  - 既存 DB へ接続するための `get_connection(db_path)` を追加（スキーマ初期化は行わないことを明記）。

### 変更 (Changed)
- 初回公開のため、特になし。

### 修正 (Fixed)
- 初回公開のため、特になし。

### セキュリティ (Security)
- 初回公開のため、特になし。

-----

注:
- この CHANGELOG は、提供されたコードベースから推測できる変更点・初期機能をもとに作成しています。実際のリリースノートに合わせて日付・詳細を調整してください。