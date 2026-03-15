Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。
誠実なセマンティック バージョニングに従います。
詳細: https://keepachangelog.com/ja/1.0.0/

移行メモ: この CHANGELOG はソースコードから推測して作成しています。

Unreleased
---------

- 特になし

[0.1.0] - 2026-03-15
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報
    - src/kabusys/__init__.py にて __version__ = "0.1.0"、公開モジュールとして data, strategy, execution, monitoring をエクスポート。
  - 環境設定管理モジュールを追加（src/kabusys/config.py）
    - .env ファイルおよび環境変数から設定を読み込む仕組みを実装。
    - プロジェクトルート自動検出: __file__ を起点に親ディレクトリを探索し、.git または pyproject.toml を検出してルートを特定。
      - プロジェクトルートが特定できない場合は自動ロードをスキップ。
    - .env の自動読み込みルール:
      - 読み込み優先度: OS 環境変数 > .env.local > .env
      - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
      - OS 環境変数を保護する protected キーセットを採用し、.env.local での上書きを制御。
    - 高度な .env パーサ:
      - "export KEY=val" 形式を許容。
      - シングル/ダブルクォートで囲まれた値とエスケープシーケンスに対応（閉じクォートまでを正しく解析）。
      - クォートなし値に対しては '#' をインラインコメントとして扱う条件を細かく制御（直前がスペース/タブの場合にコメント扱い）。
      - 無効行（空行やコメント行）は無視。
      - ファイル読み込み失敗時に警告を出す。
    - Settings クラスによる型付きプロパティ群を提供（環境変数取得とバリデーション）:
      - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
      - kabuステーション API: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - Slack: SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
      - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
      - システム設定: KABUSYS_ENV（development/paper_trading/live のいずれか、検証あり）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか、検証あり）
      - 環境チェック用ユーティリティ: is_live, is_paper, is_dev
      - 必須環境変数未設定時は ValueError を送出する挙動を持つ。
  - DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）
    - データレイヤ構成（ドキュメント: DataSchema.md に想定準拠）
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに対して型・NOT NULL 制約・CHECK 制約（負数禁止や列値の範囲など）を定義。
      - 例: prices_daily の low <= high チェック、raw_executions や trades の size > 0 チェック、orders/status の列挙チェックなど。
    - 主キー、外部キー制約を適切に設定（news_symbols → news_articles、orders → signal_queue、trades → orders 等）。
    - signal_queue.status、orders.status 等に文字列列挙的チェックを導入しステータス管理を明示。
    - 頻出クエリ向けのインデックスを定義:
      - prices_daily(code, date)、features(code, date)、ai_scores(code, date)、signal_queue(status)、orders(status)、orders(signal_id)、trades(order_id)、news_symbols(code) など。
    - スキーマ初期化関数:
      - init_schema(db_path) を提供。DuckDB ファイルの親ディレクトリを自動作成し、全テーブルとインデックスを作成（冪等）。
      - ":memory:" 指定でインメモリ DB をサポート。
      - get_connection(db_path) は既存 DB へ接続するユーティリティ（スキーマ初期化は行わない）として提供。
  - パッケージ構成
    - 空の __init__.py を配置してサブパッケージを用意: src/kabusys/data, src/kabusys/strategy, src/kabusys/execution, src/kabusys/monitoring（将来の機能実装用プレースホルダ）。

Changed
- 該当なし（初回リリース）

Fixed
- 該当なし（初回リリース）

Deprecated
- 該当なし

Removed
- 該当なし

Security
- 該当なし

注記 / 実装上の補足
- .env の自動読み込みはテストや CI の場面で副作用を起こす可能性があるため、KABUSYS_DISABLE_AUTO_ENV_LOAD で明示的に無効化できるように設計されています。
- Settings の一部プロパティは必須環境変数を要求します。実行前に .env.example を参考に必要な環境変数を設定してください。
- DuckDB スキーマのチェック制約や外部キーは、データ整合性を高める一方で既存データの挿入時に失敗する可能性があります。既存データを取り込む場合はスキーマに合わせて調整してください。