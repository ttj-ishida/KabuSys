Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣習に従います。
セマンティック バージョニングを使用します。

[0.1.0] - 2026-03-15
-------------------

初期リリース — 基本的なアーキテクチャとデータ基盤、外部 API クライアント、環境設定管理、監査ログ機能を実装しました。

Added
- パッケージ基盤
  - kabusys パッケージの初期化（src/kabusys/__init__.py）を追加。version = 0.1.0、公開モジュールを __all__ で定義（data, strategy, execution, monitoring）。
  - strategy、execution、monitoring パッケージのプレースホルダを追加（__init__.py）。

- 環境設定 / .env ローダー（src/kabusys/config.py）
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装。プロジェクト配布後も CWD に依存せず動作。
  - OS 環境変数を保護するため .env 読み込み時に既存キーを保護（.env.local は上書き可能だが OS 環境変数は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト向け）。
  - .env 行パーサーを強化：
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - インラインコメントの取り扱い（クォートなしの場合は '#' の直前が空白またはタブのときのみコメントとみなす）
  - Settings クラスを提供し、環境変数から各種設定を取得：
    - J-Quants / kabu API / Slack / データベースパス（DuckDB/SQLite）/ 環境 (development/paper_trading/live)/ ログレベルの検証付き取得メソッド
    - env ロール判定プロパティ（is_live, is_paper, is_dev）
  - 未設定の必須環境変数アクセス時は明確なエラーメッセージを送出。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - ベース機能を実装：
    - 株価日足（OHLCV）取得 fetch_daily_quotes（ページネーション対応）
    - 財務データ（四半期 BS/PL）取得 fetch_financial_statements（ページネーション対応）
    - JPX マーケットカレンダー取得 fetch_market_calendar
    - refresh token から id token を取得する get_id_token（POST）
  - レート制限制御（120 req/min）を固定間隔スロットリングで実装（内部 RateLimiter）。
  - 再試行ロジックを実装（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
  - 401（Unauthorized）受信時は id_token を自動リフレッシュして 1 回だけ再試行（無限再帰を防止）。
  - id_token はモジュールレベルでキャッシュし、ページネーション間で共有。
  - JSON デコード失敗時やネットワークエラーに対する明確な例外処理とログ。

- DuckDB 保存ユーティリティ（src/kabusys/data/jquants_client.py）
  - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - fetched_at を UTC ISO 形式で付与（Look-ahead bias 防止のため取得日時を記録）。
    - DuckDB へは冪等性を担保する INSERT ... ON CONFLICT DO UPDATE を利用して重複更新を防止。
    - PK 欠損行はスキップし、スキップ件数を警告ログ出力。
  - 値変換ユーティリティ _to_float / _to_int を実装。_to_int は "1.0" のような float 文字列を許容するが小数部が 0 以外の場合は None を返すなど厳密な取り扱い。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DataLayer に基づくスキーマを定義・初期化：
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェック制約（CHECK）、主キー、外部キーを設定。
  - 頻出クエリを想定したインデックス群を定義（code×date、status、order_id など）。
  - init_schema(db_path) により DB ファイルの親ディレクトリを自動作成してスキーマを冪等に作成、DuckDB コネクションを返す。
  - get_connection(db_path) を提供（既存 DB への接続、初回は init_schema を推奨）。

- 監査ログ（audit）機能（src/kabusys/data/audit.py）
  - 監査用テーブル群を追加：
    - signal_events（戦略が生成した全シグナル、棄却やエラーも記録）
    - order_requests（発注要求、order_request_id を冪等キーに設定。order_type ごとのチェック制約あり）
    - executions（証券会社からの約定情報。broker_execution_id を一意キーとして冪等性を担保）
  - 監査用インデックス群を定義（signal_events の検索、order_requests の status スキャン、broker_order_id, execution の紐付け等）。
  - init_audit_schema(conn) により既存の DuckDB 接続へ監査テーブルを冪等に追加（すべての TIMESTAMP は UTC に設定）。
  - init_audit_db(db_path) を提供（監査専用 DB の初期化と接続返却）。
  - 設計方針ドキュメントに準拠したトレーサビリティ（UUID 連鎖、created_at/updated_at の運用ルール）を実装。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Notes / 補足
- 多くの設計上の注釈（レート制限、リトライポリシー、トークン自動リフレッシュ、UTC タイムスタンプ保存、冪等性のための ON CONFLICT 更新、監査ログの削除禁止方針など）がソースに記載されています。実運用前に環境変数（.env）や DuckDB スキーマ、外部 API の認証情報を正しく設定してください。
- strategy / execution / monitoring パッケージはプレースホルダの状態です。戦略実装や発注ロジック、監視機能は今後追加予定です。