CHANGELOG
=========

本CHANGELOGは Keep a Changelog の形式に準拠します。  
このファイルはコードベース（src/kabusys）から推測して作成した初期リリースの変更履歴です。

フォーマット:
- すべての変更は意味のあるカテゴリ（Added, Changed, Fixed, Deprecated, Removed, Security）に分類しています。
- 日付はこのCHANGELOG作成日（YYYY-MM-DD）を使用しています。

Unreleased
----------
（現在未リリースの項目はありません）

[0.1.0] - 2026-03-15
-------------------

Added
- パッケージ基盤を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py の __version__ に基づく)
  - エクスポートモジュール: data, strategy, execution, monitoring

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加
  - 自動 .env ロード機能（プロジェクトルートの .env / .env.local）を実装
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
    - プロジェクトルート判定は __file__ を基点に .git または pyproject.toml を探索
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）
  - 上書きポリシー:
    - .env は OS 環境変数を保護（protected set）したうえで読み込み
    - .env.local は .env の値を上書き可能
  - 必須環境変数取得ヘルパ _require() と Settings のプロパティ群を追加
    - J-Quants / kabu API / Slack / データベース（DuckDB/SQLite）などの設定をカバー
  - 環境変数値検証:
    - KABUSYS_ENV の許容値（development, paper_trading, live）
    - LOG_LEVEL の許容値（DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - 環境判定ユーティリティプロパティ（is_live, is_paper, is_dev）

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 基本設計: レート制限遵守、リトライ、トークン自動リフレッシュ、look-ahead 防止（fetched_at）、冪等性
  - レート制御: 固定間隔スロットリング _RateLimiter（120 req/min を既定値）
  - HTTP リクエストラッパ _request():
    - JSON デコード検出、再試行ロジック（指数バックオフ）、HTTP ステータス別処理
    - 401 を検出した場合は ID トークンを自動リフレッシュして1回リトライ
    - 408 / 429 / 5xx 系に対するリトライ（最大 3 回）
    - 429 の場合は Retry-After を優先して待機
  - 認証関数 get_id_token(refresh_token: Optional[str]) を実装（POST /token/auth_refresh）
  - データ取得関数（ページネーション対応）
    - fetch_daily_quotes(...) : 株価日足（OHLCV）
    - fetch_financial_statements(...) : 四半期財務データ（BS/PL）
    - fetch_market_calendar(...) : JPX マーケットカレンダー（祝日・半日・SQ）
  - データ保存（DuckDB）用関数（冪等）
    - save_daily_quotes(conn, records) : raw_prices へ INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements(conn, records) : raw_financials へ同様の冪等挿入
    - save_market_calendar(conn, records) : market_calendar へ同様
    - 保存時に fetched_at を UTC ISO8601（Z付き）で記録し、Look-ahead Bias 防止
  - 型変換ユーティリティ:
    - _to_float(), _to_int()（空値・不適切な値は None を返す。_to_int は小数部が 0 以外の float 文字列は None にする）

- DuckDB スキーマ（src/kabusys/data/schema.py）
  - DataSchema.md を想定した 3 層＋実行層のテーブル定義を実装
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・制約（CHECK, PRIMARY KEY, FOREIGN KEY）を設定
  - パフォーマンス向けインデックスを多数追加（例: code/date の複合インデックス、status 検索用など）
  - init_schema(db_path) を提供:
    - ディレクトリ自動作成、DDL を順次実行して冪等にテーブルとインデックスを作成
    - ":memory:" によるインメモリ DB 対応
  - get_connection(db_path) を提供（既存 DB 接続取得、初期化は行わない）

- 監査（Audit）スキーマ（src/kabusys/data/audit.py）
  - シグナルから約定までのトレーサビリティ用テーブルを実装
    - signal_events（戦略が生成したすべてのシグナルを記録）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社からの約定ログ、broker_execution_id を冪等キーとして利用可能）
  - 設計方針:
    - すべての TIMESTAMP を UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）
    - 削除を想定しない（ON DELETE RESTRICT の外部キー等）
    - 状態遷移やエラー情報を格納（status, error_message 等）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供（既存 conn への追加や専用 DB の初期化）

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 認証トークンの自動リフレッシュとキャッシュを実装し、401 に対する自動復旧を提供
- 環境変数の取り扱い: OS 環境変数を既定で保護し、.env による上書きを必要に応じて制御

Notes / 開発者向け補足
- DB 初期化:
  - シンプルな開始手順例:
    - from kabusys.data.schema import init_schema
    - conn = init_schema(settings.duckdb_path)
  - 監査ログを別 DB で管理したい場合は init_audit_db() を使用
- 自動 .env 読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後に期待どおり動作させるには .git または pyproject.toml を含めるか、自動読み込みを無効化して明示的に環境を設定してください。
- 例外とリトライ:
  - ネットワーク系エラーや一部 HTTP ステータスは内部でリトライしますが、最大試行回数を超えると RuntimeError を返します。呼び出し側は例外ハンドリングを行ってください。
- タイムスタンプは原則 UTC 保存（fetched_at, created_at など）

Known limitations / TODO（推測）
- strategy / execution / monitoring パッケージは __init__.py は存在するが具体的実装は未提供（将来追加予定）
- テストコードやエンドツーエンドの統合テストはこのリリースのコードからは確認できない
- J-Quants のスキーマやフィールド名の変更に対する柔軟性は将来的に強化の余地あり

ライセンス / 著作権
- このCHANGELOGはコードベースの内容から推測して作成したものであり、実際のリリースノートは実装・ドキュメントの責任者によって正式に作成してください。