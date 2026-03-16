CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。  

[未リリース]: https://example.com/kabusys/compare

## [0.1.0] - 2026-03-16
初回公開リリース。日本株自動売買プラットフォームの基盤機能を実装しています。

追加 (Added)
- パッケージ基点とバージョン
  - パッケージ初期化: kabusys.__version__ = 0.1.0、主要サブパッケージ（data, strategy, execution, monitoring）をエクスポート。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと OS 環境変数を統合して読み込む自動ロード実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサーの強化:
    - コメント行、`export KEY=val` 形式、シングル/ダブルクォートおよびエスケープシーケンス対応。
    - クォートなし値のインラインコメント扱いの条件付け（直前が空白/タブの場合のみ）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をサポート（テスト用途）。
  - Settings クラスでアプリ設定をプロパティとして公開（J-Quants / kabuステーション / Slack / DB パス / ログレベル / 環境）。
  - 必須キー未設定時は明示的なエラーを投げる _require() を提供。KABUSYS_ENV / LOG_LEVEL 値検証を実装。
  - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"（expanduser 対応）。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API ベースとトークン取得・キャッシュ: get_id_token、モジュールレベルの ID トークンキャッシュを実装。
  - レートリミッタ: 固定間隔スロットリングを用いて 120 req/min 制限を順守する _RateLimiter を実装。
  - リトライとエラーハンドリング:
    - 指数バックオフ、最大 3 回リトライ（ネットワーク系エラー、HTTP 408/429/5xx 等を対象）。
    - 401 受信時は id_token を自動リフレッシュして 1 回だけリトライ（無限再帰対策あり）。
    - 429 の場合は Retry-After ヘッダを優先。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes (株価日足 / OHLCV)
    - fetch_financial_statements (財務四半期データ)
    - fetch_market_calendar (JPX マーケットカレンダー)
  - DuckDB への保存（冪等）関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 保存は ON CONFLICT DO UPDATE を用いて冪等化。PK 欠損行はスキップしログ出力。
  - 型変換ユーティリティ: _to_float と _to_int（"1.0" のような表現を安全に扱うロジックを含む）。
- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層 の DDL を定義。
  - テーブル群（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）を実装。
  - インデックス定義（クエリパターンに基づく）とテーブル作成順を考慮した init_schema(db_path) を提供。get_connection() も実装。
  - db_path の親ディレクトリ自動作成と ":memory:" サポート。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL の統合エントリ run_daily_etl を実装（カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）。
  - 差分更新戦略:
    - 最終取得日を基に自動で date_from を算出（バックフィル日数デフォルト 3 日）。
    - 市場カレンダーは lookahead（デフォルト 90 日）で先読みして営業日調整に使用。
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl（それぞれ差分取得と保存を行う）。
  - ETLResult データクラスで実行結果／品質問題／エラーを集約。品質チェックの重大度判定ヘルパーを含む。
  - id_token 注入可能でテスト容易性を配慮。
- 品質チェック (src/kabusys/data/quality.py)
  - QualityIssue データクラスを定義。
  - チェック実装:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は除外）。
    - check_spike: LAG ウィンドウで前日比スパイク検出（閾値デフォルト 50%）。
  - 各チェックは全件収集方式（Fail-Fast ではなく問題を一覧で返す）。
  - DuckDB 上で SQL を実行する実装（パラメータバインドでインジェクション対策）。
- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - トレーサビリティ階層と監査テーブル（signal_events, order_requests, executions）を実装。
  - order_request_id を冪等キーとして扱う設計、各テーブルに created_at/updated_at を持たせる方針。
  - DuckDB 上で UTC タイムゾーンを設定して初期化する init_audit_schema / init_audit_db を提供。
  - 必須チェック制約、外部キー（ON DELETE RESTRICT）やインデックスを定義。
- データアクセスパッケージ初期化モジュール（src/kabusys/data/__init__.py）と空の strategy/execution パッケージを用意。

変更 (Changed)
- なし（初回リリース）。

修正 (Fixed)
- なし（初回リリース）。

注記（Release notes / 使用上の注意）
- 環境変数必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 未設定の場合 Settings プロパティで ValueError が発生します。
- 自動 .env ロードはプロジェクトルート検出に依存するため、配布後は環境変数での運用か KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。
- J-Quants API 呼び出しは内部でレート制御・リトライ・トークンリフレッシュを行いますが、外部要因（ネットワーク、API 仕様変更）により例外が発生する可能性があります。run_daily_etl では各ステップが独立して例外ハンドリングされ、問題が起きても他ステップは継続します（ETLResult.errors に記録）。
- DuckDB スキーマは init_schema() で冪等に作成されます。監査ログは init_audit_schema() で追加可能。
- 型変換の挙動:
  - _to_int は "1.9" など小数部が存在する文字列を None にすることで意図しない切り捨てを防止しています。
- 監査ログは設計上削除しない前提です（FK は ON DELETE RESTRICT）。

今後の予定（例）
- strategy / execution / monitoring の具体実装（戦略ロジック、注文送信ラッパー、監視・通知機能）。
- 品質チェックの追加（重複チェック、将来日付検出などの完全実装）。
- テスト・CI、ドキュメント（DataPlatform.md、DataSchema.md）に基づく追加整備。

以上

---