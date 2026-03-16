CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは「Keep a Changelog」方式に準拠しています。
バージョン番号は semver を使用します。

[0.1.0] - 2026-03-16
-------------------

追加
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - __version__ を "0.1.0" に設定
  - パッケージ公開モジュール: data, strategy, execution, monitoring

- 環境変数 / 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み実装（プロジェクトルートは .git または pyproject.toml で検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能
  - .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応
  - protected パラメータで OS 環境変数の上書きを保護
  - 必須環境変数取得ヘルパー (_require)
  - Settings クラスを実装（プロパティで設定を取得）
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID などを参照
    - DUCKDB_PATH、SQLITE_PATH のデフォルト値を提供（data/kabusys.duckdb, data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証ロジック
    - is_live / is_paper / is_dev のユーティリティプロパティ

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装（_request）
    - レート制御: 固定間隔スロットリングで 120 req/min を遵守（_RateLimiter）
    - 再試行ロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象
    - 401 応答時にリフレッシュトークンを使って id_token を自動再取得して 1 回のみ再試行
    - JSON デコードエラーやタイムアウトの扱いを明示
    - ページネーション対応（pagination_key を利用）
  - get_id_token 実装（リフレッシュトークン→IDトークン）
  - データ取得関数を追加
    - fetch_daily_quotes: 株価日足（OHLCV）
    - fetch_financial_statements: 財務データ（四半期 BS/PL）
    - fetch_market_calendar: JPX カレンダー
  - DuckDB に冪等保存する save_* 関数を実装（ON CONFLICT DO UPDATE）
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - fetched_at は UTC タイムスタンプで記録（Z 表記）
  - 型安全な変換ユーティリティ _to_float / _to_int（不正値は None）

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - 3 層（Raw / Processed / Feature）＋ Execution 層に基づく豊富な DDL を定義
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与
  - 多数のインデックスを定義してクエリパフォーマンスを考慮
  - init_schema(db_path) でディレクトリ自動作成・DDL 実行して接続を返す
  - get_connection(db_path) を提供（スキーマ初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - 全体設計: 差分更新・保存（冪等）・品質チェックのワークフローを実装
  - 定数・デフォルト
    - データ最小開始日: 2017-01-01
    - カレンダー先読み: 90 日
    - バックフィルデフォルト: 3 日
    - デフォルトスパイク閾値: 0.5 (50%)
  - ETLResult dataclass により結果と品質問題・エラーを集約
  - 差分判定ユーティリティ
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _get_max_date / _table_exists
  - 営業日調整ヘルパー _adjust_to_trading_day（market_calendar を参照し最大30日遡る）
  - 個別 ETL ジョブを提供
    - run_prices_etl（差分取得 + backfill）
    - run_financials_etl（差分取得 + backfill）
    - run_calendar_etl（最終取得日の翌日から target + lookahead まで取得）
  - メインエントリ run_daily_etl（カレンダー→価格→財務→品質チェックの順に実行）
    - 各ステップは独立して例外処理を行い、1 ステップ失敗でも他ステップを継続
    - id_token 注入可能でテスト容易性を確保

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - 信号・発注・約定レイヤの監査テーブルを定義
    - signal_events（戦略生成ログ）
    - order_requests（冪等キー: order_request_id、価格チェック制約含む）
    - executions（証券会社提供の約定IDをユニークキーとして保持）
  - 監査用インデックス群を定義（status / signal_id / broker_order_id など）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供
  - 全ての TIMESTAMP を UTC 保存するために接続時に SET TimeZone='UTC' を実行

- データ品質チェック (kabusys.data.quality)
  - QualityIssue dataclass を定義（check_name, table, severity, detail, rows）
  - 実装済みチェック
    - check_missing_data: raw_prices の OHLC 欠損検出（必須カラムの欠損は error）
    - check_spike: 前日比スパイク検出（LAG を使った SQL 実装、デフォルト閾値 50%）
  - 各チェックはサンプル行（最大 10 行）を返す。全問題を集める設計（Fail-Fast しない）
  - DuckDB 接続とパラメータバインド（?）を使用して効率・安全性を確保

変更
- なし（初回リリース）

修正
- なし（初回リリース）

削除
- なし（初回リリース）

既知の制限 / 注意点
- J-Quants API へのレート制御はモジュール内の固定 120 req/min を前提としている。用途により調整が必要な場合は _MIN_INTERVAL_SEC / _RateLimiter を変更すること。
- get_id_token は settings.jquants_refresh_token に依存するため、CI / テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD 等の制御が必要になる場合がある。
- DuckDB スキーマは比較的厳密な CHECK 制約を持つため、外部ソースの不正データにより挿入が失敗する可能性がある。ETL 側での前処理や quality モジュールでの検出後の対処が推奨される。
- 現在の品質チェック実装は raw_prices に焦点を当てている。news / executions 等の追加チェックは今後拡張可能。

今後の予定（想定）
- strategy / execution / monitoring 層の実装（現状はパッケージプレースホルダ）
- 品質チェックの拡張（重複チェック、日付不整合の検出等の追加）
- 監査ログに対する API（イベント挿入・検索）や運用向けユーティリティの追加
- テストの整備（単体テスト・統合テスト用のモック・フェイク実装）

---
参考: 必要な主な環境変数
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO

以上。