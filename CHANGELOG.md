Changelog
=========

すべての注目すべき変更点はこのファイルに記録します。
フォーマットは 「Keep a Changelog」に準拠しています。
このプロジェクトはセマンティックバージョニングに従います。

Unreleased
----------

（現在のところ未リリースの変更はありません）

[0.1.0] - 2026-03-15
-------------------

最初の公開リリース。KabuSys のコア機能（設定管理、データ取得・保存、スキーマ定義、監査ログ基盤）を実装しました。

Added
- パッケージ初期構成
  - パッケージ名: kabusys、バージョン: 0.1.0。
  - 基本モジュール構造を追加（data, strategy, execution, monitoring）。strategy/execution/monitoring は初期のパッケージインポートポイントとして空の __init__ を提供。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数読み込み機能を実装。
    - 自動ロード順: OS 環境変数 > .env.local > .env。
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env パーサの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
    - クォートなし値のインラインコメント処理（'#' の直前が空白/タブの場合にコメントとみなす）。
    - 無効行・コメント行のスキップ。
  - 環境変数保護機構:
    - .env からの読み込み時に既存 OS 環境変数を保護（.env.local は override=True により上書き可能だが、OS 環境変数は保護）。
  - Settings クラスを公開（settings インスタンス）。
    - J-Quants / kabuステーション / Slack 用の必須トークン取得プロパティ（未設定時は ValueError）。
    - データベースパス（DuckDB/SQLite）の既定値と Path 変換。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の入力検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API クライアントを実装（/prices/daily_quotes, /fins/statements, /markets/trading_calendar 等の取得）。
  - レート制御:
    - 固定間隔スロットリングによる 120 req/min のレート制限（_RateLimiter）。
  - リトライ/エラーハンドリング:
    - 指数バックオフによる最大 3 回のリトライ（ネットワークエラーや 408/429/5xx を対象）。
    - 429 の場合は Retry-After ヘッダを優先。
    - JSON デコード失敗時の明示的エラー。
  - 認証・トークン処理:
    - リフレッシュトークンから id_token を取得する get_id_token（POST）。
    - id_token のモジュールレベルキャッシュを保持し、ページネーション間で共有。
    - 401 受信時は id_token を 1 回自動リフレッシュして再試行（無限再帰防止）。
  - ページネーション対応:
    - fetch_* 系関数は pagination_key を用いて全ページを取得（ループ検出防止のため seen_keys を使用）。
  - Look-ahead bias 防止:
    - データを保存する際に取得時刻を UTC で記録（fetched_at）。
  - データ保存（DuckDB 向け）:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 主キー欠損行はスキップし、スキップ件数をログに出力。
    - 冪等性のため INSERT ... ON CONFLICT DO UPDATE を用いた upsert を実施。
  - データ変換ユーティリティ:
    - _to_float / _to_int を実装。空値や変換失敗は None、"1.0" のような float 文字列は整数に変換するが "1.9" のような非整数は None を返す等の仕様。

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマを定義。
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約・チェック制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）を定義してデータ整合性を担保。
  - 検索パフォーマンス向けに主要インデックスを作成（銘柄・日付、ステータス検索、外部キー結合列など）。
  - init_schema(db_path) を実装:
    - DuckDB ファイルを初期化して全テーブル・インデックスを作成（冪等）。
    - db_path の親ディレクトリが存在しない場合は自動作成。
    - ":memory:" でインメモリ DB をサポート。
  - get_connection(db_path) を提供（既存 DB に接続、スキーマ初期化は行わない）。

- 監査ログ / トレーサビリティ基盤（kabusys.data.audit）
  - 戦略→シグナル→発注→約定のトレーサビリティを担保する監査テーブル群を実装。
    - signal_events（戦略が生成した全シグナルとステータス/理由を保存）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ。limit/stop/maket 注文の制約を強制）
    - executions（証券会社からの約定を記録。broker_execution_id をユニーク冪等キーとして扱う）
  - 設計方針を DB レベルで反映:
    - order_request_id は冪等キーとして二重発注を防止。
    - 監査ログは削除しない前提（ON DELETE RESTRICT を使用）。
    - すべての TIMESTAMP を UTC で保存（init_audit_schema で SET TimeZone='UTC' を実行）。
    - created_at / updated_at を持ち、アプリからの更新で updated_at を更新する想定。
    - order_requests のステータス遷移仕様（pending → sent → filled/partially_filled/cancelled/rejected/error）をドキュメントに記載。
  - インデックスを整備（シグナル検索、日付/銘柄検索、status キュー取得、broker_order_id 等）。

Changed
- 初回リリースにつき「変更」はなし。

Fixed
- 初回リリースにつき「修正」はなし。

Security
- セキュリティ関連の注意:
  - .env にシークレットを置く運用ではファイルパーミッション等に注意すること。
  - OS 環境変数を保護する仕組みを導入（.env 読み込み時に上書きされない）。

Notes / 既知の制限
- strategy, execution, monitoring モジュールはパッケージ階層に存在するが、具体的な戦略ロジックや発注実行ロジックはこのリリースでは実装されていません（インポートポイントとしての空モジュールを用意）。
- J-Quants クライアントは urllib を使った実装であり、将来的に httpx や requests などへの切替検討が可能です。
- DuckDB の UNIQUE インデックスは NULL の扱いが DB 毎に挙動が異なる点に注意（コメントに記載あり）。

互換性
- 初期リリースのため互換性に関する破壊的変更はありません。

作者
- KabuSys 開発チーム

（詳細な設計原則や DataPlatform.md / DataSchema.md 等の参照ドキュメントはコード内部の docstring に記載）