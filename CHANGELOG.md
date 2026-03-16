# Changelog

すべての注目すべき変更点はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
- なし

[0.1.0] - 2026-03-16
====================
初期リリース。日本株自動売買用の基盤ライブラリを実装しました。主な追加点は以下の通りです。

Added
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは 0.1.0 に設定。
  - 公開モジュール: data, strategy, execution, monitoring（strategy と execution は初期プレースホルダ）。

- 設定管理モジュール (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読込する仕組みを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動的にルートを探す（CWD 非依存）。
  - .env のパース実装: コメント、export プレフィックス、シングル/ダブルクォート、エスケープを考慮。
  - 自動ロード優先度: OS 環境変数 > .env.local > .env。テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、アプリで必要な環境変数をプロパティ経由で安全に取得:
    - 必須変数チェック: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト付き設定: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV（検証あり）, LOG_LEVEL（検証あり）
    - ヘルパー: is_live / is_paper / is_dev

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - 機能:
    - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
    - ページネーション対応（pagination_key を用いたループ）
    - レート制限制御: 120 req/min を固定間隔スロットリングで遵守（_RateLimiter）
    - リトライロジック: 指数バックオフ、最大3回。408/429/5xx を再試行対象。429 の場合は Retry-After を優先。
    - 401 時の自動トークンリフレッシュ（1回まで）とトークンキャッシュ共有（ページネーション間で共有）
    - JSON デコードエラーハンドリング
    - fetched_at を UTC ISO8601 (Z) で付与し、Look-ahead Bias を防止する設計思想
  - DuckDB への保存関数（冪等性を担保）
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE を利用して保存
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE
  - 型変換ユーティリティ: _to_float / _to_int（空値と異常値に対する安全な変換ルール）

- スキーマ定義・初期化 (kabusys.data.schema)
  - DataPlatform に沿った 3 層（Raw / Processed / Feature）+ Execution 層の DuckDB DDL を定義。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリ用）を追加。
  - init_schema(db_path) でディレクトリ自動作成およびテーブル/インデックスの冪等初期化を実行。
  - get_connection(db_path) による接続取得（初回は init_schema を推奨）。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL のエントリポイント run_daily_etl を実装（市場カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック）。
  - 差分更新ロジック:
    - DB の最終取得日を元に差分のみ取得する。未取得時は初期日付から取り込み。
    - backfill_days により数日前から再取得して API の後出し修正を吸収（デフォルト 3 日）。
    - カレンダーは lookahead（デフォルト 90 日）を先読みして営業日判定に利用。
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl（それぞれ取得→保存を実行）。
  - ETLResult データクラス: 各種件数、品質問題リスト、エラーリストを返却。処理はステップ単位で例外を捕捉し継続する設計（Fail-Fast ではない）。

- 監査ログ（トレーサビリティ）(kabusys.data.audit)
  - シグナル→発注要求→約定の UUID 連鎖で完全にトレース可能な監査テーブルを実装。
  - テーブル:
    - signal_events（戦略が生成したシグナルの記録: decision/status を含む）
    - order_requests（発注要求: order_request_id を冪等キー、各種チェック制約、status/updated_at を持つ）
    - executions（実際の約定ログ: broker_execution_id をユニークな冪等キーとして保存）
  - すべての TIMESTAMP を UTC に保存するため init_audit_schema は SET TimeZone='UTC' を実行。
  - init_audit_db(db_path) による専用 DB 初期化 / 接続作成を提供。
  - インデックスを用意し、日付・銘柄・status による検索を高速化。

- 品質チェックモジュール (kabusys.data.quality)
  - DataPlatform に基づく品質チェック実装（SQL ベースで DuckDB に対して実行）。
  - 実装済みチェック:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損を検出（サンプル最大10件を返す）
    - 異常値（スパイク）検出 (check_spike): 前日比で閾値（デフォルト 50%）を超える変動を検出（LAG ウィンドウ使用）
    - （設計に記載）重複チェック、日付不整合検出も設計内で扱う（実装方針に準拠）
  - QualityIssue データクラスで検出結果を構造化（check_name, table, severity, detail, rows）。

Changed
- 新規リリースのため変更履歴なし。

Fixed
- 新規リリースのため修正履歴なし。

Security
- セキュリティに関する変更なし。ただし機密情報（トークン・パスワード等）は Settings 経由で環境変数から取得する設計。

注意事項 / 互換性
- DuckDB のスキーマは初期化処理で冪等に作成されるため、既存 DB に対して同じスキーマを安全に適用可能。
- J-Quants API トークン取得処理は get_id_token() がリフレッシュトークンを用いて POST するため、環境変数 JQUANTS_REFRESH_TOKEN の設定が必須。
- .env 自動読み込みはプロジェクトルート（.git か pyproject.toml）を基準に行うため、パッケージ配布後も CWD に依存せず動作する想定。ただし特殊な配置では自動ロードがスキップされる場合がある。
- strategy / execution / monitoring モジュール群はエントリを公開しているが、戦略ロジックやブローカー接続の具体実装は別途実装が必要。

参考（必須環境変数）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- SLACK_BOT_TOKEN（必須）
- SLACK_CHANNEL_ID（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- DUCKDB_PATH / SQLITE_PATH（デフォルトパス設定あり）

---

注: 本 CHANGELOG は現行コードベースの内容から推測して作成しています。将来的な API 変更や実装拡張に伴い更新してください。