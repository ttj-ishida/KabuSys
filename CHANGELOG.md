# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]


## [0.1.0] - 2026-03-16

初期リリース

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring
  - バージョン: 0.1.0

- 環境設定モジュール（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - .env パーサを実装（コメント、export 形式、シングル/ダブルクォート、エスケープ対応、インラインコメント処理のルールを含む）。
  - Settings クラスでアプリ設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスあり、~展開）
    - KABUSYS_ENV 検証（development / paper_trading / live のみ許容）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の便宜プロパティ

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本機能:
    - ID トークン取得（get_id_token）
    - 日足株価取得（fetch_daily_quotes）/ 財務諸表取得（fetch_financial_statements）/ マーケットカレンダー取得（fetch_market_calendar）
    - ページネーション対応（pagination_key を用いた取得）
  - レート制御:
    - 固定間隔スロットリングで 120 req/min 制限に対応（RateLimiter 実装）
  - 再試行ロジック:
    - 指数バックオフで最大 3 回リトライ（ネットワークエラー、HTTP 408/429/5xx 対象）
    - 429 時は Retry-After ヘッダを優先
    - 401 認証エラー時はトークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止のため allow_refresh フラグ）
  - モジュールレベルで ID トークンをキャッシュし、ページネーション間で共有
  - データ取得時に fetched_at を UTC タイムスタンプ（Z）で付与する設計方針を採用（DuckDB 保存時に利用）
  - データ整形ユーティリティ:
    - _to_float / _to_int（空値や不正な文字列を安全に None にするロジック、"1.0" などの float 文字列処理や小数部の切捨て回避）

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - 3 層データレイヤ設計を実装（Raw / Processed / Feature / Execution）
  - Raw レイヤ:
    - raw_prices, raw_financials, raw_news, raw_executions テーブル定義（主キー・チェック制約付き）
  - Processed レイヤ:
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature レイヤ:
    - features, ai_scores
  - Execution レイヤ:
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 頻出クエリ向けのインデックス定義（複数）
  - init_schema(db_path) によりディレクトリ自動作成（必要時）と冪等的に全テーブル／インデックス作成を実行
  - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない）

- 監査（Audit）スキーマ（kabusys.data.audit）
  - 監査ログ用テーブルを別モジュールで定義・初期化:
    - signal_events（シグナル生成ログ、ステータス/理由含む）
    - order_requests（発注要求、order_request_id を冪等キーとして扱う）
    - executions（証券会社からの約定ログ、broker_execution_id をユニーク冪等キー）
  - 監査初期化関数:
    - init_audit_schema(conn)（渡された DuckDB 接続に監査テーブルを追加。SET TimeZone='UTC' を実行）
    - init_audit_db(db_path)（監査専用 DB の作成と初期化）
  - 外部キーとチェック制約により削除不可（ON DELETE RESTRICT）を基本とした設計
  - インデックスを多数作成し検索性能を考慮

- データ品質チェックモジュール（kabusys.data.quality）
  - QualityIssue データクラスを導入（check_name, table, severity, detail, sample rows）
  - チェック実装:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は対象外）
    - check_spike: 前日比のスパイク検出（デフォルト閾値 50%）
    - check_duplicates: raw_prices の主キー重複チェック
    - check_date_consistency: 将来日付・market_calendar との整合性検出（非営業日のデータ）
  - run_all_checks で全チェックをまとめて実行し、エラー/警告をログ出力
  - 各チェックは Fail-Fast ではなく全問題を収集して返す設計

- その他
  - ロギング用の logger 呼び出しを随所に追加（情報、警告、エラーの出力）
  - 各モジュールの設計ドキュメント（docstring）に設計方針・注意点を明記
  - strategy/ execution/ monitoring パッケージのプレースホルダ（__init__.py）は存在するが具体実装はなし（今後の拡張ポイント）

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Security
- 認証トークンの自動リフレッシュやキャッシュの仕組みにより、401 ハンドリングを安全に行うように設計。ただしトークンの保護は環境変数管理に依存（.env ファイルの取扱いに注意）。

---

注:
- これはパッケージ内容から推測した変更履歴（初期リリースの記録）です。実際のリリースノートやユーザー向けドキュメントは必要に応じて補足してください。