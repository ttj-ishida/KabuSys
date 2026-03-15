# Changelog

すべての notable な変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。  
このプロジェクトはセマンティックバージョニング（SemVer）を採用します。

## [Unreleased]

（次回リリースに向けた未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-03-15

初回リリース。日本株自動売買システムのコア基盤を実装しました。主要な機能と設計上の注意点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期実装。バージョン: 0.1.0
  - __all__ に data, strategy, execution, monitoring を定義。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - Settings クラスを追加し、アプリケーション設定を環境変数から提供。
  - 必須設定の検証を実装（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - env 値の検証（KABUSYS_ENV、LOG_LEVEL の許容値チェック）。
  - .env 自動読み込み機能を実装:
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWDに依存しない）。
    - 読み込み順序: OS 環境 > .env.local（上書き）> .env（未設定のみ）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト用途）。
  - .env パーサを実装:
    - export プレフィックス対応、クォート（シングル/ダブル）とバックスラッシュエスケープ対応、行内コメントの扱い等を考慮。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API からのデータ取得関数を実装:
    - fetch_daily_quotes: 株価日足（OHLCV、ページネーション対応）
    - fetch_financial_statements: 四半期財務データ（ページネーション対応）
    - fetch_market_calendar: JPX マーケットカレンダー（祝日・半日・SQ）
  - 認証ユーティリティ:
    - get_id_token: refresh_token から id_token を取得（POST）
    - モジュールレベルの id_token キャッシュを実装（ページネーション間で共有）
    - 401 受信時に自動でトークンリフレッシュして 1 回リトライ
  - HTTP リクエスト実装:
    - 固定間隔スロットリングによるレート制御（120 req/min を順守）
    - リトライロジック（最大 3 回、指数バックオフ、HTTP 408/429/5xx やネットワークエラーを再試行）
    - 429 の場合は Retry-After ヘッダを尊重
    - JSON デコード失敗時に明示的エラー
  - データ保存ユーティリティ（DuckDB 用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装
    - fetched_at を UTC ISO8601 形式で記録し、Look-ahead Bias を防止
    - INSERT ... ON CONFLICT DO UPDATE による冪等性確保
    - PK 欠損行はスキップし、スキップ数をログ出力
    - 型変換ヘルパー _to_float / _to_int を実装（堅牢な変換ルール）

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - 3 層データモデルに基づくスキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 初期化 API:
    - init_schema(db_path) — 必要なディレクトリ作成、全テーブル・インデックス作成（冪等）
    - get_connection(db_path) — 既存 DB への接続
  - 性能向けインデックス群の定義（よく使うクエリパターンに対応）

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - 監査用テーブル群を実装:
    - signal_events（戦略が生成した全シグナルの記録）
    - order_requests（冪等キー order_request_id を持つ発注要求）
    - executions（証券会社からの約定情報）
  - 監査スキーマ初期化 API:
    - init_audit_schema(conn) — 既存の DuckDB 接続に監査テーブルを追加
    - init_audit_db(db_path) — 監査専用 DB を初期化
  - 設計方針:
    - すべての TIMESTAMP は UTC 保存（init_audit_schema は SET TimeZone='UTC' を実行）
    - 外部キーは ON DELETE RESTRICT（監査ログは削除しない前提）
    - ステータス遷移やチェック制約を明確化

- パッケージ構成（空のパッケージプレースホルダ）
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/data/__init__.py
  - src/kabusys/monitoring/__init__.py

### 変更 (Changed)
- 初期リリースのため該当なし（ベース実装の追加が中心）

### 修正 (Fixed)
- 初期リリースのため該当なし

### 既知の制限 / 注意点
- 環境変数の必須項目（未設定時は Settings プロパティが ValueError を送出します）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB のデフォルトパス:
  - DUCKDB_PATH のデフォルトは data/kabusys.duckdb
  - SQLITE_PATH のデフォルトは data/monitoring.db
- 自動 .env 読み込みはプロジェクトルートが特定できない場合はスキップされます（配布パッケージ環境での挙動に配慮）。
- J-Quants API のレート制限はソフト実装（ローカルプロセス内の制御）。複数プロセス/ホストでの同時実行時は別途考慮が必要です。
- DuckDB の SQL 制約・インデックスは設計時の想定クエリパターンに最適化していますが、実運用に応じて調整してください。

### マイグレーション / 初期化手順
1. 環境変数を設定（またはプロジェクトルートに .env を用意）
2. DuckDB スキーマ初期化:
   - from kabusys.data.schema import init_schema
   - conn = init_schema(settings.duckdb_path)
3. 監査ログを追加する場合:
   - from kabusys.data.audit import init_audit_schema
   - init_audit_schema(conn)
4. J-Quants データ取得例:
   - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   - recs = fetch_daily_quotes(date_from=..., date_to=...)
   - save_daily_quotes(conn, recs)

### セキュリティ (Security)
- 現時点で機密情報（トークン・パスワード）は環境変数経由で管理する設計。運用時は環境・シークレット管理に注意してください。

---

（以降のリリースでは、Added / Changed / Fixed / Deprecated / Removed / Security の各セクションを更新してください）