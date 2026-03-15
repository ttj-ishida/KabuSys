Keep a Changelog
=================

すべての重要な変更を記録します。  
このファイルは "Keep a Changelog" の形式に準拠します。

[Unreleased]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-15
-------------------

初回公開リリース。以下の主要機能・仕様を実装しています。

Added
- パッケージ初期構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0 （src/kabusys/__init__.py の __version__ を参照）
  - モジュール公開: data, strategy, execution, monitoring を __all__ に指定

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機構を実装
    - プロジェクトルートの判定は __file__ を起点に親ディレクトリを探索し、.git または pyproject.toml を検出
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - .env ファイル読み込み時、既存の OS 環境変数は保護（protected キーセット）され、.env.local は override=True で後から読み込む挙動
  - .env パーサーの実装（_parse_env_line）
    - 空行・行頭コメント（#）を無視
    - export KEY=val 形式に対応
    - シングル/ダブルクォートで囲まれた値のエスケープ処理（バックスラッシュのエスケープを解釈）
    - クォートなし値では、'#' が直前にスペース/タブのある場合にコメントとして扱う
  - 必須設定を取得するヘルパー _require()
    - 未設定時は ValueError を送出して明示的にエラー通知
  - Settings クラス（settings インスタンスを提供）
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション API: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（既定値: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
    - データベースパス: DUCKDB_PATH（既定値: data/kabusys.duckdb）、SQLITE_PATH（既定値: data/monitoring.db）
    - システム設定: KABUSYS_ENV（既定値: development、許容値: development, paper_trading, live）、LOG_LEVEL（既定値: INFO、許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - ヘルパー真偽プロパティ: is_live / is_paper / is_dev

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - データレイヤー設計に基づくテーブル群を定義（Raw / Processed / Feature / Execution の 4 層）
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な型制約（CHECK、NOT NULL、PRIMARY KEY、FOREIGN KEY）を設定し、データ整合性を確保
  - 頻出クエリ向けのインデックス定義を追加
    - 例: idx_prices_daily_code_date, idx_features_code_date, idx_signal_queue_status など
  - 公開 API
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定したパスの DuckDB を初期化し（:memory: 対応）、DDL とインデックスを適用して接続を返す
      - ファイルベースの場合、db_path の親ディレクトリが存在しないときは自動作成
      - 冪等性: 既存テーブルがあれば作成をスキップ
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない）

Other
- パッケージ構成
  - 空のパッケージエントリを用意: src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py
    - 今後の機能追加のためのプレースホルダ

Notes / 補足
- .env のパース挙動や設定名・デフォルト値はコードから推定して記載しています。運用時は .env.example 等で実際に必要なキーを明記してください。
- DB スキーマは初期設計であり、将来的に外部キー・インデックス・型等は要調整となる可能性があります。

参考
- パッケージ内部のバージョンは src/kabusys/__init__.py の __version__ を参照してください。