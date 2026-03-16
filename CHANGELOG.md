CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは Keep a Changelog のフォーマットに準拠しています。

Unreleased
----------

（なし）

0.1.0 - 2026-03-16
------------------

Added
- 初回リリース: KabuSys 日本株自動売買ライブラリの初期実装を追加
  - パッケージ情報
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - __all__ に data, strategy, execution, monitoring を公開（strategy, execution, monitoring はスキャフォールド）
  - 環境設定管理 (kabusys.config)
    - .env ファイルまたは環境変数から設定を自動ロード
      - 自動ロードの優先順位: OS環境変数 > .env.local > .env
      - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
      - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定（CWD 非依存）
    - 高度な .env パーサを実装
      - export KEY=val 形式に対応
      - シングル/ダブルクォート内のバックスラッシュエスケープを考慮
      - クォート無しのインラインコメント処理（'#' の前が空白／タブの場合はコメント）
      - 読み込み失敗時は警告を出力
    - Settings クラスでアプリ設定を公開
      - 必須環境変数は _require() により ValueError を投げる（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）
      - パスは Path 型で返す（duckdb/sqlite ファイルパス）
      - KABUSYS_ENV 値検証（development/paper_trading/live）
      - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - is_live / is_paper / is_dev の補助プロパティ
  - データ取得クライアント (kabusys.data.jquants_client)
    - J-Quants API クライアントを実装
      - ベースURL: https://api.jquants.com/v1
      - レート制限を厳守: 固定間隔スロットリングで 120 req/min を実現（_RateLimiter）
      - 冪等なページネーション取得をサポート（pagination_key を追跡）
      - リトライロジック: 指数バックオフ（最大 3 回）、対象ステータス: 408, 429, 5xx、ネットワークエラーもリトライ
      - 401 受信時は ID トークンを自動リフレッシュして 1 回だけリトライ（無限再帰を防止）
      - ID トークンはモジュールレベルでキャッシュ（ページネーション間で共有）
      - データ取得関数:
        - fetch_daily_quotes: 日足（OHLCV）をページネーション付きで取得
        - fetch_financial_statements: 四半期財務データを取得
        - fetch_market_calendar: JPX マーケットカレンダーを取得
      - JSON デコード失敗や HTTPError の説明的な例外処理
    - DuckDB への保存ユーティリティ:
      - save_daily_quotes / save_financial_statements / save_market_calendar を提供
      - 保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で重複を排除
      - fetched_at を UTC ISO8601 で記録して Look-ahead Bias のトレースを容易化
      - PK 欠損行はスキップし件数をログ出力
    - 型変換ユーティリティ:
      - _to_float: None/空文字列/変換失敗で None
      - _to_int: まず int 変換を試み、文字列浮動小数点（例 "1.0"）は float 経由で変換、非整数値は None を返す（意図しない切り捨て防止）
  - データスキーマ管理 (kabusys.data.schema)
    - DuckDB スキーマを定義・初期化するモジュールを追加
      - 3 層構造（Raw / Processed / Feature）＋ Execution レイヤーの DDL を定義
      - 主要テーブル（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）を作成
      - 各テーブルに制約（PRIMARY KEY、CHECK 等）を定義してデータ整合性を担保
      - パフォーマンス向けにインデックスを作成（銘柄×日付スキャン、ステータス検索などの頻出クエリを想定）
      - init_schema(db_path) によりディレクトリ自動作成 → 接続を返す（冪等）
      - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない）
  - 監査ログ（トレーサビリティ） (kabusys.data.audit)
    - 監査用テーブル群を追加（signal_events, order_requests, executions）
      - UUID ベースのトレーサビリティチェーンを想定（signal_id → order_request_id → broker_order_id → execution）
      - order_requests は冪等キー（order_request_id）をサポート（CHECK 制約で limit/stop/market の price 条件を保証）
      - executions は broker_execution_id を一意キーとして保存（外部システムからの冪等性保証）
      - ステータス遷移規約をドキュメント化（pending → sent → filled / partially_filled / cancelled / rejected / error 等）
      - init_audit_schema(conn) / init_audit_db(db_path) を提供。UTC タイムゾーンを強制（SET TimeZone='UTC'）
      - 監査用インデックスも作成（戦略別検索、pending キュー走査、broker_order_id 紐付けなど）
  - データ品質チェック (kabusys.data.quality)
    - DataQuality のチェックを提供（QualityIssue データクラスを返す）
      - check_missing_data: raw_prices の OHLC 欄の欠損検出（volume は対象外）
      - check_spike: 前日比スパイク検出（デフォルト閾値 50%）、LAG ウィンドウで前日終値を参照
      - check_duplicates: raw_prices の主キー重複検出（念のため）
      - check_date_consistency: 将来日付（reference_date より後）と market_calendar と整合しない日付（非営業日にデータがある）を検出。market_calendar が存在しない場合はスキップ
      - run_all_checks: 上記すべてを実行して QualityIssue のリストを返す。エラー／警告件数をログ出力
    - 設計方針: 全問題を収集して返す（Fail-Fast ではない）、SQL はパラメータバインドでインジェクション対策
  - パッケージ構成
    - サブパッケージ: kabusys.data（データ層）, kabusys.strategy（戦略層のスキャフォールド）, kabusys.execution（発注層のスキャフォールド）, kabusys.monitoring（監視のスキャフォールド）

Changed
- （該当なし — 初回リリース）

Fixed
- （該当なし — 初回リリース）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- 環境変数で機密情報（トークン・パスワード等）を取り扱う設計
  - 必須トークンが未設定の場合は早期に ValueError を投げて明示（運用ミスを発見しやすくする）
  - .env の自動読み込みは任意で無効化可能（テスト時の安全性向上）

Notes / Known limitations
- strategy/, execution/, monitoring/ パッケージは現時点でエントリポイント（__init__.py のみ）で、具体的な戦略実装・発注ブリッジ・監視ロジックは未実装（次フェーズの実装対象）
- テスト、ドキュメント（DataSchema.md, DataPlatform.md の参照はコード内にあるが、別途文書化が必要）
- J-Quants クライアントは urllib を使用しており、将来的に requests 等への移行を検討する余地あり
- DuckDB を前提とした設計（大容量の分析向け）。軽量環境や別 DB を利用する場合はアダプタが必要

開発上のヒント
- DB 初期化:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
- 監査スキーマ追加:
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn)
- データ取得と保存の例:
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  - records = fetch_daily_quotes(date_from=..., date_to=...)
  - save_daily_quotes(conn, records)

-- End of CHANGELOG --