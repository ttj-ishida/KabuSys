# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
[https://keepachangelog.com/ja/1.0.0/](https://keepachangelog.com/ja/1.0.0/)

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買システムの基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージの初期化（src/kabusys/__init__.py）を追加。バージョンを "0.1.0" に設定し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定／環境変数管理
  - src/kabusys/config.py:
    - .env ファイルおよび環境変数から設定値を読み込む自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を探索して特定）。
    - .env のパースは export 付き行、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどを扱える堅牢な実装。
    - .env と .env.local の読み込み優先順位（OS 環境変数 > .env.local > .env）を実装。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを追加し、J-Quants / kabu ステーション / Slack / データベースパス / 実行環境（development/paper_trading/live）などをプロパティ経由で提供。値検証（例: KABUSYS_ENV や LOG_LEVEL の妥当性チェック）を実装。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py:
    - J-Quants API から株価（日足 OHLCV）、財務（四半期 BS/PL）、JPX 市場カレンダーを取得するクライアントを実装。
    - レート制限制御（120 req/min 固定間隔スロットリング）を導入する RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx にリトライ）を実装。429 時は Retry-After ヘッダを尊重。
    - 401 受信時はトークンを自動リフレッシュして 1 回だけ再試行（無限再帰防止）。
    - ID トークンのモジュールレベルキャッシュを導入し、ページネーション間で共有。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。
    - DuckDB に保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）は fetched_at を UTC で記録し、ON CONFLICT DO UPDATE による冪等性を確保。
    - データ変換ユーティリティ（_to_float, _to_int）実装。

- DuckDB スキーマ定義と初期化
  - src/kabusys/data/schema.py:
    - Raw / Processed / Feature / Execution 層にわたる包括的なテーブル定義（DDL）を追加。
    - 制約（PK, CHECK, FOREIGN KEY）や検索パターンを踏まえたインデックスを定義。
    - init_schema(db_path) によりディレクトリ自動作成を行いテーブルを冪等的に作成。get_connection() を提供。

- ETL パイプライン
  - src/kabusys/data/pipeline.py:
    - 日次 ETL のエントリポイント run_daily_etl を実装。処理は
      1. 市場カレンダー ETL（先読み）
      2. 株価日足 ETL（差分 + backfill）
      3. 財務データ ETL（差分 + backfill）
      4. 品質チェック
      の順で実行。各ステップは独立してエラーハンドリングされ、1 ステップ失敗でも他のステップは継続。
    - 差分更新ロジック（最終取得日を元に取得範囲を計算）、backfill_days による再取得、カレンダーを用いた営業日補正（_adjust_to_trading_day）を実装。
    - ETLResult dataclass により取得件数・保存件数・品質問題・エラーを集約して返却。
    - 個別ジョブ run_prices_etl / run_financials_etl / run_calendar_etl を実装。

- 監査ログ（トレーサビリティ）
  - src/kabusys/data/audit.py:
    - シグナル → 発注要求 → 約定に至る監査テーブル群（signal_events, order_requests, executions）を実装。
    - UUID 連鎖によるトレーサビリティ設計（order_request_id を冪等キーとして利用）。
    - 全ての TIMESTAMP を UTC で保存するための初期化（SET TimeZone='UTC'）を実行。
    - init_audit_schema(conn) / init_audit_db(db_path) を提供。

- データ品質チェック
  - src/kabusys/data/quality.py:
    - QualityIssue dataclass を実装し、品質チェック結果を構造化。
    - 欠損データ検出（check_missing_data: raw_prices の OHLC 欠損を検知）を実装。検出時はサンプル行を最大 10 件返却。
    - スパイク検知（check_spike: 前日比の変動率が閾値を超えるレコードを検知）を実装。ウィンドウ関数を使用して効率的に判定。
    - SQL はパラメータバインドを用いて実装し、効率性と安全性を配慮。

- その他
  - data パッケージ・submoduleの初期プレースホルダ（src/kabusys/data/__init__.py、strategy/__init__.py、execution/__init__.py）を追加。
  - ロギング出力を各所に追加（処理件数や警告・例外の記録）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- SQL 実行時にパラメータバインド（?）を使用してインジェクションリスクを低減。
- .env パースおよび自動読み込みは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）で、テストなど外部影響を抑制可能。

### Migration / Upgrade notes
- 初期化:
  - データベースを使用する前に data.schema.init_schema(db_path) を実行してスキーマを作成してください。
  - 監査ログを別 DB に分ける場合は data.audit.init_audit_db() を使用できます。
- 必要な環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）、KABU_API_PASSWORD（必須）、SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）。
  - その他、DUCKDB_PATH / SQLITE_PATH / KABUSYS_ENV / LOG_LEVEL にはデフォルトがあり、必要に応じて設定可能。
- .env の自動読み込みはプロジェクトルート検出（.git / pyproject.toml）に依存するため、配布した場合は必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を使い手動ロードすることを検討してください。

---

今後の予定（TODO/Planned）
- execution（発注連携）および strategy 層の具象実装（ブローカー連携、注文送信ロジック、ポートフォリオ管理など）。
- 追加の品質チェック（重複検出、将来日付検出など）の拡充。現在の実装は一部チェック（欠損・スパイク）を含みますが、設計文書に基づく残りのチェックを実装予定。
- テストカバレッジの拡充（特にネットワークエラー／リトライ・トークンリフレッシュ周り、ETL の差分ロジック）。

もし CHANGELOG に追加してほしい詳細やリリース日付の修正要望があれば教えてください。