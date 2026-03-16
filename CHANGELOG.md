# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」の形式に従います。

## [Unreleased]

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - package: kabusys（バージョン 0.1.0）
  - __all__ に data, strategy, execution, monitoring を公開（将来的なモジュール拡張を想定）

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の読み込み機能を実装
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 環境変数自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサーの強化（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等）
  - Settings クラスを導入し、必須設定の取得をメソッド化（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等）
  - env と log_level のバリデーション（許容値チェック）
  - duckdb/sqlite のデフォルトパス設定と Path 展開

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API からのデータ取得（株価日足 / 財務データ / JPX マーケットカレンダー）
  - レート制御: 固定間隔スロットリング実装（_RateLimiter、120 req/min）
  - リトライロジック: 指数バックオフ（最大 3 回）、408/429/5xx に対する再試行、429 の Retry-After ヘッダ対応
  - 認証更新: 401 受信時にリフレッシュトークンで id_token を自動更新して一回だけ再試行
  - id_token キャッシュをモジュールレベルで保持し、ページネーション間で共有
  - ページネーション対応（pagination_key を扱うループ）
  - 取得時に fetched_at を UTC ISO 形式で付与（Look-ahead Bias のトレーサビリティ確保）
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
    - 冪等性を考慮した INSERT ... ON CONFLICT DO UPDATE による保存
    - PK 欠損行のスキップとログ出力
    - 型安全な変換ユーティリティ（_to_float, _to_int）

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - 3 層（Raw / Processed / Feature）+ Execution レイヤーのテーブル定義を実装
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル
  - prices_daily, market_calendar, fundamentals 等の Processed テーブル
  - features, ai_scores 等の Feature テーブル
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル
  - 各種 CHECK 制約・PRIMARY KEY の指定によるデータ整合性
  - 頻出クエリを想定したインデックスを定義
  - init_schema(db_path) による初期化（親ディレクトリ自動作成、冪等）
  - get_connection(db_path) による接続取得（初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新を行う ETL 層の実装（run_prices_etl, run_financials_etl, run_calendar_etl）
    - DB の最終取得日から自動算出される date_from（バックフィル日数を指定可能）
    - run_calendar_etl は先読み（デフォルト 90 日）を行い、営業日判定に利用
    - run_prices_etl/run_financials_etl はデフォルトで backfill_days=3 を利用して後出し修正を吸収
  - 日次 ETL エントリポイント run_daily_etl を実装
    - カレンダー取得 → 営業日調整 → 株価ETL → 財務ETL → 品質チェック の順
    - 各ステップは独立して例外処理され、1 ステップ失敗でも残りを継続
    - ETLResult データクラスを返却し、取得件数・保存件数・品質問題・エラーログ等を集約

- 品質チェック (kabusys.data.quality)
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）
  - check_missing_data: raw_prices の OHLC 欠損検出（volume は許容）
  - check_spike: 前日比の急騰／急落（スパイク）検出（デフォルト閾値 50%）
  - 各チェックはサンプル行（最大 10 件）を返却し、Fail-Fast ではなく全件収集ポリシー

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - signal_events / order_requests / executions の監査テーブル定義を実装
  - 発注の冪等キー（order_request_id）や broker_execution_id の一意性確保
  - 全 TIMESTAMP を UTC で保存する設計（init_audit_schema は TimeZone='UTC' を設定）
  - ステータス列とチェック制約による状態遷移管理
  - init_audit_schema(conn) および init_audit_db(db_path) を提供

- 汎用ユーティリティ・設計面
  - 明示的なログ出力箇所（logger を使用）で動作状況を追跡可能
  - SQL 実行はパラメータバインドを基本とする（SQL インジェクション対策）
  - 型チェック・チェック制約を多用して DB 側での不正データ挿入を抑制

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 認証情報は環境変数（または .env）から取得する設計。トークンはメモリ内キャッシュで管理し自動リフレッシュを行うが、永続化は行わない。

### Notes / Breaking Changes
- 本バージョンは初回公開のため互換性の古いバージョンは存在しません。
- DuckDB のスキーマや制約に依存した実装が多いため、既存 DB を手動で修正した場合には init_schema による標準スキーマとの不整合が生じる可能性があります（初回は init_schema を使って DB を生成してください）。
- すべての TIMESTAMP は UTC を前提に実装しています。ローカルタイムでの運用には注意してください。

---

将来のリリースでは、strategy 層の実装、execution と monitoring の具体的なブローカー連携、より多様な品質検査・アラート、テスト用のモッククライアント等を追加予定です。