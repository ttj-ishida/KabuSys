CHANGELOG
=========

All notable changes to this project will be documented in this file.
このファイルは Keep a Changelog に従って変更点を記録します。
（フォーマット: https://keepachangelog.com/ja/1.0.0/）

[Unreleased]
-------------

- （今後の変更をここに記載）

[0.1.0] - 2026-03-15
-------------------

初回リリース。

Added
- パッケージ初期公開
  - kabusys パッケージ（__version__ = 0.1.0）。
  - 公開モジュール: data, strategy, execution, monitoring（strategy/execution/monitoring は初期プレースホルダ）。
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して判定）。
  - 読み込みの優先順位: OS環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ（コメント、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ対応）。
  - 必須設定取得ヘルパー _require() と Settings クラスを提供。
  - 必須環境変数（例）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（既定: data/kabusys.duckdb）
    - SQLITE_PATH（既定: data/monitoring.db）
    - KABUSYS_ENV（既定: development。有効値: development, paper_trading, live）
    - LOG_LEVEL（既定: INFO。DEBUG/INFO/WARNING/ERROR/CRITICAL を許容）
  - OS 環境変数の保護機構（.env の上書き防止）。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 価格日足、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - 認証: get_id_token()（リフレッシュトークン → idToken の取得）。
  - レート制限対応: 固定間隔スロットリングで 120 req/min に準拠する _RateLimiter を実装。
  - 再試行ロジック: 指数バックオフ、最大 3 回、対象ステータス 408/429/5xx、429 の場合は Retry-After ヘッダを優先。
  - 401 レスポンス時の id_token 自動リフレッシュ（1 回まで）とリトライ。無限再帰防止のため allow_refresh フラグを使用。
  - トークンキャッシュ（モジュールレベル）をページネーションや複数呼び出しで共有。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止できる設計。
  - 保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
    - DuckDB に対して冪等に INSERT（ON CONFLICT DO UPDATE）する実装。
    - 主キー欠損行はスキップしてログ出力（スキップ数の警告）。
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋Execution レイヤのテーブル定義を実装。
  - 主要テーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など。
  - 監査/パフォーマンスのための複数インデックス定義を含む。
  - init_schema(db_path) でデータベースの初期化（親ディレクトリ自動作成、冪等）と接続を返す。
  - get_connection(db_path) で既存 DB への接続を取得。
- 監査ログ（kabusys.data.audit）
  - 戦略→シグナル→発注要求→約定までの UUID 連鎖でトレース可能な監査テーブルを実装。
  - 主要テーブル: signal_events, order_requests, executions。
  - order_requests.order_request_id を冪等キーとして二重発注防止。
  - すべての TIMESTAMP を UTC で保存するため、init_audit_schema は SET TimeZone='UTC' を実行。
  - init_audit_schema(conn) による既存接続への監査テーブル追加、init_audit_db(db_path) による監査専用 DB 初期化を提供。
  - 監査用のインデックス群を含む（status/日付/銘柄検索などを想定）。
- データ変換ユーティリティ
  - _to_float / _to_int 実装: 空値や変換失敗時は None を返す。_to_int は "1.0" などの float 文字列を float 経由で安全に変換し、小数部が 0 以外の場合は None を返す（意図しない切り捨て防止）。
- ロギングメッセージを追加（取得件数や保存件数、リトライや警告など）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- .env 読み込みは OS 環境変数を保護（protected set）。自動読み込みを無効化する仕組みを提供（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- J-Quants id_token の取り扱いはキャッシュ化かつ期限切れ時にのみ再取得することで不必要な漏洩や再発行を抑制。

Migration / Upgrade notes
- 初回導入時:
  - 環境変数（JQUANTS_REFRESH_TOKEN 等）を設定してください。.env.example を参照して .env を作成できます。
  - データベース初期化: data.schema.init_schema(settings.duckdb_path) を実行して DuckDB スキーマを作成してください（":memory:" も可）。
  - 監査ログ追加: 既存接続に監査テーブルを追加するには data.audit.init_audit_schema(conn) を使用します。監査専用 DB を作る場合は init_audit_db() を使用してください。
- タイムゾーン:
  - 監査テーブルは init_audit_schema 実行時に TimeZone='UTC' を設定します。監査ログは UTC を前提に扱われます。
- 注意点:
  - .env の自動ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml）。パッケージ配布後やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御してください。
  - J-Quants API の再試行/レート制御の挙動により、短時間に大量リクエストを投げる用途ではスロットリングが掛かります。

既知の制限 / 今後の課題
- strategy / execution / monitoring モジュールは初期プレースホルダのみ（実装が必要）。
- J-Quants クライアントは urllib を使用。より高度な HTTP 機能（セッション管理、接続プーリング等）が必要な場合は追加検討。
- DuckDB スキーマは現状の設計に基づく。運用でのパフォーマンス観察に応じてインデックスや型を調整する可能性あり。

作者
- KabuSys チーム

問い合わせ
- リポジトリ内ドキュメント（DataSchema.md, DataPlatform.md 等）を参照してください。