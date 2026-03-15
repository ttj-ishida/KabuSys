# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニング (SemVer) を採用します。

## [Unreleased]
（未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買プラットフォームのコアライブラリを追加しました。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージ名、バージョン（0.1.0）および公開サブモジュール一覧を定義（data, strategy, execution, monitoring）。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
    - 自動ロードの挙動:
      - プロジェクトルートは __file__ を基点に `.git` または `pyproject.toml` を探索して決定（CWD に依存しない）。
      - 自動ロードはデフォルトで有効。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - .env パーサは `export KEY=val` 形式、クォート値、インラインコメント（スペース・タブで区切られた `#`）等に対応。
    - Settings による必須変数の取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - デフォルト値や検証:
      - KABUSYS_ENV の許容値: development / paper_trading / live（不正値は ValueError）
      - LOG_LEVEL の許容値: DEBUG / INFO / WARNING / ERROR / CRITICAL（不正値は ValueError）
      - DB パスのデフォルト（DuckDB/SQLite）を提供。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - API から株価日足（OHLCV）、財務四半期データ、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
    - 認証: refresh token から id_token を取得する get_id_token() を実装。
    - レート制御:
      - 固定間隔スロットリング実装（_RateLimiter）で 120 req/min を順守。
      - id_token のモジュールレベルキャッシュを実装し、ページネーション間で共有。
    - リトライ/エラーハンドリング:
      - 408/429/5xx 等の再試行（指数バックオフ、最大 3 回）。429 の場合は Retry-After を優先。
      - 401 受信時は id_token を自動リフレッシュして 1 回リトライ（無限再帰回避のため allow_refresh フラグ）。
    - トレーサビリティ:
      - データ保存時に取得時刻（fetched_at）を UTC ISO 形式で付与（Look-ahead bias を防止）。
    - データ永続化:
      - DuckDB に保存する save_daily_quotes / save_financial_statements / save_market_calendar を実装。
      - 挿入は冪等（ON CONFLICT DO UPDATE）で重複を排除。
    - 型変換ユーティリティ: _to_float / _to_int（厳密な変換ルール、"1.0" のような文字列処理や小数切り捨てを防ぐ挙動を含む）。

- DuckDB スキーマ定義・初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution の 3 層（＋実行・監査のテーブル）に対応した DDL を定義。
    - テーブルの主な追加:
      - Raw layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature layer: features, ai_scores
      - Execution layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 頻出クエリを想定したインデックスを多数定義（コード×日付スキャンやステータス検索など）。
    - init_schema(db_path) による初期化関数を追加:
      - db_path の親ディレクトリが存在しない場合は自動作成。
      - ":memory:" をサポート。
      - 既存テーブルはスキップするため冪等。
    - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- 監査ログ（トレーサビリティ）モジュール
  - src/kabusys/data/audit.py
    - シグナル→発注→約定のトレーサビリティを担保する監査テーブル群を実装。
    - テーブル:
      - signal_events（戦略が生成した全シグナルの記録。拒否やエラーも含む）
      - order_requests（発注要求。order_request_id を冪等キーとして扱う。limit/stop チェック制約あり）
      - executions（証券会社からの約定ログ。broker_execution_id をユニークな冪等キーとして扱う）
    - 監査用インデックス群を定義（signal_events の検索、order_requests のステータス検索、broker_order_id 紐付け等）。
    - init_audit_schema(conn) / init_audit_db(db_path) を追加:
      - 全ての TIMESTAMP を UTC に統一（init_audit_schema は "SET TimeZone='UTC'" を実行）。
      - 既存接続に監査テーブルを追加するユーティリティ。
      - init_audit_db は親ディレクトリ自動作成、":memory:" サポート。

- モジュールのプレースホルダ
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を追加（パッケージ構成のための空 __init__）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 認証トークンの扱い:
  - id_token リフレッシュは許可された条件下でのみ自動実行し、無限再帰を防止する設計を採用。
  - 環境変数の自動ロードは明示的に無効化できる（テストなどに配慮）。

注意事項 / マイグレーション
- DuckDB の初期化:
  - 初回は必ず init_schema() または init_audit_db() を呼んでテーブルを作成してください。get_connection() はスキーマを作成しません。
- 環境変数:
  - 必須の環境変数が未設定の場合、Settings の各プロパティは ValueError を投げます。リリース前に .env.example を参照して .env を用意してください。
- タイムゾーン:
  - 監査用テーブルのタイムスタンプは UTC に固定されます。アプリ側はタイムゾーンに注意して取り扱ってください。

-- end --