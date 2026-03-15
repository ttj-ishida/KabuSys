# Changelog

すべての変更は Keep a Changelog の仕様に準拠します。  
このファイルはリポジトリのコードベースから推測して作成した初期リリースの変更履歴です。

全般
- 初版リリース (v0.1.0)
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - リリース日: 2026-03-15

## [0.1.0] - 2026-03-15

### 追加 (Added)
- パッケージ構成（モジュール群）
  - kabusys パッケージの骨格を追加。公開対象モジュールとして data, strategy, execution, monitoring を __all__ に定義。
  - モジュール群のための空の __init__ ファイルを配置（execution, strategy, data, monitoring）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを追加。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）, LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - .env 自動ロード機能を実装。挙動:
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - OS 側の既存環境変数は保護（保護されたキー群は上書きされない）。
    - 自動ロードを無効にするための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env 行パーサを実装（export KEY=val 形式対応、引用符・バックスラッシュエスケープ対応、コメント処理の細かいルール）。
  - 必須変数未設定時は明確な ValueError を送出する _require 関数を提供。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants から以下のデータを取得するクライアントを実装:
    - 株価日足（OHLCV）: fetch_daily_quotes()
    - 財務データ（四半期 BS/PL）: fetch_financial_statements()
    - JPX マーケットカレンダー: fetch_market_calendar()
  - 設計/実装のポイント:
    - API レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter、最小間隔 = 60 / 120 = 0.5s）。
    - リトライロジックを実装（指数バックオフ、最大 3 回、ネットワーク/サーバーエラー/429/408 を対象）。
    - 429 の場合は Retry-After ヘッダを優先して待機。
    - 401 Unauthorized 受信時は自動でリフレッシュトークンから id_token を再取得して 1 回だけリトライ（無限再帰を回避）。
    - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）。
    - すべての API 呼び出しは JSON を返すことを前提にデコードし、失敗時はわかりやすい例外を送出。
    - ページネーション対応（pagination_key を利用）、重複 pagination_key の検出によるループ終了。
    - データ取得時のロギング（取得件数の info ログなど）。

  - DuckDB への保存関数:
    - save_daily_quotes(), save_financial_statements(), save_market_calendar()
    - 保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で実装。fetched_at は UTC の ISO8601 (Z) で保存。
    - PK 欠損行はスキップし、スキップ件数を warning ログで通知。
    - 型変換ユーティリティ _to_float(), _to_int() を提供（空/不正値は None、_to_int は小数部が非ゼロの文字列を None にする等の厳密挙動）。

- DuckDB スキーマと初期化 (src/kabusys/data/schema.py)
  - データレイヤーのスキーマ定義（DDL）を追加。3 層（Raw / Processed / Feature）に加え Execution レイヤーを含む網羅的なテーブルセット:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリパターンを意識した複数の CREATE INDEX 文）。
  - init_schema(db_path) を提供:
    - DB ファイルの親ディレクトリを自動作成し、すべてのテーブル/インデックスを作成（冪等）。
    - ":memory:" によるインメモリ DB をサポート。
  - get_connection(db_path) を提供（既存 DB への素直な接続。初回は init_schema を推奨）。

- 監査ログ（Audit）スキーマ (src/kabusys/data/audit.py)
  - シグナルから約定までをトレースする監査テーブル群を追加（UUID ベースの連鎖トレーサビリティ）:
    - signal_events（戦略が生成したシグナル／棄却含む）
    - order_requests（発注要求。order_request_id を冪等キーとして扱う。limit/stop のチェック制約を実装）
    - executions（証券会社からの約定ログ。broker_execution_id を一意キーとして冪等性確保）
  - 監査インデックス群（status や signal_id・broker_order_id による検索を高速化）。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供:
    - init_audit_schema は接続に対して UTC タイムゾーン（SET TimeZone='UTC'）をセットしテーブルを作成。
    - init_audit_db は専用 DuckDB を初期化して接続を返す（親ディレクトリ自動作成、":memory:" サポート）。

### 変更 (Changed)
- 初版のため該当なし

### 修正 (Fixed)
- 初版のため該当なし

### 破壊的変更 (Removed / Deprecated)
- 初版のため該当なし

## 補足 / 運用メモ
- 環境変数自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。
- DuckDB 初期化は init_schema() を一度実行しておくことを推奨します（get_connection はスキーマ初期化を行いません）。
- 監査ログではすべての TIMESTAMP を UTC で保存する方針です。アプリ側で updated_at を更新する際は current_timestamp を使ってください。
- J-Quants クライアントはレート制限・リトライ・トークンリフレッシュを備えていますが、運用時はログや監視による挙動確認を行ってください。

（この CHANGELOG はコードの静的解析とコメントから推測して作成しています。実運用に合わせて内容を調整してください。）