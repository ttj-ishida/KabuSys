CHANGELOG
=========

すべての変更は Keep a Changelog に準拠して記載しています。  
このファイルは主にリリースノートや新機能の把握を目的としています。

フォーマット
-----------
- 変更は「Added」「Changed」「Fixed」「Removed」「Security」などに分類しています。
- 各リリースはセマンティックバージョニング（MAJOR.MINOR.PATCH）を想定しています。

[Unreleased]
------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-15
-------------------

Added
- 初回リリース: kabusys パッケージ（バージョン 0.1.0）
  - パッケージ基本情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を定義。
    - パッケージは data, strategy, execution, monitoring サブパッケージを公開（__all__）。
  - 環境設定管理モジュール（src/kabusys/config.py）
    - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
    - 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準として行うため、CWD に依存しない設計。
    - 環境変数自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で使用可能）。
    - .env パーサーは次をサポート:
      - 空行・コメント（#）を無視
      - export KEY=val 形式の対応
      - シングル／ダブルクォートで囲まれた値の解釈（バックスラッシュによるエスケープを考慮）
      - クォートがない場合の行内コメント処理（'#' の直前がスペース／タブならコメントとみなす）
    - .env ファイル読み込み時の振る舞い:
      - override=False: 既存の OS 環境変数を上書きしない（未設定のみ設定）
      - override=True: 保護されたキー（読み込み開始時の OS 環境変数セット）を上書きしない
      - 読み込み失敗時には warnings.warn で警告を出力
    - Settings による明示的プロパティ:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（有効値: development, paper_trading, live。デフォルト: development）と is_live / is_paper / is_dev ヘルパー
      - LOG_LEVEL（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO）
    - 必須変数未設定時は ValueError を送出する _require 関数を提供
    - 使い方例:
      - from kabusys.config import settings
      - token = settings.jquants_refresh_token

  - データベーススキーマ（src/kabusys/data/schema.py）
    - DuckDB を用いたスキーマ定義と初期化機能を提供
    - 3〜4 層の概念に基づくテーブル群を定義：
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに対して適切な型・NOT NULL 制約・CHECK 制約・PRIMARY KEY・外部キー制約を設定
    - 頻出クエリ向けのインデックスを定義（例: prices_daily(code, date), features(code, date), signal_queue(status) など）
    - 公開 API:
      - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - 指定したパスに対してディレクトリを自動作成（":memory:" はそのままインメモリ DB）
        - DDL を順次実行してテーブルとインデックスを作成（既存の場合はスキップ、冪等）
        - 初期化済みの接続を返す
      - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - 既存 DB へ単純に接続（スキーマ初期化は行わない。初回は init_schema を使用）
    - スキーマ設計は DataSchema.md に準拠（ドキュメント参照を想定）

  - その他のモジュール雛形
    - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py, src/kabusys/monitoring/__init__.py を配置（将来の拡張に備えたパッケージ構成）

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes
- 本リリースは初期実装（0.1.0）であり、主要な機能は設定管理とデータベーススキーマの定義に集中しています。
- 実際の取引ロジック（戦略実装）、発注・接続ロジック、モニタリング処理はパッケージの別モジュールとして今後実装を想定しています。
- 環境変数（特に API キー類）は必ず安全に管理してください（.env をコミットしない、CI / シークレットマネージャを利用する等）。

参考（簡単な使用例）
- 設定利用:
  - from kabusys.config import settings
  - print(settings.duckdb_path)
- スキーマ初期化:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

---