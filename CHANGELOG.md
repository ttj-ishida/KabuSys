# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

さらに: この CHANGELOG は与えられたコードベースからの実装内容を推測して作成した初期リリース記録です。

## [Unreleased]

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買プラットフォームの基礎モジュール群を実装。

### 追加 (Added)
- パッケージエントリポイント
  - kabusys.__init__ に __version__ = "0.1.0" とパブリック API (data, strategy, execution, monitoring) を追加。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env を自動読み込み。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
  - .env パーサ実装 (_parse_env_line):
    - コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント考慮の処理。
  - 必須項目の取得ヘルパー (_require) と代表的な設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DB パス: DUCKDB_PATH / SQLITE_PATH（デフォルトを提供）
    - 環境 (KABUSYS_ENV)、ログレベル検証（許容値チェック）と is_live / is_paper / is_dev フラグ。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティ _request を実装:
    - ベース URL: https://api.jquants.com/v1
    - レート制限 (120 req/min) を守る固定間隔スロットリング (_RateLimiter) を実装。
    - リトライ戦略: 最大 3 回、指数バックオフ、対象ステータス 408/429/5xx、ネットワークエラー対応。
    - 401 Unauthorized を受けた場合はリフレッシュを自動試行して 1 回リトライ（無限再帰防止）。
    - レスポンス JSON のデコードエラーを明示的に扱う。
  - ID トークン取得/キャッシュ:
    - get_id_token(refresh_token=None) を実装。モジュールレベルのキャッシュを保持。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes: 日足 (OHLCV) をページングで取得。
    - fetch_financial_statements: 四半期財務データをページングで取得。
    - fetch_market_calendar: JPX マーケットカレンダーを取得。
    - 取得時に fetched_at を UTC で記録する設計（保存時）。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar を提供。
    - ON CONFLICT DO UPDATE を用いることで既存レコードを上書きし冪等性を確保。
    - PK 欠損レコードはスキップして警告ログを出力。
  - 型変換ユーティリティ:
    - _to_float, _to_int を実装（空値や不正値に対して安全に None を返す。整数変換は小数部検出に注意）。

- スキーマ定義・初期化 (kabusys.data.schema)
  - DuckDB 用の包括的スキーマを DDL 文字列で定義（Raw / Processed / Feature / Execution 層）。
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature 層: features, ai_scores
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - テーブル制約（PK、CHECK、FOREIGN KEY）とインデックスを定義。
  - init_schema(db_path) でディレクトリ作成 → DuckDB 接続 → DDL/インデックス実行（冪等）。
  - get_connection(db_path) を提供（既存 DB への接続、初期化は行わない）。

- 監査ログ / トレーサビリティ (kabusys.data.audit)
  - トレーサビリティを目的とした監査テーブルを定義:
    - signal_events, order_requests (冪等キー order_request_id), executions
  - すべての TIMESTAMP を UTC で保存する方針（init_audit_schema 内で SET TimeZone='UTC' を実行）。
  - 状態遷移と業務要件（注文のステータスセット、チェック制約、外部キー制約）をDDLに反映。
  - init_audit_schema(conn)（既存接続へ追加）と init_audit_db(db_path)（専用 DB 初期化）を提供。
  - 監査用インデックスを定義（status・signal_id・broker_order_id 等での高速検索）。

- データ品質チェック (kabusys.data.quality)
  - QualityIssue dataclass を定義（チェック名、テーブル、severity、詳細、サンプル行）。
  - チェック機能を実装:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は除外）。
    - check_spike: 前日比スパイク検出（デフォルト閾値 50%）、LAG ウィンドウを使用。
    - check_duplicates: raw_prices の主キー重複検出（念のため）。
    - check_date_consistency: 将来日付の検出、market_calendar と整合しない非営業日のデータ検出（market_calendar が存在する場合のみ）。
  - run_all_checks で上記をまとめて実行し、検出結果をリストで返却。重大度別のログ出力を実施。

- パッケージ構造に空 __init__ ファイルを用意
  - kabusys.data.__init__, kabusys.execution.__init__, kabusys.strategy.__init__, kabusys.monitoring.__init__（将来モジュール実装のためのプレースホルダ）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### ドキュメント / 設計ノート
- 各モジュールに設計原則・注釈コメントを多数追加（レート制御、リトライポリシー、冪等性、トレーサビリティ、UTC保存等）。
- DataSchema.md / DataPlatform.md 等の外部設計参照をコメントで明示（実装に沿った仕様記載）。

### 既知の制限 / 注意点
- J-Quants クライアントは urllib を直接使用しており、非同期処理は未対応。
- トークンキャッシュはモジュールスコープの単純キャッシュでプロセス内共有のみ。
- DuckDB スキーマは業務要件に合わせて詳細な CHECK 制約を多数含むため、外部ツールや手作業でのデータ挿入時に制約違反が発生する可能性がある。
- 市場データの取得・保存フローにおける Look-ahead 防止は fetched_at の記録で対応しているが、ETL フロー設計時に更なる注意が必要。

---

（今後のリリースでは、戦略実装、発注実行バインディング、監視/アラート機能、単体テストおよび CI 設定、さらに細かなエラーハンドリング強化などを追記予定）