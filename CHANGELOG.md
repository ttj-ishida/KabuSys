# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはまだ初期リリースであり、以降のバージョンはここに追記されます。

全般ルール:  
- 非互換な変更は Breaking Changes として明記します。  
- 重要な環境変数や動作の既定値は各項目に記載します。

## [Unreleased]

- （将来の変更をここに記載）

## [0.1.0] - 2026-03-15

初回リリース。以下の主要機能と実装が含まれます。

Added
- パッケージ基盤
  - kabusys パッケージを追加。パッケージバージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定/環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルート判定は __file__ の親階層を探索し、.git または pyproject.toml を基準に行うため、CWD に依存しない。
  - .env 行パーサーを実装（コメント・export / 引用・エスケープ対応、無効行スキップ）。
  - 環境変数読み込みで OS の既存キーを保護する機能（protected set）。
  - Settings クラスを追加し、プロパティで主要設定を取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（既定: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（既定: data/kabusys.duckdb）
    - SQLITE_PATH（既定: data/monitoring.db）
    - KABUSYS_ENV（既定: development、許容値: development, paper_trading, live）
    - LOG_LEVEL（既定: INFO、許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - 未設定の必須環境変数は _require() により ValueError を送出するため、起動前に環境を整備すること。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API レート制御を行う固定間隔スロットリング RateLimiter を実装（デフォルト 120 req/min）。
  - リトライロジック搭載:
    - 指数バックオフ（base=2.0 秒）
    - 最大リトライ回数: 3
    - 再試行対象: 408, 429, および 5xx 系
    - 429 の場合は Retry-After ヘッダを優先
  - 認証トークン処理:
    - refresh_token から id_token を取得する get_id_token() を実装（POST /token/auth_refresh）
    - 401 受信時は自動で1回だけトークンをリフレッシュしてリトライ（無限再帰回避）
    - モジュールレベルで id_token をキャッシュし、ページネーション間で共有
  - データ取得関数（ページネーション対応）を実装:
    - fetch_daily_quotes(): 株価日足（OHLCV）
    - fetch_financial_statements(): 四半期財務データ（BS/PL）
    - fetch_market_calendar(): JPX マーケットカレンダー（祝日・半日・SQ）
  - 取得時の設計原則:
    - API レート制限遵守、401 時の自動リフレッシュ、Look-ahead 防止のため fetched_at に UTC タイムスタンプを記録
  - DuckDB への保存関数を実装（冪等性確保）:
    - save_daily_quotes(), save_financial_statements(), save_market_calendar()
    - ON CONFLICT DO UPDATE を使用し重複を排除・更新
    - PK 欠損レコードはスキップしログ出力
  - ユーティリティ変換関数を実装:
    - _to_float(): 空値や変換失敗は None を返す
    - _to_int(): "1.0" のような表現を float 経由で変換。小数部が 0 以外の場合は None を返す（安全優先）

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - DataSchema.md を想定した 3 層（Raw / Processed / Feature）＋ Execution レイヤのテーブル定義を実装:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 監査テーブルは別モジュールで定義（init_schema() は監査テーブルを含まない）
  - 頻出クエリ向けにインデックスを多数定義（例: code, date に対する複合インデックス、status 検索用インデックス等）
  - init_schema(db_path) を実装:
    - 指定したパスの親ディレクトリを自動作成（:memory: をサポート）
    - すべてのテーブル/インデックスを作成（冪等）
    - 初回使う場合は init_schema() を呼ぶこと（get_connection() は単に接続を返す）
  - get_connection(db_path) を実装（スキーマ初期化は行わない）

- 監査ログ（トレーサビリティ）モジュール（kabusys.data.audit）
  - 戦略→シグナル→発注→約定 のトレーサビリティを完全に追跡する監査用スキーマを実装:
    - signal_events: 戦略が生成した全シグナル（棄却やエラー含む）
    - order_requests: 発注要求（order_request_id を冪等キーとして機能）
    - executions: 証券会社から返された約定ログ（broker_execution_id を冪等キーとして保持）
  - 監査スキーマ初期化関数:
    - init_audit_schema(conn): 既存 DuckDB 接続に監査テーブルを追加。実行時に SET TimeZone='UTC' を実行して UTC 保存を強制。
    - init_audit_db(db_path): 監査専用 DB を初期化して接続を返す（親ディレクトリ自動作成）
  - テーブル設計原則:
    - すべてのテーブルに created_at を持ち、updated_at はアプリ側で更新時に current_timestamp を設定する想定
    - 監査ログは削除しない前提で ON DELETE RESTRICT を採用
    - ステータス遷移定義（order_requests の状態管理に関する制約）を明文化

- その他
  - ロギングを適所に追加（fetch/save の情報・警告出力）
  - 各種入力検証（チェック制約）をスキーマに反映
  - DB 初期化時に親ディレクトリ自動作成（ファイルパス向け）

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 使用上の注意
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - これらが未設定の場合、Settings の対応プロパティ参照で ValueError が発生します。
- DB 初期化:
  - data.schema.init_schema() を呼んでからデータ操作関数（save_* 等）を使用してください。
  - 監査テーブルは init_audit_schema() で追加するか、init_audit_db() で専用 DB を用意してください。
- タイムゾーン:
  - 監査スキーマ初期化時に UTC に固定します。保存される TIMESTAMP は UTC 想定です。
- API 利用上の制約:
  - J-Quants API のレート制限（120 req/min）を内部で制御しますが、大量並列呼び出しなどの運用は追加対策が必要です。

今後の予定（例）
- strategy / execution / monitoring の実装充実
- テストスイートの追加（特にリトライ・トークン更新・DB 書き込みの統合テスト）
- より柔軟なレートリミッタ（トークンバケット等）や非同期化の検討

-----------------------------------------
参考: Keep a Changelog
https://keepachangelog.com/ja/1.0.0/