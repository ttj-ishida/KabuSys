Changelog
=========
全ての注目すべき変更点をこのファイルに記載します。
フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
-------------

## [0.1.0] - 2026-03-16
初期リリース。日本株自動売買システム「KabuSys」の基盤モジュール群を実装しました。

### Added
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは 0.1.0。公開 API に data, strategy, execution, monitoring を含む。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により、CWD に依存しない .env ロードを実現。
  - .env のパース機能を強化（export プレフィックス対応、クォート・エスケープ処理、インラインコメントの扱い）。
  - .env の上書き制御（.env → .env.local、OS 環境変数保護）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルなどをプロパティ経由で取得可能に。
  - env と log_level の入力検証（許容値チェック）を実装。

- データクライアント：J-Quants (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - API レート制御（固定間隔スロットリング）を実装し、120 req/min を遵守。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。対象はネットワーク系エラーおよび 408/429/5xx。
  - 401 Unauthorized 受信時はリフレッシュトークンを用いて自動的に id_token を再取得して 1 回リトライ（無限再帰防止の仕組みあり）。
  - ページネーション対応で fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を提供。
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias 対策を設計に反映。
  - DuckDB へ保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を確保。
  - id_token のモジュールレベルキャッシュ（ページネーション間で共有）を実装し、テストしやすいよう id_token 注入をサポート。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の多層データレイヤー向けテーブル定義を実装。
  - raw_prices / raw_financials / raw_news / raw_executions などの Raw テーブル。
  - prices_daily / market_calendar / fundamentals / news_articles / news_symbols などの Processed テーブル。
  - features / ai_scores などの Feature テーブル。
  - signals / signal_queue / orders / trades / positions / portfolio_performance / portfolio_targets などの Execution テーブル。
  - 頻出クエリ向けインデックス群を定義。
  - init_schema(db_path) で DB ファイルの親ディレクトリ自動作成と全テーブル・インデックス作成（冪等）を提供。
  - get_connection(db_path) により既存 DB への接続を返すユーティリティを実装。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL の総合エントリ run_daily_etl を実装。処理はカレンダー→株価→財務→品質チェックの順で実行。
  - 差分更新ロジックを実装（DB の最終取得日を参照し未取得分のみ取得）。バックフィル期間(backfill_days)による後出し修正吸収をサポート。
  - 市場カレンダーは lookahead で将来日を先読みして営業日調整に利用。
  - 各 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）は独立してエラーハンドリングし、1 ステップ失敗でも他ステップを継続。
  - ETL 結果を集約する ETLResult データクラスを導入（取得数、保存数、品質問題、エラー一覧などを保持）。to_dict により監査ログ等にシリアライズ可能。
  - 品質チェックモジュールとの連携フラグを実装（run_quality_checks）。

- 品質チェック (kabusys.data.quality)
  - DataPlatform 設計に基づく品質チェック基盤を実装。
  - QualityIssue データクラスを追加（check_name, table, severity, detail, sample rows）。
  - 欠損データ検出（open/high/low/close の NULL 検出）を実装（check_missing_data）。
  - スパイク検出（前日比の変化率が閾値を超えるレコード）を実装（check_spike）。閾値はデフォルト 50%。
  - 各チェックは DuckDB SQL を用いて実行し、問題のサンプルと件数を返す設計。Fail-Fast ではなく全件収集を行う。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - シグナル → 発注要求 → 約定の完全トレーサビリティを目的とした監査テーブルを実装。
  - signal_events / order_requests / executions テーブルを定義。order_request_id を冪等キーとして扱う設計。
  - 各テーブルに created_at / updated_at を付与。TIMESTAMP は UTC 保存を前提（init_audit_schema は SET TimeZone='UTC' を実行）。
  - 監査用インデックス群を実装（status / date/code / broker_id などでの高速検索を想定）。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供。

- 設計上の考慮点・利便性
  - SQL インジェクション対策としてパラメータバインド（?）を利用する方針を採用。
  - fetch/save 関数での冪等性設計（ON CONFLICT DO UPDATE）により再実行が安全。
  - テスト容易性を考慮し、id_token 等を外部注入可能に設計。
  - ログ出力とエラー収集を重視し、ETLResult や logger による可観測性を提供。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Known issues / Notes
- strategy と execution パッケージはパッケージ空ディレクトリとして存在します（戦略ロジック・注文送信ロジックは今後実装予定）。
- 品質チェックの設計書では重複チェック・日付不整合チェックも記載されていますが、現状では欠損検出とスパイク検出が実装済みです。その他のチェックは今後追加予定です。
- J-Quants クライアントの HTTP 呼び出しは urllib を用いて実装しており、ユーザのニーズに応じて非同期化や requests 等への差し替えを検討可能です。
- DuckDB スキーマには多くの制約・チェックを含みます。既存データとの互換性が必要な場合はマイグレーション手順が別途必要になります。

Notes for Upgrading
- 初回導入時は data.schema.init_schema()（または init_audit_db/init_audit_schema）を実行して DB を初期化してください。
- 環境変数は .env/.env.local を用いることを推奨します。既存 OS 環境変数はデフォルトで保護されます。

(以上)