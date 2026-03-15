# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従い、セマンティックバージョニングを使用します。

## [Unreleased]

### 追加
- 開発中のトピックや次回リリースに含める予定の変更をここに記載します。

---

## [0.1.0] - 2026-03-15

初回リリース。

### 追加
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョン番号を `__version__ = "0.1.0"` として定義し、公開モジュールとして `data`, `strategy`, `execution`, `monitoring` をエクスポート。
  - 空のサブパッケージ用初期化ファイルを追加（src/kabusys/data/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/monitoring/__init__.py）。

- 環境設定管理
  - 環境変数/設定を扱う `Settings` クラスを追加（src/kabusys/config.py）。
    - 必須環境変数チェックを行うヘルパー `_require()` を提供。未設定時に明示的な `ValueError` を送出。
    - J-Quants や kabuステーション API、Slack、データベースパスなどの設定プロパティを定義（例: `jquants_refresh_token`, `kabu_api_password`, `slack_bot_token`, `duckdb_path`, `sqlite_path` 等）。
    - 実行環境判定プロパティ（`is_live`, `is_paper`, `is_dev`）と `env`/`log_level` に対する妥当性チェック（許容値の制約）を実装。
  - .env ファイルの自動読み込み機能を実装
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に `_find_project_root()` で探索し、見つからない場合は自動ロードをスキップ。
    - 読み込み順序は OS 環境 > .env.local > .env（`.env.local` は上書き許可）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途など）。
  - .env パーサーを実装（`_parse_env_line`）
    - `export KEY=val` 形式の対応、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い（クォートあり/なしでの挙動差）など、Shell風の挙動を考慮した堅牢なパース。
  - .env 読み込み時の上書き制御
    - `_load_env_file(path, override=False, protected=frozenset(...))` により、OS環境変数を保護しつつ上書き/非上書きの振る舞いを制御。

- DuckDB スキーマと初期化ユーティリティ
  - DuckDB 用のスキーマ定義モジュールを追加（src/kabusys/data/schema.py）。
    - データレイヤーを明確に分離:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに対して適切な型・NOT NULL 制約・CHECK 制約（例: price >= 0、size > 0、side/status/order_type の列挙チェック）やプライマリキー、外部キー参照を定義。
    - 頻出クエリを想定したインデックスを複数定義（銘柄×日付スキャン、ステータス検索、orders(signal_id) 等）。
  - スキーマ初期化関数を提供
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 指定した DuckDB ファイルに対して全 DDL とインデックスを作成（冪等）。`":memory:"` をサポート。
      - ファイル指定時は親ディレクトリを自動作成。
      - 初回のみスキーマを作成したい場合に使用。
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 既存 DB への接続を返す。スキーマ初期化は行わない（初回は `init_schema()` を推奨）。

### 修正
- （初回リリースのため該当なし）

### 破壊的変更
- （初回リリースのため該当なし）

### セキュリティ
- .env 読み込み時に OS 環境変数を保護する仕組みを導入し、誤って上書きされないよう配慮。

---

メンテナンスや新機能は上記形式で今後のリリースノートに追記します。