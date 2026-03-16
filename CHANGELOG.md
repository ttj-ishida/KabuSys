# Changelog

すべての注目すべき変更はこのファイルで管理します。  
フォーマットは「Keep a Changelog」準拠です。

## [0.1.0] - 2026-03-16
初回リリース。以下の主要コンポーネントと機能を追加しました。

### 追加 (Added)
- パッケージの基本構成
  - kabusys パッケージ初期化（バージョン: 0.1.0）と公開サブパッケージ定義（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装: 行のコメント、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ処理などに対応。
  - .env 読み込み時の上書き制御（override）と保護キー（protected）機能。
  - Settings クラスによるプロパティアクセス:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID の必須チェック（未設定時は ValueError）。
    - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH のデフォルト値。
    - KABUSYS_ENV（development, paper_trading, live の検証）と LOG_LEVEL の検証。
    - is_live / is_paper / is_dev のヘルパー。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得機能を実装。
  - レート制限対策: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter。
  - リトライロジック: 指数バックオフによる最大 3 回リトライ（408/429/5xx 対象）。429 の場合は Retry-After ヘッダを尊重。
  - 401 レスポンス時の自動トークンリフレッシュを 1 回だけ行う仕組み（無限再帰を回避）。
  - ページネーション対応（pagination_key を用いたフェッチのループ）。
  - 取得データに対して fetched_at を UTC で記録（Look-ahead Bias 対策のため）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等性を保証（ON CONFLICT DO UPDATE）。
  - 型変換ユーティリティ: _to_float, _to_int（空値や不正値を None に変換、"1.0" のような float 文字列に対する安全な int 変換など）。

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマを DDL で定義。
  - 代表的なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対する制約（主キー、チェック制約、外部キー）を定義。
  - 検索パフォーマンスを考慮したインデックスを定義。
  - init_schema(db_path) で DB ファイルの親ディレクトリ自動作成を行い、DDL を実行して接続を返す。
  - get_connection(db_path) により既存 DB への接続を取得可能（初回は init_schema を推奨）。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL のメインエントリ run_daily_etl を実装。
  - 処理フロー:
    1. 市場カレンダー ETL（先読み lookahead）
    2. 株価日足 ETL（差分更新 + backfill）
    3. 財務データ ETL（差分更新 + backfill）
    4. 品質チェック（オプション）
  - 差分更新ロジック: DB の最終取得日を基に自動で取得開始日を計算し、backfill_days による再取得で API 後出し修正を吸収。
  - 市場カレンダーは target_date より未来を先読みし、営業日調整に利用（_adjust_to_trading_day）。
  - 各ステップは独立したエラーハンドリング（1 ステップ失敗でも他は継続）。結果を ETLResult オブジェクトに収集（取得数、保存数、品質問題、エラー一覧など）。
  - ID トークン注入によりテスト容易性を確保。

- 品質チェックモジュール（kabusys.data.quality）
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - 実装済チェック（例）:
    - 欠損データ検出: raw_prices の OHLC 欠損検出（check_missing_data）。欠損があれば severity="error"。
    - スパイク検出: 前日比での急騰・急落検出（check_spike）。デフォルト閾値 50%。
  - 各チェックは問題を全件収集して QualityIssue リストを返す設計（Fail-Fast ではない）。
  - DuckDB 上の SQL を用いて効率的に検査。パラメータバインドを使用。

- 監査ログ / トレーサビリティ（kabusys.data.audit）
  - シグナル→発注→約定のトレーサビリティを記録する監査用テーブル群を定義。
  - テーブル:
    - signal_events（戦略が生成したシグナル。棄却やエラーも記録）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社からの約定ログ、broker_execution_id をユニークで保持）
  - init_audit_schema(conn) と init_audit_db(db_path) により監査用テーブルを初期化可能。
  - すべての TIMESTAMP を UTC で保存するように SET TimeZone='UTC' を実行。
  - 各テーブルにインデックスを追加して検索パフォーマンス向上。
  - 発注ロジック向けの拘束（limit/stop/market のチェック制約）を定義。
  - 監査ログは削除しない前提（ON DELETE RESTRICT など）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- （初回リリースのため該当なし）

注記:
- API 呼び出しや DB 書き込みでのエラーはログに記録し、ETLResult に集約されます。運用側でのモニタリング・アラート通知（例: Slack）は設定次第で組み合わせる想定です。
- 本 CHANGELOG はコードベースから推測して作成しています。実際の変更履歴（コミット単位やリリース手順）と差異がある可能性があります。必要であれば実際の VCS 履歴に基づいて更新してください。