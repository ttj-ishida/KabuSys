CHANGELOG
=========

すべての注目すべき変更点を記録します。This project adheres to Keep a Changelog の形式に準拠します。
リリースはセマンティックバージョニングに従います。

[Unreleased]: https://example.com/kabusys/compare/v0.1.0...HEAD

v0.1.0 - 2026-03-16
-------------------

初回リリース。日本株自動売買プラットフォームの基盤機能を実装しました。

Added
- パッケージメタ情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。
  - パッケージ公開 API に data, strategy, execution, monitoring を含める（strategy/execution は placeholder）。
- 環境設定管理（kabusys.config）
  - .env / .env.local ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装:
    - export プレフィックス対応（export KEY=val）。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなしでのインラインコメント認識（直前が空白/タブの '#' をコメントとみなす）。
    - 読み込み時に OS 環境変数を保護する機能（.env.local は .env より優先して上書き）。
  - Settings クラスを提供し、必要な設定値をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のヘルパープロパティ
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本機能:
    - 日足（OHLCV）、四半期財務、JPX マーケットカレンダーを取得する fetch_* 関数を実装。
    - ページネーション対応（pagination_key を用いた連続取得）。
  - 認証・トークン管理:
    - refresh_token から id_token を取得する get_id_token 実装。
    - モジュールレベルで id_token をキャッシュし、ページネーション間で共有。
    - 401 受信時に自動リフレッシュして最大1回リトライ（無限再帰防止）。
  - レート制限・リトライ:
    - 固定間隔スロットリングで J-Quants のレート制限（120 req/min）を遵守する RateLimiter を実装。
    - 指数バックオフによるリトライ（最大 3 回）。408/429/5xx を再試行対象とし、429 の場合は Retry-After ヘッダを優先。
    - ネットワークエラー（URLError / OSError）も再試行。
  - データ保存:
    - DuckDB に対する idempotent な保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE）。
    - fetched_at を UTC タイムスタンプ（ISO 8601 Z表記）で付与。
  - ユーティリティ:
    - _to_float, _to_int により文字列等から安全に数値変換（不正値は None）。
- DuckDB スキーマと初期化（kabusys.data.schema）
  - 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を実装:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）および想定されるインデックスを定義。
  - init_schema(db_path) でディレクトリ作成→テーブル作成（冪等）し、DuckDB 接続を返す。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。
- データ ETL パイプライン（kabusys.data.pipeline）
  - ETL フローを実装:
    - 差分更新: DB の最終取得日から必要範囲のみ取得（デフォルトバックフィル 3 日で API の後出し修正を吸収）。
    - 市場カレンダーは先読み（デフォルト 90 日）して営業日調整に使用。
    - 個別 job: run_prices_etl, run_financials_etl, run_calendar_etl（各々差分取得・保存を行う）。
    - 日次統合: run_daily_etl でカレンダー→株価→財務→品質チェックの順で実行。各ステップは独立して例外処理し、他ステップは継続する設計（Fail-Fast しない）。
  - ETLResult dataclass を定義（取得数/保存数/品質問題/エラーの収集と to_dict）。
  - 品質チェックモジュール（quality）との連携を実装（run_all_checks を呼び出し、結果を ETLResult に格納）。
- 監査ログ（トレーサビリティ）スキーマ（kabusys.data.audit）
  - 信号→発注要求→約定までを UUID で完全トレース可能にする監査テーブルを実装:
    - signal_events（シグナル生成ログ: strategy_id, decision, reason, created_at 等）
    - order_requests（冪等キー order_request_id、注文種別チェック、価格チェック、ステータス管理）
    - executions（証券会社提供の約定ID を一意に記録、commission 等）
  - init_audit_schema(conn) で監査テーブルとインデックスを追加（UTC タイムゾーンを強制）。
  - init_audit_db(db_path) を提供（監査専用 DB 初期化）。
- データ品質チェック（kabusys.data.quality）
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は対象外）。検出時は severity="error"。
    - check_spike: LAG ウィンドウ関数を用いた前日比スパイク検出（デフォルト閾値 50%）。
  - チェックはすべて DuckDB 上の SQL（パラメータバインド）で効率的に実行し、最大 10 件のサンプル行を返す。
- プレースホルダーモジュールとパッケージ構成
  - パッケージツリーを整理（kabusys.data, kabusys.strategy, kabusys.execution の __init__ を配置）。
  - strategy と execution パッケージは現時点では空の初期化ファイルのみ（戦略・実行ロジックは今後実装予定）。
  - monitoring が __all__ に含まれるが、ソース内に monitoring モジュールの実装は含まれていません（将来追加予定）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- J-Quants id_token はモジュール内でキャッシュされるが、refresh は明示的に制御（allow_refresh フラグ）して無限再帰を防止。
- .env 読み込み時に OS 環境変数を保護（protected セット）して上書きを制御。

Notes / マイグレーション / 使用上の注意
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須。Settings の対応プロパティ参照。
- DB 初期化
  - data/schema.init_schema(db_path) を呼んで DuckDB スキーマを作成してください（:memory: を指定するとインメモリ DB）。
  - 監査ログを追加で作成する場合は init_audit_schema(conn) または init_audit_db(db_path) を使用してください。
- ETL の実行
  - run_daily_etl(conn) を呼ぶとカレンダ・株価・財務の差分 ETL が実行され、品質チェックを含む結果が ETLResult として返されます。
- ロギング / 環境
  - KABUSYS_ENV と LOG_LEVEL は検証済みの値のみ受け付けます。不正値は ValueError を送出します。
- monitoring
  - __all__ に monitoring が含まれますが、現在 monitoring の実装は含まれていません。必要であれば別途実装を追加してください。

今後の予定（例）
- strategy 層に戦略実装（シグナル生成）を追加
- execution 層にブローカー API 統合（kabuステーション等）を実装
- monitoring / alerting 機能の追加（Slack 通知連携の活用）
- 品質チェックの拡張（重複・日付不整合・PL/BS の整合性チェック等）

---

参考: Keep a Changelog の簡潔なガイドラインに従い、各リリースには変更点をカテゴリ別（Added, Changed, Fixed, Removed, Security）で記載しています。必要に応じて日付・詳細を更新してください。