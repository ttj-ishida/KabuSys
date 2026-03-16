# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-16
初期リリース — 日本株自動売買システムのコアライブラリを導入。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージの初期モジュールを追加（data, strategy, execution, monitoring を __all__ に公開）。
  - バージョン: __version__ = "0.1.0"。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート（テスト用途）。
  - .env パーサー (_parse_env_line): コメント・export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープ等を考慮してパース。
  - .env 読み込み時の保護キー機能（OS 環境変数を protected として上書き回避）。
  - Settings クラスを導入し、主要設定をプロパティ経由で提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live 検証）および LOG_LEVEL 検証
    - is_live / is_paper / is_dev ヘルパー

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリングを実装（_RateLimiter）。
  - 冪等性・堅牢性:
    - 最大リトライ回数（3回）、指数バックオフ、408/429/5xx に対するリトライ実装。
    - 401 受信時にリフレッシュトークンで id_token を自動更新して 1 回だけリトライする仕組み。
    - ページネーション対応（pagination_key の追跡）。
    - id_token のモジュールレベルキャッシュを共有（ページネーション間の再利用）。
  - 取得 API:
    - fetch_daily_quotes（株価日足 OHLCV、ページネーション対応）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - 保存関数（DuckDB 連携、冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE を利用して重複を排除・上書き
    - fetched_at を UTC ISO 形式で記録し、Look-ahead バイアスを追跡可能に
  - ユーティリティ:
    - _to_float / _to_int: 空値や変換失敗を None とし、int 変換は小数部が 0 の場合のみ許容

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用の包括的なスキーマを追加（Raw / Processed / Feature / Execution 層）。
  - Raw テーブル: raw_prices, raw_financials, raw_news, raw_executions
  - Processed テーブル: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature テーブル: features, ai_scores
  - Execution テーブル: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 頻出クエリ向けインデックス群を定義
  - init_schema(db_path) でディレクトリ自動作成→DDL 実行、get_connection() を提供

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL の統合入口 run_daily_etl を実装（マーケットカレンダー取得 → 株価 ETL → 財務 ETL → 品質チェックの順）。
  - 個別 ETL ジョブ:
    - run_calendar_etl（デフォルト先読み 90 日）
    - run_prices_etl（デフォルトバックフィル 3 日、差分更新ロジック）
    - run_financials_etl（差分更新 + バックフィル）
  - 差分取得ヘルパー:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _adjust_to_trading_day: 非営業日は直近の過去営業日に調整（market_calendar を参照）
  - ETLResult データクラスで実行結果（取得/保存件数、品質問題、エラー）を集約
  - 品質チェックはオプションで run_quality_checks により実行可能

- 監査ログ（トレーサビリティ）(kabusys.data.audit)
  - 戦略→シグナル→発注要求→約定のトレーサビリティを保持する監査スキーマを実装
  - テーブル: signal_events, order_requests (冪等キー: order_request_id), executions（broker_execution_id はユニーク）
  - すべての TIMESTAMP を UTC とする（init_audit_schema で TimeZone='UTC' を設定）
  - インデックスを実装（status でのスキャン、signal_id/日付による検索など）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供

- データ品質チェック (kabusys.data.quality)
  - QualityIssue データクラスで問題を表現（check_name, table, severity, detail, rows）
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（severity=error）
    - check_spike: 前日比スパイク検出（デフォルト閾値 0.5 = 50%）
  - 各チェックはサンプル行（最大 10 件）と件数を返し、Fail-Fast を行わず全件収集する設計
  - DuckDB 上で効率的に SQL による検査を実行（パラメータバインド使用）

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 注意事項 (Notes)
- デフォルトの J-Quants レート制限: 120 req/min（_MIN_INTERVAL_SEC に基づく固定間隔スロットリング）。
- リトライ挙動:
  - ネットワークエラーや 408/429/5xx で最大 3 回リトライ（指数バックオフ）。
  - 401 は一度だけトークンをリフレッシュして再試行。再度 401 が返る場合は失敗。
- DuckDB への保存は ON CONFLICT DO UPDATE を使い冪等性を確保。
- .env のパースは実用上の多くのケースをカバーするが、特殊なフォーマットは未対応の可能性あり。
- audit テーブルは削除を前提としない（FK は ON DELETE RESTRICT）。監査ログは原則削除しない設計。

### 既知の制限 / 今後対応予定
- strategy, execution, monitoring パッケージは名前空間を確保しているが、詳細実装は今後追加予定。
- DB マイグレーションやバージョン管理機構（スキーママイグレーションツール）は未導入。スキーマ変更は手動または次版で検討予定。
- 複数プロセスから同時に J-Quants リクエストを行う場合のグローバルなレート制御（プロセス間共有トークンや分散レート制御）は現状非対応。

---

（この CHANGELOG はコード内容から推測して作成しています。正確なユーザー向け変更履歴は実際のコミット履歴・リリースノートに基づいて更新してください。）