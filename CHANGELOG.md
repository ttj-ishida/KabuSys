# Changelog

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

※ 本リポジトリは初期リリースの内容をコードベースから推測して記載しています。

## [0.1.0] - 2026-03-15

### 追加 (Added)
- パッケージ初期導入
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージの公開内容: data, strategy, execution, monitoring を __all__ として公開。

- 環境設定管理 (src/kabusys/config.py)
  - Settings クラスを導入し、環境変数からアプリケーション設定を取得するプロパティを提供。
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN、SLACK_CHANNEL_ID（いずれも必須）
    - データベースのパス: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - システム設定: KABUSYS_ENV（許容値: development, paper_trading, live）、LOG_LEVEL（許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - 環境判定プロパティ: is_live, is_paper, is_dev
  - .env 自動ロード機能を実装
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出は .git または pyproject.toml を基準に実装（__file__ を基点に探索）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env パーサを実装（_parse_env_line）
    - export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 基本機能
    - get_id_token: リフレッシュトークンから id_token を取得（POST /token/auth_refresh）
    - fetch_daily_quotes: 株価日足（OHLCV）のページネーション対応取得
    - fetch_financial_statements: 四半期財務データのページネーション対応取得
    - fetch_market_calendar: JPX マーケットカレンダー取得
  - 実装上の特徴
    - レート制限遵守: 固定間隔スロットリングで 120 req/min（_min_interval = 60/120）を実装（_RateLimiter）
    - リトライロジック: 指数バックオフ、最大 3 回、対象ステータス 408 / 429 / 5xx を考慮
    - 401 応答時は自動で id_token をリフレッシュして 1 回リトライ（無限再帰防止の仕組みあり）
    - id_token のモジュールレベルキャッシュを導入（ページネーション間で再利用）
    - Look-ahead Bias 対策: データ保存時に fetched_at を UTC タイムスタンプで記録
    - JSON デコード失敗時の明確なエラー
  - DuckDB への保存関数
    - save_daily_quotes / save_financial_statements / save_market_calendar
      - ON CONFLICT DO UPDATE による冪等性（重複挿入を更新で吸収）
      - PK 欠損行はスキップし、スキップ数をログ出力
      - 日付・コードなどを厳密に扱う（型変換ユーティリティ _to_float, _to_int を使用）
  - ヘルパー
    - _request: 共通 HTTP 呼び出しラッパー（ヘッダ、タイムアウト、リトライ、Retry-After 参照）
    - _to_float / _to_int: 変換失敗時は None を返す安全な変換ロジック（"1.0" のような文字列を int に変換する取り扱いも明示）

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - 3 層構造の設計に基づくテーブル定義を追加
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対する制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY など）を細かく定義
  - インデックス定義を含む（頻出クエリパターンに基づく複数インデックス）
  - 公開 API:
    - init_schema(db_path): ディレクトリ作成を含めた初期化（冪等）、全 DDL とインデックスを実行して DuckDB 接続を返す
    - get_connection(db_path): 既存 DB への接続を返す（スキーマ初期化は行わない）

- 監査ログ（トレーサビリティ）モジュール (src/kabusys/data/audit.py)
  - 監査テーブルの設計および初期化を追加
    - signal_events（戦略が生成したシグナルの記録。棄却やエラーも含む）
    - order_requests（発注要求。order_request_id を冪等キーとして扱う。limit/stop の価格チェックを含む）
    - executions（証券会社からの約定ログ。broker_execution_id を冪等キーとして扱う）
  - 設計原則をコード中に記述
    - 全ての TIMESTAMP を UTC で保存する（init_audit_schema は conn.execute("SET TimeZone='UTC'") を実行）
    - 削除しない前提（ON DELETE RESTRICT）
    - 状態遷移やステータス列を明示
  - インデックスを複数定義（シグナル検索、キュー検索、broker_order_id 検索等）
  - 公開 API:
    - init_audit_schema(conn): 既存の DuckDB 接続に監査テーブルを追加（冪等）
    - init_audit_db(db_path): 監査専用 DB を初期化して接続を返す

- モジュール構成（空のパッケージプレースホルダ）
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py, src/kabusys/monitoring/__init__.py を追加（パッケージ階層を確立）

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### 注意事項 (Notes)
- 環境変数が未設定で必須項目を参照した場合は ValueError を発生させるため、運用環境や CI では必須の環境変数を設定する必要があります（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
- DuckDB 初期化は init_schema() を利用すること（get_connection() は既存 DB 接続用）。
- J-Quants API 呼び出しは内部でレート制御・リトライ・トークン自動リフレッシュを行いますが、運用上の追加制御（より厳しいスロットリングやバッチ化など）は必要に応じて検討してください。
- 監査ログは削除しない前提の設計です。データ保持方針に合わせて運用側でバックアップ/アーカイブ設計を行ってください。

---

今後のリリースでは、strategy / execution / monitoring の実装、CLI やデプロイ関連設定、テストカバレッジ、ドキュメント（DataSchema.md, DataPlatform.md 参照）などの追加が想定されます。