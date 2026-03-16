# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはプロジェクトの主要な変更点・機能追加を記録するためのものです。

注: バージョンはパッケージの __version__ (src/kabusys/__init__.py) に基づきます。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システムのコア基盤を実装。

### Added
- パッケージ基本情報
  - src/kabusys/__init__.py にてパッケージ名とバージョン (0.1.0)、公開サブパッケージを定義。

- 環境設定管理
  - src/kabusys/config.py を追加。
    - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml から探索）。
    - .env ファイルの行パース実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須環境変数取得ヘルパ _require。
    - settings オブジェクトを介した設定プロパティ（J-Quants, kabu API, Slack, DB パス, 実行環境判定, ログレベル検証 等）。
    - デフォルト値: KABU_API_BASE_URL（http://localhost:18080/kabusapi）、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV の検証（development/paper_trading/live のみ有効）、LOG_LEVEL の検証。

- J-Quants データクライアント
  - src/kabusys/data/jquants_client.py を追加。
    - daily quotes（OHLCV）、financial statements（四半期 BS/PL）、JPX market calendar を取得する fetch_* 関数群。
    - API 呼び出しユーティリティ _request:
      - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
      - リトライロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx およびネットワークエラー）。
      - 429 の場合は Retry-After ヘッダを優先。
      - 401 受信時は id_token を自動リフレッシュして 1 回だけリトライ（無限再帰防止のため allow_refresh フラグ）。
      - ページネーション対応（pagination_key の取り扱い、ページ間でトークンキャッシュ共有）。
    - get_id_token によるリフレッシュトークン→id_token の取得（POST）。
    - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar:
      - fetched_at を UTC ISO8601 形式で記録（Look-ahead bias 防止のため取得時刻を明示）。
      - 冪等性確保: INSERT ... ON CONFLICT DO UPDATE による重複排除・更新。
      - PK 欠損行のスキップとログ出力、保存件数ログ。

- DuckDB スキーマ管理
  - src/kabusys/data/schema.py を追加。
    - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）+ Execution 層のテーブル定義を実装。
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw レイヤー。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤー。
    - features, ai_scores 等の Feature レイヤー。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤー。
    - 頻出クエリ向けのインデックス定義。
    - init_schema(db_path) によりディレクトリ作成→テーブル作成（冪等）を行い DuckDB 接続を返却。
    - get_connection(db_path) による接続取得（初回は init_schema を推奨）。

- 監査（Audit）ログ
  - src/kabusys/data/audit.py を追加。
    - シグナル→発注要求→約定までのトレーサビリティを保証する監査テーブル（signal_events, order_requests, executions）。
    - order_request_id を冪等キーとして設計（再送による二重発注防止）。
    - 各テーブルに created_at/updated_at を持ち、TIMESTAMP は UTC 保存（init_audit_schema は SET TimeZone='UTC' を実行）。
    - 外部キーは ON DELETE RESTRICT（監査ログは削除しない前提）。
    - インデックス（status 検索、signal_id 連携、broker_order_id 連携等）を作成。

- データ品質チェック
  - src/kabusys/data/quality.py を追加。
    - DataPlatform.md に基づく品質チェック群:
      - check_missing_data: raw_prices の OHLC 欄欠損検出（volume は許容）。
      - check_spike: 前日比スパイク検出（デフォルト閾値 50%）。
      - check_duplicates: 主キー（date, code）重複検出（通常は ON CONFLICT で防がれるが念のため）。
      - check_date_consistency: 将来日付検出 / market_calendar と整合しないデータ検出。
    - 各チェックは QualityIssue オブジェクトのリストを返し、最大サンプル 10 件を含む（Fail-Fast ではなく全件収集）。
    - run_all_checks で全チェックをまとめて実行し、error/warning の件数をログ出力。
    - SQL による実装（パラメータバインドを使用しインジェクション対策）。

- パッケージ / サブパッケージのプレースホルダ
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py, src/kabusys/monitoring/__init__.py を追加（将来の拡張用）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

## 既知の注意点 / 使用上のメモ
- 自動 .env ロードはプロジェクトルート探索に依存するため、配布後やパッケージ化された環境では想定どおり動かない場合があります。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants のレート制限や認証周りは慎重に設計されていますが、実運用では追加の監視（ログやメトリクス）やより高機能な HTTP クライアント導入を検討してください。
- DuckDB スキーマは多くのチェック制約を含みます。既存データの移行や外部からの直接書き込みがある場合は注意してください。
- すべての TIMESTAMP は UTC で扱うことを前提にしています（監査ログ初期化で SET TimeZone='UTC' を実行）。

## 開発者向け
- デフォルトの DuckDB ファイルパス:
  - DUCKDB_PATH 環境変数（デフォルト: data/kabusys.duckdb）
- モニタリング/実行周りの詳細実装は今後のリリースで追加予定。

---

（今後のリリースでは、各変更ごとに "Added/Changed/Fixed/Security" を適切に追記してください）