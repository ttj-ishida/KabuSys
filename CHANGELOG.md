# Changelog

すべての変更は Keep a Changelog の仕様に準拠して記載しています。  
このファイルはコードベースから推測した初期リリース向けの変更履歴です。

フォーマット: 年-月-日（リリース日）

## [Unreleased]
- なし

## [0.1.0] - 2026-03-15
初期リリース。以下の主要機能と実装を含みます。

### 追加
- パッケージ基礎
  - pakage 名称: kabusys、バージョン __version__ = "0.1.0"
  - 公開モジュール: data, strategy, execution, monitoring（各サブパッケージの __init__.py を含む薄いスケルトン）
- 設定・環境変数管理 (`kabusys.config`)
  - プロジェクトルート検出: 現在ファイルを起点に親ディレクトリを探索し、`.git` または `pyproject.toml` を基準にルートを特定するユーティリティを実装。これにより CWD に依存しない自動 `.env` ロードが可能。
  - .env パーサ: `_parse_env_line` により以下の形式に対応
    - 空行、コメント行（#）を無視
    - `export KEY=val` 形式をサポート
    - シングル/ダブルクォートで囲まれた値のエスケープ処理（バックスラッシュ）を考慮して正しくパース
    - クォートなし値に対するインラインコメント判定（# の直前がスペース／タブの場合にコメントとみなす）
  - .env ファイル読み込み: `_load_env_file` によりファイルの存在チェック、エンコーディング utf-8 での読み込み、読み込み失敗時は警告を発行する実装。引数で override と protected キーを指定可能（既存 OS 環境変数を保護）。
  - 自動ロード順序: OS 環境変数 > .env.local > .env（`.env.local` は上書き許可）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。プロジェクトルートが特定できない場合は自動ロードをスキップ。
  - 必須変数チェック: `_require` により未設定時は ValueError を送出（.env.example を参照する旨のメッセージ）。
  - Settings クラス: 各種設定プロパティを提供（J-Quants リフレッシュトークン、Kabu API パスワード、Kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）、Slack トークン・チャンネル、DB パス等）。デフォルト値や Path 展開、型変換を含む。
  - 環境種別・ログレベル検証: KABUSYS_ENV は (development|paper_trading|live) のみ許容、LOG_LEVEL は標準ログレベルのみ許容。検証に失敗した場合は ValueError を送出。便利な bool 判定プロパティ（is_live, is_paper, is_dev）を提供。
- データベーススキーマ（DuckDB） (`kabusys.data.schema`)
  - レイヤー設計に基づくテーブル定義（DDL）を実装
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して型、主キー、制約（CHECK、NOT NULL）、外部キーを定義。例:
    - price 列の非負制約、volume の非負チェック
    - side 列に対する IN ('buy','sell') 制約
    - order_type, status 等の列に対する列挙的チェック
    - 外部キーによる参照（news_symbols → news_articles、orders.signal_id → signal_queue、trades.order_id → orders など）と適切な ON DELETE 動作（CASCADE/SET NULL）
  - インデックス定義: 頻出クエリに基づくインデックスを作成（例: prices_daily(code, date)、features(code, date)、signal_queue(status)、orders(status) など）
  - スキーマ初期化 API:
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 全テーブルとインデックスを作成（冪等）。db_path の親ディレクトリが存在しない場合は自動作成。":memory:" によるインメモリ DB をサポート。
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を推奨）。
- 実装上の利便性
  - init_schema は既存テーブルを上書きせずに実行できる（CREATE IF NOT EXISTS を使用）。
  - 強い型付け・制約を用いたデータ整合性の担保。
  - 各種テーブル・列名は将来の戦略やモニタリング用途を意識した命名（features, ai_scores, signal_queue, portfolio_performance 等）。

### 変更
- なし（初期リリース）

### 修正
- なし（初期リリース。ただし設計上の安全策: .env 読み込み失敗時に警告を出す、スキーマ作成は冪等にして既存データの安全を考慮）

### セキュリティ
- なし

注記:
- この CHANGELOG は提供されたソースコードの内容から推測して作成したものです。README、リリースノート、コミット履歴があれば更に正確に整備可能です。