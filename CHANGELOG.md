# CHANGELOG

すべての注目すべき変更を記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-03-15

初回リリース。本リリースで導入された主要な機能・モジュールは以下のとおりです。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化 (src/kabusys/__init__.py)
    - バージョン情報 __version__ = "0.1.0"
    - 公開モジュール一覧: data, strategy, execution, monitoring

- 環境変数/設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの自動読み込み機能を実装
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索
    - 自動ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ実装（コメント・クォート・export 形式対応）
  - Settings クラスを提供（プロパティ経由で設定値を取得）
    - 必須の環境変数を検証し、未設定時に ValueError を送出
    - J-Quants / kabu ステーション / Slack / DB パス 等のプロパティを定義
    - 環境 (development/paper_trading/live) とログレベルの検証ロジック
    - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 操作用ユーティリティを実装（JSON の自動デコード、エラーハンドリング）
  - レート制限制御（固定間隔スロットリング、120 req/min を実装）
  - 再試行ロジック（指数バックオフ、最大リトライ回数 3 回、408/429/5xx に対応）
  - 401 レスポンス時の自動トークンリフレッシュ（1 回のみ）を実装
  - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）
  - データ取得 API
    - fetch_daily_quotes: 日足（OHLCV）取得（ページネーション対応）
    - fetch_financial_statements: 財務データ（四半期 BS/PL）取得（ページネーション対応）
    - fetch_market_calendar: JPX マーケットカレンダー取得
  - DuckDB への保存（冪等実装）
    - save_daily_quotes: raw_prices テーブルへ保存（ON CONFLICT DO UPDATE）
    - save_financial_statements: raw_financials テーブルへ保存（ON CONFLICT DO UPDATE）
    - save_market_calendar: market_calendar テーブルへ保存（ON CONFLICT DO UPDATE）
  - ユーティリティ関数
    - _to_float / _to_int: 入力値の堅牢な変換（空値・不正値を None にするロジック、"1.0" 型変換の扱い 等）
  - 設計上の注記
    - 取得時刻 fetched_at は UTC で記録し、Look-ahead Bias のトレーサビリティを確保

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - 「Raw / Processed / Feature / Execution」3層構造に基づくテーブル定義を実装
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 主要な制約（PRIMARY KEY, CHECK, FOREIGN KEY）とインデックス定義を含む
  - init_schema(db_path) によりデータベースファイルの親ディレクトリを自動作成しつつスキーマを冪等に初期化
  - get_connection(db_path) により既存 DB への接続を取得（初期化は行わない）

- 監査ログ（トレーサビリティ）モジュール (src/kabusys/data/audit.py)
  - signal_events, order_requests, executions の監査用テーブルを定義
  - order_request_id を冪等キーとして扱う設計（再送による二重発注防止）
  - 全 TIMESTAMP を UTC で保存することを前提（init_audit_schema は SET TimeZone='UTC' を実行）
  - init_audit_schema(conn) により既存接続へ監査テーブルを追加（冪等）
  - init_audit_db(db_path) による監査専用 DB 初期化ヘルパー
  - インデックス定義により検索・ジョインを高速化（status / date / broker_order_id 等で最適化）

- 空のモジュールプレースホルダ
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/data/__init__.py
  - src/kabusys/monitoring/__init__.py
  - これらは外部 API の拡張用プレースホルダとして配置

### 変更 (Changed)
- 初回リリースのため該当なし

### 修正 (Fixed)
- 初回リリースのため該当なし

### セキュリティ (Security)
- 以下の環境変数は必須として扱われ、未設定時は起動時にエラーを送出する（Settings にて検証）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- .env の読み込み時に OS 環境変数は保護（上書きされない）される挙動を導入

### 既知の制約・注意点 (Notes)
- J-Quants API のレート制限は固定間隔スロットリングで実装（120 req/min）。厳密な分散環境では追加の協調が必要。
- HTTP 429 応答時は Retry-After ヘッダを優先して待機する実装。
- トークンリフレッシュは 401 発生時に 1 回のみ自動で行い、それで解決しない場合は失敗となる。
- DuckDB スキーマ初期化は冪等であり、既存のデータは基本的に保持される（DDL の変更は破壊的ではないが、スキーマ変更の際は注意）。
- audit テーブルは削除を前提としない設計（FK は ON DELETE RESTRICT）。監査ログは基本的に消さない運用を想定。

---

今後のリリースでは、strategy / execution / monitoring 各モジュールの具象実装、より詳細なエラーハンドリング、分散環境向けのレート制御強化、CI テスト向けのモック機能等を予定しています。