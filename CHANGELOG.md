CHANGELOG
=========

すべての重要な変更を記録します。これは Keep a Changelog の形式に準拠しています。
[詳細](https://keepachangelog.com/ja/1.0.0/)

Unreleased
----------

（なし）

0.1.0 - 2026-03-15
-----------------

Added
- 初回リリース。パッケージ名: `kabusys`、バージョン: `0.1.0`。
- パッケージの基本構成を追加。
  - モジュール群: `kabusys.data`、`kabusys.strategy`、`kabusys.execution`、`kabusys.monitoring`（各サブパッケージの初期化ファイルを含む）。
  - パッケージのエントリポイント: `src/kabusys/__init__.py`（`__version__` と `__all__` を定義）。

- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルおよび OS 環境変数から設定を読み込む仕組みを提供。
  - 自動読み込みの探索はパッケージファイル位置から親ディレクトリを辿り、`.git` または `pyproject.toml` をプロジェクトルートとして検出。
  - 読み込み優先順位:
    - OS 環境変数 > .env.local > .env
  - 自動ロードの無効化機能:
    - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト用途など）。
  - .env のパース機能（`_parse_env_line`）:
    - 空行／コメント行（行頭の `#`）を無視。
    - `export KEY=val` 形式に対応。
    - シングル／ダブルクォートを考慮した値のパース（バックスラッシュによるエスケープ処理をサポート）。
    - クォートなし値に対しては `#` の前に空白またはタブがある場合のみコメントとして扱うなどの挙動を実装。
  - .env 読み込み関数（`_load_env_file`）:
    - ファイルごとの上書き制御（`override`）と保護対象キー（`protected`）を考慮して OS 環境変数を上書きしないように設計。
    - 読み込み失敗時は警告を発行して継続。
  - 必須値チェック（`_require`）:
    - 必須の環境変数が未設定の場合は `ValueError` を送出して明示的に失敗させる。
  - Settings クラス（`settings` インスタンスを公開）:
    - J-Quants / kabu ステーション / Slack / DB パス / システム設定などのプロパティを提供。
    - 取得可能プロパティ例:
      - jquants_refresh_token（JQUANTS_REFRESH_TOKEN を必須取得）
      - kabu_api_password（KABU_API_PASSWORD を必須取得）
      - kabu_api_base_url（既定値: http://localhost:18080/kabusapi）
      - slack_bot_token, slack_channel_id（必須）
      - duckdb_path（既定: data/kabusys.duckdb）
      - sqlite_path（既定: data/monitoring.db）
      - env（KABUSYS_ENV の検証。許容値: development, paper_trading, live）
      - log_level（LOG_LEVEL の検証。許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
      - is_live / is_paper / is_dev（環境判定ユーティリティ）

- DuckDB 用スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）。
  - DataSchema.md に基づく 3 層＋実行レイヤのテーブル定義を実装。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェック・制約を付与:
    - 主キー（PRIMARY KEY）、外部キー（FOREIGN KEY）、CHECK 制約（価格 >= 0、サイズ > 0、ステータスや side の列挙値制約等）を含む。
    - 外部キーに対して ON DELETE CASCADE / SET NULL を利用して参照整合性を管理。
  - 頻出クエリを想定したインデックスを定義:
    - 銘柄×日付スキャン用インデックスやステータス検索用インデックス等を作成。
  - 公開 API:
    - init_schema(db_path: str | Path) -> DuckDB 接続:
      - 指定したパスで DB を初期化し、必要な親ディレクトリを自動作成。
      - ":memory:" を渡すことでインメモリ DB を使用可能。
      - 全 DDL とインデックスを冪等に作成。
    - get_connection(db_path: str | Path) -> DuckDB 接続:
      - 既存の DB へ接続。スキーマ初期化は行わない（初回は init_schema を推奨）。

- コード品質に関する実装:
  - 型ヒント（Python の型注釈）を多数採用。
  - ドキュメンテーション文字列（docstring）を各モジュール・関数に付与。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Known limitations
- サブパッケージ（strategy, execution, monitoring）は初期化ファイルのみであり、各機能の実装はこれから追加予定。
- 環境変数の自動読み込みはプロジェクトルートの検出に依存する（.git または pyproject.toml）。配布後の環境では意図した動作を確認してください。
- DuckDB スキーマは現状で冪等に作成されるが、マイグレーション機構は未実装のためスキーマ変更時は注意が必要。

Contributing
- 貢献やバグ報告、機能提案はリポジトリの Issue / Pull Request を通じて受け付けてください。