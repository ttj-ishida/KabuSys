Keep a Changelog
=================
すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog のガイドラインに従って作成されています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（今後の変更をここに記載）

0.1.0 - 2026-03-16
-----------------
初回リリース。

Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。モジュール構成: data, strategy, execution, monitoring（空のパッケージ初期化ファイルを含む）。
- 設定管理
  - 環境変数・設定管理モジュールを追加（kabusys.config）。
  - .env ファイルまたは OS 環境変数から設定を自動ロードする仕組みを実装。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env 読み込みの優先順位: OS 環境 > .env.local > .env。
  - .env の行パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
  - Settings クラスを実装し、J-Quants トークン、kabu API パスワード、Slack トークン・チャンネル、DB パス（DuckDB/SQLite）、実行環境（development/paper_trading/live）、ログレベル等のプロパティを提供。無効な環境値に対する検証も実装。
- J-Quants クライアント
  - J-Quants API クライアントを実装（kabusys.data.jquants_client）。
  - 機能: 日足（OHLCV）、財務諸表（四半期）、JPX マーケットカレンダーの取得。
  - レート制限保護（固定間隔スロットリング _RateLimiter、デフォルト 120 req/min）を実装。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。
  - 401 受信時の自動トークンリフレッシュを実装（1 回のみリトライし、無限再帰防止）。
  - ID トークンのモジュールキャッシュ化（ページネーション間でトークン共有）。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE を使用し重複上書き対応。PK 欠損行はスキップしログ出力。
  - データ型変換ユーティリティ（_to_float, _to_int）を実装（安全な変換と異常値取扱い）。
- スキーマ管理（DuckDB）
  - DuckDB 用スキーマ初期化モジュールを追加（kabusys.data.schema）。
  - 3 層アーキテクチャに基づくテーブル群を定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリパターンに対応）を追加。
  - init_schema(db_path) によりディレクトリ自動作成・テーブル作成を行い冪等に初期化可能。get_connection で既存 DB に接続可能。
- ETL パイプライン
  - ETL パイプラインモジュールを追加（kabusys.data.pipeline）。
  - 日次 ETL のエントリポイント run_daily_etl を実装。処理順序:
    1. 市場カレンダー ETL（先読み lookahead）
    2. 株価日足 ETL（差分取得 + backfill）
    3. 財務データ ETL（差分取得 + backfill）
    4. 品質チェック（オプション）
  - 差分更新ロジックを実装（DB の最終日を参照して未取得分のみ取得、未取得時は最古データから取得）。backfill_days により最終取得日の数日前から再取得して API の後出し修正を吸収。
  - run_prices_etl, run_financials_etl, run_calendar_etl を個別に実行可能。
  - ETL 結果を ETLResult dataclass として返却。品質問題や処理エラーは収集して呼び出し元で判定可能（Fail-Fast ではなく全件収集）。
- 品質チェック
  - データ品質チェックモジュールを追加（kabusys.data.quality）。
  - 実装済みチェック例:
    - 欠損データ検出（raw_prices の OHLC 欄の欠損検出、サンプル最大 10 行を返す）
    - スパイク検出（前日比の変動率が閾値を超えるレコード検出、ウィンドウ関数を利用）
  - QualityIssue dataclass によりチェック結果（check_name, table, severity, detail, rows）を返す設計。
  - 各チェックは DuckDB 上で効率的に SQL クエリを用いて実行し、呼び出し元が重大度に応じて停止や通知を判断できる。
- 監査ログ（トレーサビリティ）
  - 監査ログ初期化モジュールを追加（kabusys.data.audit）。
  - signal_events, order_requests, executions の監査テーブルを定義。UUID ベースのトレーサビリティチェーン（signal_id → order_request_id → broker_order_id → execution）に対応。
  - 発注の冪等キー（order_request_id）や証券会社約定 ID（broker_execution_id）をサポート。制約（CHECK, FOREIGN KEY）やインデックスも含む。
  - init_audit_schema(conn) で既存の DuckDB 接続に監査テーブルを追加。init_audit_db(db_path) で専用 DB を作成可能。
  - すべての TIMESTAMP を UTC で保存する方針を採用（初期化時に SET TimeZone='UTC' を実行）。
- ロギング／エラーハンドリング
  - 各所で詳細ログ（info/warning/error）を追加し、異常時に例外を捕捉して ETL の他ステップへ影響を与えないように設計。
  - HTTP/ネットワークエラー、JSON デコードエラーに対するエラーハンドリングと詳細メッセージ化を実施。

Changed
- 初公開のため該当なし。

Fixed
- 初公開のため該当なし。

Security
- 初公開のため該当なし。

Notes / 開発上の留意点
- .env パーサは多くのケースに対応しているが、複雑なシェル展開（${VAR} 等）はサポートしていない。
- J-Quants API の rate limit とリトライ挙動は実装済みだが、実運用では負荷状況に応じた調整や監視を推奨。
- DuckDB のスキーマは初期設計に基づく。将来的に外部キーやインデックスの見直しが必要になる可能性あり。
- 品質チェックは現在いくつかの代表的チェックを実装。運用で検出されたケースに応じて拡張を予定。

作者・著作
- kabusys コードベース（初期実装）  

--- 
（以降のリリースではここにバージョンごとの変更を追記してください）