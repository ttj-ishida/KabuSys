# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

<!--
Maintainers: 新しい変更は最上部に Unreleased セクションを追加してください。
-->

## [Unreleased]

## [0.1.0] - 2026-03-15
初期リリース。日本株自動売買システムのコア初期実装を追加。

### 追加
- パッケージ基盤
  - src/kabusys/__init__.py
    - パッケージ名「KabuSys」を定義。バージョン情報 __version__ = "0.1.0" を追加。
    - __all__ を定義し、公開サブパッケージとして data, strategy, execution, monitoring を列挙。

- 環境設定管理モジュール
  - src/kabusys/config.py
    - 環境変数・設定を管理する Settings クラスを追加。以下のプロパティを提供：
      - J-Quants: jquants_refresh_token (必須)
      - kabuステーション API: kabu_api_password (必須)、kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
      - Slack: slack_bot_token (必須)、slack_channel_id (必須)
      - データベースパス: duckdb_path (デフォルト: data/kabusys.duckdb)、sqlite_path (デフォルト: data/monitoring.db)
      - システム設定: env (KABUSYS_ENV; 有効値: development, paper_trading, live)、log_level (LOG_LEVEL; DEBUG/INFO/WARNING/ERROR/CRITICAL)、およびユーティリティプロパティ is_live / is_paper / is_dev
    - 必須環境変数が未設定の場合は _require() が ValueError を送出するように実装。
    - 自動読み込み機能:
      - プロジェクトルートを .git または pyproject.toml を起点に探索する _find_project_root() を実装（__file__ を基準に親ディレクトリを上向き探索するため、CWD に依存しない）。
      - ルートで見つかった場合、.env を読み込んだ後 .env.local を上書き読み込み（.env.local が優先）。ただし OS 環境変数は保護され、自動上書きを防止。
      - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テストなどで使用可能）。
    - .env パーサを堅牢化:
      - export KEY=val 形式に対応。
      - シングル/ダブルクォートされた値をサポートし、バックスラッシュエスケープを考慮して対応する閉じクォートを探索。
      - クォートなし値では '#' をインラインコメントと見なす条件を制御（直前が空白/タブの場合のみコメントとして扱う）。
      - ファイル読み込み失敗時は警告を発する（warnings.warn）。

- データスキーマ（DuckDB）
  - src/kabusys/data/schema.py
    - データレイヤーに基づくスキーマ定義と初期化機能を追加（Raw / Processed / Feature / Execution の4層）。
    - 主なテーブル（DDL）を定義：
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに対して主キー、外部キー、CHECK 制約（例: price/volume が非負、side が buy/sell、status/ order_type の列挙チェック等）を定義。
    - 頻出クエリ向けに複数のインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status など）。
    - テーブル作成順序を外部キー依存を考慮して管理。
    - 公開 API:
      - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - 指定した DuckDB ファイルを初期化し、全テーブルとインデックスを作成。既存テーブルはスキップ（冪等）。db_path の親ディレクトリが存在しない場合は自動作成。":memory:" をサポートしてインメモリ DB を利用可能。
      - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - 既存の DuckDB へ接続を返す（スキーマ初期化は行わない。初回は init_schema を使用することを想定）。

- パッケージ構成（雛形）
  - src/kabusys/data/__init__.py、src/kabusys/strategy/__init__.py、src/kabusys/execution/__init__.py、src/kabusys/monitoring/__init__.py を追加（将来の機能拡張のためのモジュール雛形）。

### ドキュメント（簡易）
- config.py 内に .env 読み込みの使用例を docstring に記載。

### 既知の注意点
- 現バージョンはコアの初期実装に集中しており、実際の取引ロジック（戦略実装）、kabu API/Slack 連携の具象実装、監視モジュールの実装は含まれていません。これらは今後のリリースで拡張予定です。

---

参考: Keep a Changelog に準拠した基本カテゴリを使用しています（Added, Changed, Fixed 等）。今後の変更は Unreleased に追記し、リリースごとにバージョンと日付を追加してください。