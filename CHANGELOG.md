# CHANGELOG

すべての注目すべき変更を記録します。本ドキュメントは「Keep a Changelog」規約に準拠しています。

全般: 初期リリースとして、データ取得・ETL・スキーマ・監査ログ・環境設定・品質チェックを備えた日本株自動売買向けのライブラリを提供します。

## [0.1.0] - 2026-03-16

### 追加
- パッケージ基盤
  - kabusys パッケージを追加。パッケージメタ情報として __version__ = "0.1.0" を定義し、公開モジュールとして data, strategy, execution, monitoring を列挙。
- 環境設定 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env 行パーサーを実装。`export KEY=val`、シングル/ダブルクォート、エスケープ、コメント扱い（スペース直前の # をコメントとして処理）に対応。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD の追加（テスト用途）。
  - 環境変数読み取りとバリデーションを行う Settings クラスを追加（必須値チェック _require、KABUSYS_ENV / LOG_LEVEL の検証、パスの Path 化等）。
  - J-Quants / kabuAPI / Slack / DB パス等の設定プロパティを提供。
- J-Quants クライアント (kabusys.data.jquants_client)
  - 基本機能: 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する API クライアントを実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を尊重する RateLimiter を実装。
  - 再試行ロジック: 指数バックオフ、最大 3 回のリトライ、408/429/5xx を再試行対象に設定。429 の場合は Retry-After ヘッダを優先。
  - トークン管理: get_id_token による ID トークン取得、401 受信時に自動リフレッシュして 1 回リトライする仕組み（再帰防止フラグあり）。ページネーション間で共有するモジュールレベルのトークンキャッシュ。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - 保存関数: DuckDB に対する冪等な保存処理（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による上書き、fetched_at を UTC ISO8601 で記録、PK 欠損行のスキップとログ。
  - ユーティリティ: 型変換関数 _to_float / _to_int（変換失敗時に None を返す、安全な float→int 変換ルール等）。
- DuckDB スキーマ (kabusys.data.schema)
  - Raw / Processed / Feature / Execution レイヤーに渡る包括的なテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 各テーブルの制約（PRIMARY KEY, CHECK 等）を定義し、よく使うクエリパターン向けにインデックスを作成。
  - init_schema(db_path) による冪等な初期化、get_connection(db_path) による接続取得を提供。db_path の親ディレクトリ自動作成に対応。":memory:" のサポート。
- ETL パイプライン (kabusys.data.pipeline)
  - run_daily_etl を中心に、差分更新（最終取得日からの backfill）、市場カレンダーの先読み、株価/財務データの差分取得・保存、品質チェックの一連処理を実装。
  - run_prices_etl / run_financials_etl / run_calendar_etl を個別に呼べるように実装（idempotent、ページネーション、backfill_days デフォルト 3 日、calendar lookahead デフォルト 90 日）。
  - 市場カレンダーを先に取得し、非営業日を直近営業日に調整する _adjust_to_trading_day を実装。
  - ETLResult データクラスを導入し、取得件数・保存件数・品質問題・エラーを集約。品質問題は詳細 (check_name, severity, message, sample rows) に変換可能。
  - ETL の各ステップは独立して例外処理され、1ステップ失敗でも他ステップは継続（全問題収集型の設計）。
- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - 戦略→シグナル→発注要求→証券会社約定までの UUID 連鎖で完全トレース可能な監査テーブル群を追加（signal_events, order_requests, executions）。
  - order_request_id を冪等キーとすることで二重発注防止を想定。すべての TIMESTAMP を UTC で保存するため init_audit_schema は SET TimeZone='UTC' を実行。
  - 注文種別ごとの CHECK 制約（limit/stop/market に応じた価格必須性）やステータス遷移定義を含むスキーマ。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。監査用インデックスも作成。
- データ品質チェック (kabusys.data.quality)
  - 欠損データ検出（OHLC 欠損）、スパイク検出（前日比の絶対変動 > threshold、デフォルト 50%）、主キー重複、日付不整合検出のための土台を実装。
  - QualityIssue データクラスを用いて、チェック結果（check_name, table, severity, detail, rows）を返す設計。DuckDB 上の SQL で効率的に処理。
  - 各チェックは Fail-Fast ではなく問題を全件収集して返す（呼び出し元が重大度に応じて判断）。
  - check_missing_data, check_spike 等の実装（サンプル行最大 10 件取得）。
- パッケージ公開 API
  - settings（kabusys.config.Settings のインスタンス）を通じた設定取得。
  - data.schema.init_schema / get_connection、data.audit.init_audit_schema / init_audit_db、data.jquants_client の fetch_* / save_* / get_id_token、data.pipeline.run_daily_etl など主要機能を利用可能。

### 変更
- 初期リリースのため変更履歴はありません。

### 修正
- 初期リリースのため修正履歴はありません。

### 既知の注意点（ドキュメント）
- J-Quants API のレート制限は固定間隔スロットリングで守る設計だが、外部で長時間ブロッキングが発生するとスループットに影響する可能性あり。
- DuckDB の制約やインデックスは想定されるクエリパターンに基づく。運用環境での大規模データ時はパフォーマンス調整が必要。
- quality モジュールは主要チェックを実装しているが、さらに高度な品質ルール（例えば連続欠損や時系列ノイズ補正）は今後追加可能。

### セキュリティ
- トークン・資格情報は環境変数経由で取得する設計。`.env.local` は OS 環境変数を保護しつつ上書き可能にしているが、本番環境では OS 環境変数やシークレットマネージャの利用を推奨。

---

今後のリリースでは、戦略実装例、order execution の kabu ステーション連携、監視（monitoring）や Slack 通知の実装、より多様な品質チェックの追加を予定しています。