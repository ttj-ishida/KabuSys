KEEP A CHANGELOG
すべての注目すべき変更点はこのファイルに記録します。
比較的堅牢で読みやすい履歴を保つために "Keep a Changelog" の形式に従います。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------
- なし

[0.1.0] - 2026-03-15
--------------------
Added
- パッケージ初期リリース (バージョン 0.1.0)
  - src/kabusys/__init__.py
    - パッケージメタ情報を追加。__version__ = "0.1.0"。
    - public API として data, strategy, execution, monitoring を __all__ に公開。

  - src/kabusys/config.py
    - 環境変数・設定管理モジュールを追加。
    - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
      - 読み込み順序: OS環境変数 > .env.local > .env
      - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
      - プロジェクトルートの検出は __file__ を基点に .git または pyproject.toml を探索して行う（CWD に依存しない）。
    - .env 行パーサーを実装（_parse_env_line）。
      - 空行・コメント行を無視。
      - export KEY=val 形式に対応。
      - シングル/ダブルクォートを考慮した値のパース（バックスラッシュエスケープ対応）。
      - クォートなし値ではインラインコメント扱いを空白・タブの直前のみとするなど、現実的な .env 仕様に準拠。
    - .env ファイル読み込み処理（_load_env_file）
      - override フラグと protected キーセットをサポートし、OS 環境変数（protected）を誤って上書きしない設計。
      - ファイル読み込み失敗時は警告を出す。
    - Settings クラスを提供（settings インスタンスをモジュールレベルで公開）。
      - J-Quants, kabuステーション API, Slack, データベースパス等のプロパティを定義。
      - 必須項目の取得は _require() を使用し、未設定時は ValueError を送出。
      - env（KABUSYS_ENV）と log_level（LOG_LEVEL）の検証を実装。有効値はそれぞれ固定集合でチェック。
      - is_live / is_paper / is_dev のユーティリティプロパティを追加。

  - src/kabusys/data/schema.py
    - DuckDB 用のスキーマ定義と初期化機能を追加。
    - 3 層（Raw / Processed / Feature）+ Execution レイヤーに対応する多数のテーブルの DDL を定義。
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに対して制約（PRIMARY KEY、CHECK、FOREIGN KEY 等）を付与してデータ整合性を担保。
    - クエリパターンを想定したインデックスを定義（銘柄×日付スキャン、ステータス検索など）。
    - init_schema(db_path) を実装
      - 指定したパスの DuckDB を初期化して全テーブル／インデックスを作成（冪等）。
      - db_path の親ディレクトリが無ければ自動作成。
      - ":memory:" によるインメモリ DB をサポート。
      - 初期化後、DuckDB 接続オブジェクトを返却。
    - get_connection(db_path) を実装
      - 既存 DB へ接続するユーティリティ（スキーマ初期化は行わない旨を明示）。

  - パッケージ構成（空の __init__.py を含むモジュール群）
    - src/kabusys/data/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/monitoring/__init__.py
    - 基本的なモジュール階層を用意し、今後の機能追加（データ取得、戦略、実行、モニタリング）に備える。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

注記 / リリースノート
- .env 自動読み込みの挙動はデフォルトで有効です。CI やテスト中に自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- Settings の必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）が未設定の場合、アクセス時に ValueError を送出します。デプロイ前に .env を用意するか環境変数をセットしてください。
- DuckDB スキーマは初期化処理で冪等に作成されますが、スキーマ変更（マイグレーション）が必要な場合は将来のバージョンでマイグレーション機構を追加する予定です。