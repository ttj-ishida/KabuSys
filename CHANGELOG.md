# CHANGELOG

すべての注記は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
この CHANGELOG は提示されたコードベースの内容から推測して作成しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-16
初期リリース。日本株自動売買システム (KabuSys) のコア機能群を実装。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - モジュール構成 (data, strategy, execution, monitoring) を定義。

- 設定 / 環境変数管理 (kabusys.config)
  - .env/.env.local からの自動読み込みを実装（プロジェクトルート判定は .git / pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント処理）。
  - OS 環境変数を保護する protected 機構（.env.local の上書き時に既存キーを保護）。
  - Settings クラスを提供し、以下のプロパティを取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - 環境種別 KABUSYS_ENV (development/paper_trading/live) の検証、LOG_LEVEL の検証
    - is_live / is_paper / is_dev ヘルパー

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API ベース URL とエンドポイントラッパーを実装。
  - レート制限 (120 req/min) 対応の固定間隔スロットリング実装（_RateLimiter）。
  - 冪等・堅牢な HTTP リトライロジックを追加（指数バックオフ、最大 3 回、ネットワーク/429/408/5xx のリトライ）。
  - 401 受信時にリフレッシュトークンで id_token を自動更新して 1 回再試行。
  - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有可、force_refresh 対応）。
  - JSON デコードエラー時の分かりやすいエラーメッセージ。
  - データ取得関数:
    - fetch_daily_quotes (ページネーション対応)
    - fetch_financial_statements (ページネーション対応)
    - fetch_market_calendar
  - DuckDB への保存関数（冪等性 / upsert 実装）:
    - save_daily_quotes: raw_prices テーブルへ保存（ON CONFLICT DO UPDATE）、fetched_at を UTC ISO8601 で付与
    - save_financial_statements: raw_financials へ保存（ON CONFLICT DO UPDATE）
    - save_market_calendar: market_calendar へ保存（ON CONFLICT DO UPDATE）
  - データ変換ユーティリティ:
    - _to_float / _to_int：入力の頑健なパース（空値や異常値処理、"1.0" のような float 文字列の取り扱い）

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - 3 層+実行層を想定したスキーマ定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・制約（CHECK、PRIMARY KEY、FOREIGN KEY）を設定。
  - 頻出クエリを見越したインデックスを定義。
  - init_schema(db_path) によるデータベース初期化（親ディレクトリ自動作成、:memory: サポート）。
  - get_connection(db_path) を用意（初期化済み接続を取得する既存DB向け）。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - シグナル→発注→約定を完全トレースする監査スキーマを実装:
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求ログ、order_request_id を冪等キーとして採用）
    - executions（証券会社約定ログ、broker_execution_id を冪等キー）
  - テーブル間の外部キー制約（ON DELETE RESTRICT など）を設定。
  - all TIMESTAMP は UTC 保存を明示（init_audit_schema で SET TimeZone='UTC' を実行）。
  - init_audit_schema(conn) による既存接続への追加初期化、init_audit_db(db_path) による監査専用 DB 初期化。
  - 監査用のインデックス群を定義（ステータス検索や broker_order_id 検索等の最適化）。

- データ品質チェック (kabusys.data.quality)
  - DataPlatform に基づく品質チェックを実装:
    - 欠損データ検出: check_missing_data（raw_prices の OHLC 欄）
    - 異常値検出: check_spike（前日比スパイク検出、デフォルト閾値 50%）
    - 重複チェック: check_duplicates（raw_prices の主キー重複検出）
    - 日付不整合検出: check_date_consistency（未来日付、market_calendar と非営業日の整合性検査）
  - 問題は QualityIssue データクラスで表現（check_name, table, severity, detail, rows のサンプル）。
  - run_all_checks() によりすべてのチェックを一括実行し、検出結果をまとめて返す。
  - 各チェックはサンプル行（最大 10 件）を返し、Fail-Fast ではなく全件収集方針を採用。

- その他
  - DuckDB への executemany / SQL 実行でのパラメータバインドを基本とした実装。
  - 多くの設計原則をドキュメント化（レート制限遵守、リトライ、ロギング、冪等性、UTC タイムスタンプ、監査ログの非削除方針、look-ahead bias 対策のための fetched_at 記録等）。
  - strategy、execution、monitoring のパッケージプレースホルダを用意（将来拡張を想定）。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の制約 / 注意事項
- 環境変数の必須キー (例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD) が未設定の場合、Settings のプロパティアクセス時に ValueError を発生させる。
- market_calendar テーブルが存在しない場合は日付整合性チェックの一部をスキップする設計（DuckDB エラーを吸収）。
- DuckDB の UNIQUE/NULL の扱いに依存したインデックス設計がある（例: broker_order_id の UNIQUE インデックス）。
- 実際のブローカー API 連携・発注処理はまだ実装範囲外（execution モジュールはプレースホルダ）。

-----

この CHANGELOG はコードから推測して作成しています。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。必要であれば、各機能ごとにさらに細かい変更点や想定される使用例・注意点を追加して拡張できます。