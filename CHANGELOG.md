CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録します。
このファイルは人間に読みやすく、かつリリースの要点を把握しやすいことを目的としています。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-03-15
-------------------

Added
- 基本パッケージ導入
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ に "data", "strategy", "execution", "monitoring" を公開。

- 環境変数・設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの検出: .git または pyproject.toml を基準に探索する _find_project_root() を追加。カレントワーキングディレクトリに依存せずパッケージ配布後も動作。
  - .env 自動読み込み制御: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。OS環境変数は protected として上書き防止。
  - .env パーサー (_parse_env_line) の強化:
    - export KEY=val 形式対応
    - シングル・ダブルクォートとバックスラッシュによるエスケープ対応
    - インラインコメント（#）の取り扱いルール（クォート無しのとき条件付きでコメント認識）
    - 無効行のスキップ
  - .env 読み込みでの I/O エラーに対する警告を発行。
  - Settings クラスを公開:
    - 必須値取得メソッド _require() を用いた必須環境変数チェック（未設定時は ValueError）。
    - J-Quants, kabu API, Slack, DB パス等の設定プロパティを提供（デフォルト値や妥当性検証あり）。
    - KABUSYS_ENV の許容値検証（development, paper_trading, live）。
    - LOG_LEVEL の許容値検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - is_live / is_paper / is_dev のヘルパープロパティ。

- データ取得クライアント: J-Quants (kabusys.data.jquants_client)
  - APIクライアントの実装（/v1 ベース）。
  - レート制限対応: 固定間隔スロットリングで 120 req/min を守る _RateLimiter 実装。
  - 冪等で共有可能なモジュールレベルの ID トークンキャッシュを実装（ページネーション間でトークン共有）。
  - リトライロジック:
    - 指数バックオフ、最大 3 回のリトライ。
    - 対象ステータスコード: 408, 429 および 5xx 系。
    - 429 の場合は Retry-After ヘッダを優先して待機時間を決定。
    - ネットワークエラー (URLError, OSError) に対する再試行。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回のみ）を実装し、リフレッシュ失敗時は適切に例外を送出。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes (株価日足: OHLCV)
    - fetch_financial_statements (四半期 BS/PL 等)
    - fetch_market_calendar (JPX マーケットカレンダー: 祝日・半日・SQ)
    - 取得結果に対して取得件数のログ出力
  - JSON デコード失敗時に詳細なエラーメッセージを出すように実装。

- DuckDB への保存ユーティリティ (kabusys.data.jquants_client の save_* 関数)
  - save_daily_quotes, save_financial_statements, save_market_calendar を提供。
  - 保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で実装し、重複を更新で解消。
  - PK 欠損レコードはスキップして警告ログを出力。
  - fetched_at は UTC タイムスタンプで記録（ISO 形式で Z を付与）。
  - 型変換ユーティリティ _to_float / _to_int を提供。_to_int は "1.0" のような文字列を float 経由で安全に int に変換し、小数部がある場合は None を返す等の厳密な挙動。

- データベーススキーマ管理 (kabusys.data.schema)
  - DataSchema.md 想定に基づく 3 層＋実行層のテーブル定義を実装（Raw / Processed / Feature / Execution）。
  - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
  - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature レイヤー: features, ai_scores
  - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な CHECK 制約、PRIMARY KEY、FOREIGN KEY を付与してデータ整合性を担保。
  - 頻出クエリを想定したインデックス群を定義（銘柄×日付走査、ステータス検索、JOIN 性能向上等）。
  - init_schema(db_path) を提供:
    - db_path の親ディレクトリを自動作成し、すべてのテーブルとインデックスを冪等に作成して DuckDB 接続を返す。
    - ":memory:" によるインメモリ DB 対応。
  - get_connection(db_path) を提供（既存 DB への接続、初期化は行わない）。

- 監査ログ・トレーサビリティ (kabusys.data.audit)
  - signal_events, order_requests, executions テーブルを用いた監査スキーマを実装。
  - トレーサビリティ階層と設計原則を反映:
    - business_date / strategy_id / signal_id / order_request_id / broker_order_id での連鎖トレース設計。
    - order_request_id を冪等キーとして扱い二重発注を防止する設計。
    - すべての TIMESTAMP を UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）。
    - エラー・棄却されたイベントも必ず記録し削除しない前提（ON DELETE RESTRICT）。
    - order_requests に対する複数のチェック制約（order_type に応じた price の必須/不要ルール）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供:
    - 既存の DuckDB 接続に対して監査テーブルを追記（冪等）。
    - 監査専用 DB の初期化サポート（親ディレクトリ自動作成、UTC 設定）。

Changed
- 初期リリース（新規実装のため、特段の変更履歴はありません）。

Fixed
- 初期リリース（新規実装のため、特段の修正履歴はありません）。

Notes / Design decisions
- 全体の設計において以下の方針を採用:
  - API のレート制限と再試行を厳密に守る（RateLimiter + 指数バックオフ）。
  - リフレッシュトークンによる自動トークン更新を行い、401 の場合は最大1回リフレッシュして再試行。
  - データ取得時刻（fetched_at）を UTC で記録し、Look-ahead bias の防止とトレーサビリティを確保。
  - DuckDB への保存は冪等化（ON CONFLICT DO UPDATE）してデータの上書きや再取得時の整合性を保つ。
  - 監査ログは削除しない運用を想定し、外部キーは ON DELETE RESTRICT を採用してトレース性を保護。

開発上のヒント
- テスト実行や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まないため、環境を明示的に制御できます。
- DuckDB を初めて使う場合は data.schema.init_schema() を呼んで DB とスキーマを作成してから get_connection() を使用してください。

--- 
(注) 本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして使う際は必要に応じて追加説明・修正・責任者情報・リンク（比較 URL / Issue / PR）などを追記してください。