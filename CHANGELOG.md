# Keep a Changelog
すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムの基礎構成、設定管理、および DuckDB ベースのデータスキーマを導入しました。

### 追加 (Added)
- パッケージ基礎
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py の __version__）
  - モジュールの公開: data, strategy, execution, monitoring をパッケージ公開対象と設定。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを追加。
  - 自動読み込み:
    - プロジェクトルート判定（.git または pyproject.toml を探索）に基づき .env/.env.local を自動読み込み。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env → .env.local の順で読み込み、.env.local は上書きモード（override=True）で読み込む仕組みを採用。ただし OS 環境変数は保護（protected）して上書きしない。
  - .env パーサーの強化:
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォートで囲まれた値のエスケープ（バックスラッシュ）に対応し、対応する閉じクォートまでを正しく抽出。
    - クォートなしの値では、直前がスペース/タブである '#' をコメントの開始とみなす（それ以外の '#' は値の一部として扱う）。
    - 無効行やコメント行を無視。
  - .env ファイル読み込みに失敗した場合は警告を発する（warnings.warn）。
  - 設定プロパティ（Settings）:
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション API: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
    - データベースパス: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - システム設定: KABUSYS_ENV（デフォルト: development、許容値: development, paper_trading, live）、LOG_LEVEL（デフォルト: INFO、許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - 便宜的プロパティ: is_live, is_paper, is_dev（環境判定）
  - 必須環境変数未設定時は ValueError を送出する _require() を実装。

- DuckDB スキーマ / データレイヤー (src/kabusys/data/schema.py)
  - 3層（+実行層）構造のスキーマ定義を追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して型制約、CHECK 制約、PRIMARY KEY、必要箇所に FOREIGN KEY を設定（例: news_symbols.news_id → news_articles.id, orders.signal_id → signal_queue.signal_id, trades.order_id → orders.order_id）。
  - インデックス定義を追加（頻出クエリパターンを考慮）：prices_daily(code, date)、features(code, date)、ai_scores(code, date)、signal_queue(status)、orders(status) など。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定 DB を初期化し全テーブル・インデックスを作成。既存テーブルはスキップ（冪等）。
      - db_path の親ディレクトリが存在しない場合は自動作成。
      - ":memory:" を指定してインメモリ DB を利用可能。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わないため初回は init_schema を推奨）。

- パッケージ構成
  - 空の __init__.py を配置して各サブパッケージ (data, strategy, execution, monitoring) を用意（拡張用のプレースホルダ）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注記:
- settings のプロパティは環境変数に依存しており、必須変数がない場合は明示的なエラーが発生します。テスト環境や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して自動読み込みを無効にできます。
- DuckDB スキーマは複数の制約（CHECK, PRIMARY KEY, FOREIGN KEY）やインデックスを含み、分析・実行処理の共存を意図しています。初回起動時は init_schema を呼び出してください。