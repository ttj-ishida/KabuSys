CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。
このプロジェクトはセマンティックバージョニングを採用しています。  

[Unreleased]
-------------


[0.1.0] - 2026-03-15
--------------------

Added
- 初回リリース: KabuSys — 日本株自動売買システムの基本パッケージを追加。
  - パッケージ構成:
    - kabusys (ルート)
    - サブパッケージ: data, strategy, execution, monitoring（各 __init__.py を用意）
  - バージョン情報: __version__ = "0.1.0"

- 環境設定モジュール (kabusys.config)
  - .env ファイルまたは既存の OS 環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートを .git または pyproject.toml を起点に検出するため、CWD に依存しない実装。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサを実装（エッジケースに対応）
    - 空行・コメント行（# で始まる行）を無視。
    - "export KEY=val" 形式に対応。
    - シングル／ダブルクォートされた値のバックスラッシュエスケープを正しく扱う。
    - クォートなし値におけるインラインコメントの判定（直前にスペース/タブがある場合のみコメントとみなす）。
  - .env 読み込み時の挙動
    - override=False: 未設定のキーのみセット（OS 環境変数を保持）。
    - override=True: protected（読み込み時にキャプチャした OS 環境変数キー）を除き上書き。
    - ファイル読み込み失敗時には warnings.warn を発行して処理を継続。
  - Settings クラスを提供（環境変数から値を取得するプロパティ群）
    - J-Quants / kabuステーション / Slack / DB 等の必須設定を取得するプロパティ（未設定時は ValueError を送出）。
    - DB パスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"（Path.expanduser を使用）。
    - kabu API のデフォルト URL: http://localhost:18080/kabusapi
    - 環境（KABUSYS_ENV）のバリデーション（development / paper_trading / live のみ有効）。
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev の便利なブールプロパティ。

- DuckDB スキーマ定義・初期化モジュール (kabusys.data.schema)
  - DataSchema.md に基づき、4 層（Raw / Processed / Feature / Execution）のテーブル定義を実装。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して:
    - 型指定とチェック制約（例えば価格 >= 0、サイズ > 0、ENUM 的チェック）を付与しデータ整合性を強化。
    - 主キーと外部キー制約を適宜設定（news_symbols -> news_articles、orders -> signal_queue、trades -> orders 等）。
  - インデックスを追加して典型的クエリ（銘柄×日付スキャン、ステータス検索等）の性能を改善。
  - 公開 API:
    - init_schema(db_path) : DuckDB ファイルを初期化し全テーブル及びインデックスを作成して接続を返す。
      - 冪等（既存テーブルはスキップ）。
      - db_path が ":memory:" であればインメモリ DB を使用。
      - ファイル DB の場合、親ディレクトリが存在しなければ自動作成。
    - get_connection(db_path) : 既存 DB への単純な接続を返す（スキーマ初期化は行わない）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 備考
- strategy, execution, monitoring パッケージはエントリポイント（__init__.py）を用意済みで、今後各機能（シグナル生成、発注ロジック、監視/アラート等）を実装予定です。
- .env パーサは多くの典型的な .env 構文に対応していますが、特殊ケースでの振る舞いは実運用での確認を推奨します。