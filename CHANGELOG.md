# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、Semantic Versioning を採用します。
<!-- 参考: https://keepachangelog.com/ja/1.0.0/ -->

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システムのコアライブラリを実装しました。主に以下の機能を含みます。

### 追加
- パッケージ基盤
  - パッケージルート: kabusys（__version__ = 0.1.0）。
  - サブパッケージスケルトン: data, strategy, execution, monitoring。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索（__file__ ベース）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - OS 環境変数は保護され、.env で上書きされない。
    - .env.local は override=True のため .env を上書き可能（ただし OS 環境変数は保護）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト用途）。
  - .env パーサーは export KEY=val、シングル/ダブルクォート、エスケープ、コメント処理等に対応。
  - Settings クラスを提供し、アプリケーション設定をプロパティとして取得可能。
    - 必須環境変数取得時は未設定で ValueError を送出（_require）。
    - サポートされる主要設定例:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（デフォルト: development、許容値: development, paper_trading, live）
      - LOG_LEVEL（デフォルト: INFO、許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 対応データ:
    - 株価日足（OHLCV）：fetch_daily_quotes
    - 財務データ（四半期 BS/PL）：fetch_financial_statements
    - JPX マーケットカレンダー：fetch_market_calendar
  - レート制限遵守:
    - 固定間隔スロットリング実装（_RateLimiter）で 120 req/min を保証（min interval = 60/120 秒）。
  - リトライとエラーハンドリング:
    - 指数バックオフ付きリトライ（最大 3 回、対象 HTTP ステータス 408, 429 および 5xx）。
    - 429 の場合は Retry-After ヘッダを優先して待機。
    - ネットワークエラーや URLError もリトライ対象。
  - 認証トークン処理:
    - ID トークンをモジュールレベルでキャッシュ（ページネーション間で共有）。
    - 401 受信時は自動でリフレッシュ（1 回のみ）して再試行。
    - get_id_token によりリフレッシュトークンから ID トークンを取得。
  - ページネーション対応で重複キー防止（pagination_key を追跡）。
  - DuckDB への保存ユーティリティ（冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar は ON CONFLICT DO UPDATE により上書き（重複耐性）。
    - PK 欠損行はスキップし、スキップ件数をログ出力。
    - fetched_at を UTC ISO 秒表記で保存し、データ取得時刻のトレーサビリティを確保（Look-ahead Bias 対策）。
  - 型変換ユーティリティ:
    - _to_float / _to_int（安全に None を返す・ "1.0" のようなケースに対応）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - 3 層アーキテクチャに基づくテーブル群を定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（CHECK、PRIMARY KEY、外部キー）を定義しデータ整合性を担保。
  - インデックスを多数定義（検索パターンに最適化）。
  - init_schema(db_path) によりディレクトリ作成・DDL 実行（冪等）して DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計:
    - 差分更新（最終取得日からの差分取得）と backfill による後出し修正吸収。
    - 市場カレンダー先読み（デフォルト 90 日）で営業日調整を行う。
    - 品質チェック（quality モジュール）を ETL 後に任意実行。
    - 各ステップは独立してエラーハンドリング（1 ステップ失敗でも他ステップ継続）。
    - id_token を注入可能でテスト容易性を確保。
  - 実装:
    - ETLResult dataclass（各取得数、保存数、quality issues、errors を集約）。
    - get_last_* ヘルパー（raw_prices/raw_financials/market_calendar の最終取得日）。
    - run_prices_etl / run_financials_etl / run_calendar_etl：差分取得 + 保存（backfill, lookahead に対応）。
    - run_daily_etl：日次 ETL のメイン入口。処理順序:
      1. 市場カレンダー ETL（先読み）
      2. 株価日足 ETL（営業日に調整してから）
      3. 財務データ ETL
      4. 品質チェック（オプション）
    - デフォルトの backfill_days = 3、calendar_lookahead_days = 90、spike_threshold = 0.5。

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティ用テーブルを定義:
    - signal_events（戦略が生成したシグナルをすべて記録）
    - order_requests（冪等キー: order_request_id）
    - executions（証券会社提供の約定 ID を保持し冪等性を担保）
  - 監査向けインデックスを多数定義（status 検索、戦略別検索、broker_order_id 紐付け等）。
  - すべての TIMESTAMP を UTC で保存するため init_audit_schema は "SET TimeZone='UTC'" を実行。
  - init_audit_schema(conn) および init_audit_db(db_path) を提供。

- データ品質チェック（kabusys.data.quality）
  - QualityIssue dataclass を定義（check_name, table, severity, detail, rows）。
  - 実装済チェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は対象外）。重大度は error。
    - check_spike: 前日比スパイク検出（LAG を利用、閾値デフォルト 50%）。
  - 各チェックは問題のサンプル（最大 10 件）を返し、呼び出し元で重大度に応じた対応を行える設計。

### 既知の注記 / マイグレーションノート
- 必須環境変数（存在しない場合は起動時に ValueError を発生）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト DB パス:
  - DUCKDB_PATH = data/kabusys.duckdb
  - SQLITE_PATH = data/monitoring.db
- .env の自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後に CWD からではなく __file__ を基準に探索される点に注意。
- DuckDB による ON CONFLICT の更新（冪等性）を前提にしているため、既存データとのマージ動作に注意してください。
- audit スキーマでは TIMESTAMP を UTC に固定して保存するため、アプリ側でもタイムゾーンを意識して扱ってください（updated_at はアプリ側で current_timestamp をセットする前提）。
- J-Quants API 周りはネットワーク／認証に依存するため、rate limiting・リトライが組み込まれていますが、外部環境（プロキシ等）での動作は運用で確認してください。

### セキュリティ
- リフレッシュトークンや API パスワードなどの機密情報は環境変数または .env にて管理する想定です。ログにトークン等を出力しないよう注意しています（明示的なログ出力は行っていません）。

### 変更点に含めていない事項
- strategy / execution / monitoring サブパッケージの具体的な戦略・発注ロジックは本バージョンではスケルトン（空 __init__）に留めています。今後のリリースで実装予定です。

---

今後の予定（例）
- 戦略層と発注層の具体実装（ポートフォリオ管理、スリッページ管理、証券会社 API 連携）
- データ増強（ニュース取得、AI スコアリングの初期パイプライン）
- 品質チェックの拡張（重複・日付不整合チェック等の追加）
- テストカバレッジと CI/CD の整備

ご要望やバグ報告があれば issue を作成してください。