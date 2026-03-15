# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般的な方針と語彙:
- 追加 (Added): 新機能
- 変更 (Changed): 既存の振る舞いの変更
- 修正 (Fixed): バグ修正
- 削除 (Removed): 削除された機能

## [0.1.0] - 2026-03-15

初期リリース。日本株自動売買システム "KabuSys" の基本パッケージ構成と主要コンポーネントを追加。

### 追加 (Added)
- パッケージ初期化
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ による公開モジュール: data, strategy, execution, monitoring

- 環境変数・設定管理モジュール (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を追加
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルート判定は .git または pyproject.toml を起点に行い、CWD に依存しない実装
  - .env パーサーの実装（_parse_env_line）
    - コメント行や空行を無視
    - "export KEY=val" 形式に対応
    - シングル/ダブルクォートされた値のエスケープ処理に対応
    - クォートなしの場合のインラインコメント取り扱い（直前が空白/タブの場合のみコメント扱い）
  - .env 読み込み関数（_load_env_file）
    - override フラグ、protected（上書き禁止のキー集合）をサポート
    - ファイル読み込み失敗時は警告を出力してスキップ
  - Settings クラスを公開（settings インスタンス）
    - 必須キー取得のための _require 実装（未設定時は ValueError を送出）
    - 提供プロパティ:
      - jquants_refresh_token (JQUANTS_REFRESH_TOKEN: 必須)
      - kabu_api_password (KABU_API_PASSWORD: 必須)
      - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
      - slack_bot_token (SLACK_BOT_TOKEN: 必須)
      - slack_channel_id (SLACK_CHANNEL_ID: 必須)
      - duckdb_path (DUCKDB_PATH, デフォルト: data/kabusys.duckdb)
      - sqlite_path (SQLITE_PATH, デフォルト: data/monitoring.db)
      - env (KABUSYS_ENV, デフォルト: development) — 有効値: development, paper_trading, live（不正値で ValueError）
      - log_level (LOG_LEVEL, デフォルト: INFO) — 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL（不正値で ValueError）
      - is_live / is_paper / is_dev のヘルパープロパティ

- DuckDB スキーマ定義と初期化モジュール (src/kabusys/data/schema.py)
  - 3〜4 層にわたるテーブル群を定義（Raw / Processed / Feature / Execution）
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対する制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を付与
  - 頻出クエリのためのインデックスを複数定義
    - 例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status など
  - DB 初期化 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定パスの親ディレクトリを自動作成（:memory: は除く）
      - 全テーブルとインデックスを作成（冪等）
      - DuckDB 接続を返す
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない）
  - duckdb を依存として使用

- パッケージ内プレースホルダモジュールを追加
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/data/__init__.py
  - src/kabusys/monitoring/__init__.py
  - （今後これらに機能を実装するためのスケルトン）

### 変更 (Changed)
- 初期リリースのため該当なし

### 修正 (Fixed)
- 初期リリースのため該当なし

### 削除 (Removed)
- 初期リリースのため該当なし

---

注記:
- 必須環境変数（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。未設定時は Settings のプロパティアクセスで ValueError が発生します。
- .env のパース挙動はシェルの一般的なルールに近いが、完全に互換とは限りません（本実装のコメント・クォート処理ルールに従います）。
- データベースの初期化は冪等であるため、既存テーブルが存在しても安全に呼び出せます。