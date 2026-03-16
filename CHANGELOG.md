# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  
安定版はセマンティックバージョニングに従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買プラットフォームの基盤ライブラリを追加しました。以下の主要コンポーネントと機能を含みます。

### 追加 (Added)
- パッケージ全体
  - パッケージバージョンを 0.1.0 に設定（kabusys.__version__）。
  - 公開モジュール: data, strategy, execution, monitoring をエクスポート。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みするロジックを実装。
    - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して特定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途）。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、行末コメントの扱いに対応）。
  - 環境変数取得用 Settings クラスを追加（settings インスタンスを公開）。
    - 必須キー取得時に未設定なら ValueError を送出する _require を提供。
    - サポートされる設定例（必須・任意）:
      - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - 任意/デフォルト: KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)、DUCKDB_PATH (data/kabusys.duckdb)、SQLITE_PATH (data/monitoring.db)、KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）
    - is_live / is_paper / is_dev の便利プロパティを提供。
  - 設定値の検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。

- J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API 用クライアントを実装。
    - 取得対象: 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー。
  - 設計上の特徴:
    - API レート制限対応（120 req/min）: 固定間隔スロットリング実装 (_RateLimiter)。
    - リトライロジック（指数バックオフ、最大 3 回、対象: 408 / 429 / 5xx、ネットワークエラーも再試行）。
    - 401 受信時の自動トークンリフレッシュを 1 回行う処理（再帰無限ループ防止のため allow_refresh の制御）。
    - ページネーション対応（pagination_key を用いたフェッチの継続）。
    - データ取得時の fetched_at を UTC ISO8601 で記録する保存関数を実装（Look-ahead Bias 防止のため）。
  - 公開関数:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
    - save_daily_quotes(conn, records) -> int
    - save_financial_statements(conn, records) -> int
    - save_market_calendar(conn, records) -> int
  - モジュールレベルの ID トークンキャッシュを実装（ページネーション／複数呼び出しでトークンを共有）。
  - JSON デコード時のエラーメッセージ改善（レスポンスの先頭をログに含める）。

- DuckDB スキーマと初期化 (kabusys.data.schema)
  - DataSchema.md に基づく多層スキーマを提供（Raw / Processed / Feature / Execution 層）。
  - テーブル定義（代表的なもの）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 頻出クエリに基づいたインデックスを作成。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成と DDL 実行（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化を行わない既存 DB への接続）。

- 監査ログ（Audit） (kabusys.data.audit)
  - シグナル → 発注 → 約定を追跡する監査テーブル群を実装（UUID 連鎖）。
  - DDL:
    - signal_events（戦略が生成したシグナルのログ、rejected なども記録）
    - order_requests（発注要求、order_request_id を冪等キーとして扱う）
    - executions（証券会社からの約定ログ、broker_execution_id を冪等キーとして想定）
  - インデックス群を定義（status や signal_id / broker_order_id に対する検索を最適化）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。init_audit_schema は接続に対して UTC タイムゾーンを設定してテーブルを作成。

- データ品質チェック (kabusys.data.quality)
  - DataPlatform.md に基づく品質チェックモジュールを実装。
  - チェック項目:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損（volume は除外）
    - 異常値検出 (check_spike): 前日比スパイク（デフォルト閾値 50%）
    - 重複チェック (check_duplicates): raw_prices の主キー重複（date, code）
    - 日付不整合 (check_date_consistency): 将来日付 / market_calendar と矛盾するデータ
  - QualityIssue dataclass を導入（check_name, table, severity, detail, rows）。
  - run_all_checks() で一括実行し、すべての問題を収集して返す（Fail-Fast ではなく問題を全件報告）。
  - SQL はパラメータバインドを使用してインジェクションリスクを低減。

### 変更 (Changed)
- 初版のため変更履歴なし。

### 修正 (Fixed)
- 初版のため修正履歴なし。

### 破壊的変更 (Breaking Changes)
- 初版のため破壊的変更なし。

### 既知の注意点・運用メモ
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後に CWD が変わっても期待通りに動作するよう設計されています。必要に応じて自動読み込みを無効化してください（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- J-Quants API のレート制限や 401 リフレッシュはクライアント側で扱いますが、運用環境ではトークンや接続設定を適切に管理してください。
- DuckDB スキーマの初期化は init_schema を呼ぶだけで完了します。監査ログを別 DB に分けたい場合は init_audit_db を利用できます。
- save_* 系の関数は冪等（ON CONFLICT DO UPDATE）で実装されていますが、スキーマを変更した場合の互換性には注意してください。

### 必須環境変数（初期セットアップガイド）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- （任意）KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- （任意）LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- （任意）DUCKDB_PATH（デフォルト: data/kabusys.duckdb）

---

参考: 各モジュールの公開 API を利用して DB 初期化やデータ取り込み、品質チェック・監査ログ初期化を行うことを想定しています。今後のリリースでは strategy / execution / monitoring 層の実装拡張、テストカバレッジの追加、エラーハンドリング改善や運用向けドキュメント整備を行う予定です。