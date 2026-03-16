# Changelog

すべての変更履歴は Keep a Changelog の形式に準拠します。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-16

### Added
- パッケージ初版を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py に定義）
  - エクスポート: data, strategy, execution, monitoring

- 環境設定モジュール（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む機能を実装
  - プロジェクトルート検出: __file__ を起点に親ディレクトリから .git または pyproject.toml を探索してルートを特定
  - 自動ロード順序: OS環境変数 > .env.local > .env（.env.local は .env を上書き）
  - 自動ロードの無効化環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサーの実装（export 形式、クォート・エスケープ、インラインコメント処理）
  - 環境変数保護機能（OS 環境変数は protected として上書きを防止）
  - Settings クラス（settings インスタンス提供）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須取得（未設定時は ValueError）
    - KABU_API_BASE_URL のデフォルト: http://localhost:18080/kabusapi
    - DB パスのデフォルト: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db
    - KABUSYS_ENV 検証（development, paper_trading, live）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live/is_paper/is_dev

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 基本機能:
    - ベース URL: https://api.jquants.com/v1
    - レート制限: 120 req/min を固定間隔スロットリングで順守（_RateLimiter）
    - リトライ: 最大 3 回、指数バックオフ（base=2.0 秒）
    - 再試行対象ステータス: 408, 429, 5xx
    - 429 の場合は Retry-After ヘッダを優先
    - 401 受信時は id_token を自動でリフレッシュして 1 回のみリトライ（無限再帰防止）
    - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）
  - データ取得関数（ページネーション対応）
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存（冪等操作）
    - save_daily_quotes: raw_prices テーブルに ON CONFLICT DO UPDATE で保存
    - save_financial_statements: raw_financials テーブルに ON CONFLICT DO UPDATE で保存
    - save_market_calendar: market_calendar テーブルに ON CONFLICT DO UPDATE で保存
  - データ整形ユーティリティ
    - _to_float / _to_int: 型安全な変換（空値や不正値は None）
  - ログ出力ポイント（取得件数や警告）

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - DataPlatform に基づいた 3 層構造のテーブルを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約・CHECK・PRIMARY KEY を設定
  - インデックス（頻出クエリを想定したインデックス）を作成
  - 公開 API:
    - init_schema(db_path) : テーブル・インデックスを作成して接続を返す（親ディレクトリ自動作成、冪等）
    - get_connection(db_path) : 既存 DB へ接続（スキーマ初期化は行わない）

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL を実装（差分取得・保存・品質チェック）
  - 主な機能:
    - 差分更新ロジック: DB の最終取得日を基に未取得分のみを取得。バックフィル日数(backfill_days)により数日前から再取得し API の後出し修正を吸収（デフォルト backfill_days=3）
    - カレンダー先読み: デフォルト 90 日の先読みで market_calendar を取得（calendar_lookahead_days=90）
    - run_prices_etl / run_financials_etl / run_calendar_etl を個別に実行可能
    - run_daily_etl: 1つのエントリでカレンダー→株価→財務→品質チェックを順次実行
    - ETLResult dataclass により取得件数・保存件数・品質問題・エラーを収集して返却
    - エラーハンドリング: 各ステップは独立して例外処理を行い、1ステップの失敗が他ステップを中断しない設計（Fail-Fast ではなく全件収集）
    - 市場日調整: カレンダーを用いて target_date を直近の営業日に調整（最大 30 日遡る）
    - デフォルト最小データ日: 2017-01-01（初回ロードの下限）

- 監査ログ（audit）モジュール（src/kabusys/data/audit.py）
  - シグナル→発注→約定までを UUID 連鎖でトレースする監査テーブルを定義
  - テーブル:
    - signal_events（戦略が生成したシグナルのログ）
    - order_requests（発注要求。order_request_id を冪等キーとして扱う）
    - executions（証券会社からの約定ログ。broker_execution_id をユニーク冪等キー）
  - 制約とチェックを厳密に設定（order_type と価格の整合性チェック等）
  - すべての TIMESTAMP を UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）
  - インデックスを作成（ステータス検索、JOIN、broker_order_id 検索等）
  - 公開 API:
    - init_audit_schema(conn)
    - init_audit_db(db_path)

- データ品質チェック（src/kabusys/data/quality.py）
  - チェック項目:
    - 欠損データ検出: raw_prices の OHLC 欄の欠損を検出（check_missing_data）
    - 異常値（スパイク）検出: 前日比 ±X% を超える変動を検出（check_spike、デフォルト閾値 50%）
    - （設計に重複チェック・日付不整合検出も明記。実装は拡張可能）
  - QualityIssue dataclass により、チェック名・テーブル・重大度（error|warning）・詳細・サンプル行を返却
  - DuckDB 上で SQL を用いた効率的な検査（パラメータバインド使用）
  - pipeline.run_daily_etl から呼び出し、重大度に応じた判定が可能

### Changed
- 初版リリースのため該当なし

### Fixed
- 初版リリースのため該当なし

### Notes / Implementation details
- API 呼び出しのレート制御は固定間隔スロットリング方式（最小間隔 = 60 / 120 秒）で実装。バーストは許容しない想定。
- リトライはネットワーク・サーバエラー耐性を考慮（408/429/5xx/URLError/OSError）し、最大 3 回まで指数バックオフで試行。
- 401 エラー時は refresh token を使って id_token を再取得し 1 回リトライするロジックを実装（get_id_token 呼び出しからの再帰を防止）。
- DuckDB スキーマは冪等（CREATE IF NOT EXISTS / ON CONFLICT / インデックス IF NOT EXISTS）で初期化を行うため、既存データを保持したままスキーマ追加・更新が可能。
- 監査ログは原則削除しない方針（FK は ON DELETE RESTRICT）、updated_at はアプリ側で設定する設計。
- quality.check_spike は LAG ウィンドウを用いて前日 close を取得し変動率を計算している（閾値デフォルト 0.5）。

---

今後の予定（例）
- strategy / execution モジュールの具体的な実装（発注連携、ブローカーアダプタ等）
- 追加の品質チェック（重複検出、将来日付チェックなど）とより詳細な監査メタデータ
- 単体テスト・統合テストの整備、CI ワークフローの追加

もし CHANGELOG に特に盛り込みたい点（例: 重要な設計判断や既知の制限）があれば教えてください。必要に応じて項目を追記・調整します。