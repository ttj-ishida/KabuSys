CHANGELOG
=========

すべてのリリース変更履歴は「Keep a Changelog」の形式に準拠して記載しています。  
安定版リリースや破壊的変更が発生した場合はここを更新してください。

フォーマットについて: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

（現在未リリースの変更はありません）

0.1.0 - 2026-03-15
-----------------

初回公開リリース。以下の主要機能・実装を追加しました。

Added
- パッケージ基礎
  - パッケージ名: kabusys
  - バージョン定義: src/kabusys/__init__.py に __version__ = "0.1.0"
  - パッケージ公開モジュール一覧: __all__ = ["data", "strategy", "execution", "monitoring"]

- 環境設定 / 設定管理モジュール（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダーを実装
    - プロジェクトルートの検出: .git または pyproject.toml を親ディレクトリから探索してプロジェクトルートを特定
    - 読み込み順序: OS環境変数 > .env.local > .env
    - OS 環境変数を保護するため、既存の環境変数はデフォルトで上書きされない
    - .env.local は .env の内容を上書き可能（override=True）
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト用途を想定）
  - .env パーサーの強化
    - 空行・コメント（先頭の #）を無視
    - "export KEY=val" 形式に対応
    - シングル/ダブルクォートで囲まれた値のエスケープ（バックスラッシュ）に対応し、対応する閉じクォートまでを値として扱う
    - クォート無し値の行末コメント処理: '#' が直前にスペースまたはタブがある場合のみコメントと判定
  - Settings クラスを提供（settings インスタンスをモジュールで公開）
    - 必須環境変数取得時に未設定なら ValueError を送出する _require() を実装
    - J-Quants / kabuステーション / Slack / データベース等の設定プロパティを提供:
      - jquants_refresh_token (JQUANTS_REFRESH_TOKEN)
      - kabu_api_password (KABU_API_PASSWORD)
      - kabu_api_base_url (既定: http://localhost:18080/kabusapi)
      - slack_bot_token (SLACK_BOT_TOKEN)
      - slack_channel_id (SLACK_CHANNEL_ID)
      - duckdb_path (既定: data/kabusys.duckdb)
      - sqlite_path (既定: data/monitoring.db)
      - env (KABUSYS_ENV、許可値: development, paper_trading, live) — 不正値は ValueError
      - log_level (LOG_LEVEL、許可値: DEBUG, INFO, WARNING, ERROR, CRITICAL) — 不正値は ValueError
      - is_live / is_paper / is_dev のブール判定プロパティ

- DuckDB スキーマ定義・初期化モジュール（src/kabusys/data/schema.py）
  - 3層（Raw / Processed / Feature）＋ Execution 層のテーブル設計を実装
    - Raw Layer
      - raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer
      - features, ai_scores
    - Execution Layer
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型、NULL 制約、CHECK 制約、PRIMARY KEY を付与
    - 例: prices_daily の low <= high チェック、寸法チェック（size > 0 など）、side / order_type / status の列挙チェック等
  - 外部キー制約を設定
    - news_symbols.news_id -> news_articles(id) (ON DELETE CASCADE)
    - orders.signal_id -> signal_queue(signal_id) (ON DELETE SET NULL)
    - trades.order_id -> orders(order_id) (ON DELETE CASCADE)
  - インデックスを定義（頻出クエリ最適化を想定）
    - idx_prices_daily_code_date, idx_features_code_date, idx_ai_scores_code_date, idx_signals_code_date, idx_signal_queue_status, idx_orders_status, idx_orders_signal_id, idx_trades_order_id, idx_news_symbols_code
  - スキーマ作成は冪等（CREATE TABLE IF NOT EXISTS を使用）
  - 公開関数:
    - init_schema(db_path) -> DuckDB 接続
      - 指定したパスの親ディレクトリが存在しない場合は自動作成
      - ":memory:" をサポート（インメモリ DB）
      - 全テーブルとインデックスを作成して接続を返す
    - get_connection(db_path) -> 既存の DuckDB への接続（スキーマ初期化は行わない）

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の自動ロードで OS 環境変数を保護する仕組みを導入（.env による意図しない上書きを防止）

Notes / 補足
- src/kabusys/strategy, src/kabusys/execution, src/kabusys/monitoring, src/kabusys/data の __init__.py は現時点でプレースホルダ（モジュールパッケージの骨格）として存在します。各モジュールの具体実装は今後追加予定です。
- .env のパースは Bash や POSIX の完全な互換を目指すものではなく、一般的なケース（export プレフィックス、クォート・エスケープ、行末コメント）に対応する実用的な実装としています。
- DuckDB スキーマは DataSchema.md に基づく想定設計（ドメイン的な意図に応じた列・制約を含む）。将来的に拡張やスキーマ変更が発生する可能性があります。

ライセンスや貢献方法、マイグレーションガイドなどは別途ドキュメントにまとめる予定です。