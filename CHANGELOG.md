Changelog
=========
すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このプロジェクトはセマンティックバージョニングを使用します。

Unreleased
----------
（未リリースの変更はここに記載）

0.1.0 - 2026-03-15
-----------------
Added
- 初期リリース。
- パッケージのメタ情報を追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
  - パッケージ公開 API: `__all__ = ["data", "strategy", "execution", "monitoring"]`
  - 空のサブパッケージ初期化ファイルを配置（strategy / execution / data / monitoring の枠組みを準備）。
- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルまたはシステム環境変数から設定を読み込む機能を実装。
  - プロジェクトルート検出: パッケージ内部の __file__ を起点に親ディレクトリを探索し、.git または pyproject.toml を検出してルートを特定。
  - 自動ロードの順序: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを停止可能（テスト等で利用）。
  - .env パーサーの強化:
    - 空行/コメント（先頭 #）を無視。
    - `export KEY=value` 形式を受け付ける。
    - シングル/ダブルクォートで囲まれた値のエスケープ（バックスラッシュ）に対応し、インラインコメントを無視して正しく値を抜き出す。
    - クォートなし値のコメント解釈は、`#` の直前がスペースまたはタブの場合にのみコメントとみなす実装。
  - .env 読み込み時の挙動:
    - override=False: 未設定のキーのみ設定。
    - override=True: protected（元の OS 環境変数）に含まれるキーは上書きせず、それ以外は上書き。
  - .env ファイルの読み込みに失敗した場合は warnings.warn で警告を出力。
  - 必須環境変数取得ヘルパー `_require()` を用意（未設定時は ValueError を送出）。
  - Settings クラスを公開（settings = Settings()）:
    - J-Quants、kabuステーション API、Slack、データベースパス等のプロパティを提供。
    - デフォルト値: `KABUSYS_ENV` → "development"、`KABUS_API_BASE_URL` のデフォルト、`LOG_LEVEL` デフォルトなどを実装。
    - 値検証: `KABUSYS_ENV` は ("development","paper_trading","live") のみ許可、`LOG_LEVEL` は標準ログレベルのみ許可。無効な場合は ValueError を送出。
    - ヘルパー: `is_live`, `is_paper`, `is_dev` を提供。
- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）
  - データレイヤー設計（ドキュメント: DataSchema.md 想定）に基づく 3+1 層のテーブル定義を提供:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・CHECK 制約・PRIMARY KEY を定義（例: price >= 0、size > 0、side は 'buy'/'sell' 等）。
  - 外部キー制約を定義（news_symbols → news_articles、orders → signal_queue、trades → orders 等）。
  - 頻出クエリに対するインデックスを複数定義（code/date に対するインデックス、status 検索用など）。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定したパスに対してディレクトリを自動作成（":memory:" の場合はメモリ DB を使用）。
      - 全 DDL を実行してテーブルとインデックスを冪等的に作成し、接続を返す。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存の DuckDB へ接続（スキーマ初期化は行わない。初回は init_schema を推奨）。
- ドキュメント的注釈・実装上の配慮
  - init_schema は既存テーブルの存在時にスキップする（冪等性確保）。
  - スキーマ作成順は外部キー依存を考慮して定義。
  - 各テーブルに対して PRIMARY KEY・CHECK 等の制約を設定してデータ整合性を高める。

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