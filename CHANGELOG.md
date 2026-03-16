# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
フォーマット: https://keepachangelog.com/ja/

現在のバージョン: 0.1.0 (初回リリース)

## [0.1.0] - 2026-03-16

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基礎コンポーネントを追加。
  - src/kabusys/__init__.py
    - パッケージのバージョン（0.1.0）と公開モジュールを定義。

- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途）。
  - .env パーサーは以下に対応:
    - `export KEY=val` 形式
    - シングル/ダブルクォート文字列（バックスラッシュによるエスケープ対応）
    - インラインコメント（クォート外・前がスペース/タブの場合）
  - Settings クラス: J-Quants / kabu / Slack / DB パス等のプロパティを提供（必須設定は未設定時 ValueError を発生）。
  - 環境値検証: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL の検証を実装。
  - デフォルト DB パス: DuckDB = data/kabusys.duckdb、SQLite = data/monitoring.db。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）
  - API から次を取得する関数を提供:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務四半期データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - 認証ユーティリティ: get_id_token（リフレッシュトークン経由で id_token を取得）。
  - レート制限制御: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter を実装。
  - リトライロジック: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx をリトライ対象に設定。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時は id_token を自動リフレッシュして 1 回だけリトライ（無限再帰防止ロジックあり）。
  - トークンのモジュールレベルキャッシュを実装（ページネーション間で共有）。
  - データ保存ユーティリティ（DuckDB を使用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 保存は冪等性を担保（ON CONFLICT DO UPDATE を利用）
    - 主キー欠損レコードはスキップし警告ログを出力
    - fetched_at を UTC で記録（Look-ahead Bias トレーサビリティ）
  - 型変換ユーティリティ: _to_float / _to_int（安全な変換と不正値の None 返却）

- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）
  - 3 層構造（Raw / Processed / Feature）および Execution レイヤー、監査テーブル用のDDL を定義。
  - テーブル群の一覧（例: raw_prices, raw_financials, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance, news_articles, news_symbols など）を作成。
  - 各種制約（PK/チェック制約/外部キー）と利用を想定したインデックスを定義。
  - 公開 API:
    - init_schema(db_path) — DB ファイルを作成（親ディレクトリ自動作成）し全テーブルを作成（冪等）。
    - get_connection(db_path) — 既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプラインモジュールを追加（src/kabusys/data/pipeline.py）
  - 日次 ETL の実装:
    - run_prices_etl（差分取得 + backfill）
    - run_financials_etl（差分取得 + backfill）
    - run_calendar_etl（先読み取得）
    - run_daily_etl（市場カレンダー → 株価 → 財務 → 品質チェック の一連処理）
  - 差分更新ロジック: DB の最終取得日から未取得分のみを取得。バックフィルは既定で 3 日（後出し修正を吸収）。
  - カレンダーは先読み（デフォルト 90 日）して当日の営業日調整に利用。
  - ETLResult データクラスを導入し、取得/保存数・品質問題・エラーを集約して返す。
  - 各ステップは独立してエラーハンドリング（1 ステップ失敗でも他は継続）し、エラーメッセージを収集。

- 監査ログ（トレーサビリティ）モジュールを追加（src/kabusys/data/audit.py）
  - 監査用テーブル群（signal_events, order_requests, executions）を定義。
  - 設計: UUID 連鎖によるシグナル→発注→約定の完全トレース、order_request_id による冪等性、created_at／updated_at の保持、UTC 時刻保存を前提。
  - init_audit_schema(conn) — 既存 DuckDB 接続に監査テーブルを追加。
  - init_audit_db(db_path) — 監査専用 DB を初期化して接続を返す。
  - インデックスと制約を多数定義し検索性能・整合性を考慮。

- データ品質チェックモジュールを追加（src/kabusys/data/quality.py）
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（重大度: error）
    - check_spike: 前日比スパイク検出（閾値デフォルト 50%）
  - 設計上は重複チェック・日付不整合検出なども想定（SQL ベース、パラメータバインドで実行）。
  - run_all_checks を呼び出す形で pipeline から統合（pipeline 側で呼び出し・収集）。

- モジュール薄レイヤー追加（placeholder パッケージ）
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py を追加（将来的な機能拡張場所を確保）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- .env 自動ロード時に既存の OS 環境変数を保護する仕組みを導入（protected set）。  
- J-Quants 認証トークンの自動リフレッシュは慎重に 1 回のみ実行し、無限再帰を防止。

### Notes / Migration
- DB 初期化:
  - 初回は data.schema.init_schema(db_path) を実行してスキーマを作成してください。既存 DB に対しては冪等に動作します。
  - 監査テーブルを別 DB に分離したい場合は init_audit_db を利用できます。既存接続に追加する場合は init_audit_schema(conn) を利用してください。
- .env 読み込み:
  - プロジェクトルートが検出できない場合は自動ロードをスキップします（配布後の動作を安定させるため）。
  - 自動読み込みを抑止したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API 使用上の注意:
  - レート制限 120 req/min を超えないよう内部で待機します。大量データ取得時は処理時間が伸びます。
  - API からのページネーションは `pagination_key` によって処理されます。
- 品質チェック:
  - pipeline のデフォルトは品質チェックを実行しますが、run_daily_etl の引数 `run_quality_checks=False` で無効化可能。
  - 現状実装されているチェックは欠損とスパイクで、仕様上は重複や日付不整合の検出も想定されています。必要に応じて追加実装してください。
- ログ・監査:
  - audit.init_audit_schema は接続時に "SET TimeZone='UTC'" を実行し、すべての TIMESTAMP を UTC 保存することを前提にしています。

---

今後の予定（TODO / 予定機能）
- strategy / execution 層の本格実装（シグナル生成ロジック、発注実行エンジン、ブローカー連携）
- quality モジュールの追加チェック（重複・日付不整合）の実装
- CLI / ジョブスケジューラ統合、監視用ダッシュボード、Slack 通知連携の実装
- テストカバレッジ強化（特にネットワークリトライ、トークンリフレッシュ、ETL の境界条件）

以上。