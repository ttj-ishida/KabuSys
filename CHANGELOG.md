# Changelog

すべての変更は Keep a Changelog のフォーマットに従って記載しています。  
安定版リリース以外のブランチや開発中の変更は Unreleased に記載します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-15
初回リリース — 日本株自動売買システムの基盤となるライブラリを追加。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。
    - __version__ = "0.1.0"
    - パブリックサブパッケージ指定: data, strategy, execution, monitoring

- 環境設定管理 (src/kabusys/config.py)
  - .env/.env.local の自動読み込み機能を実装
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能（テスト用途）。
    - OS 環境変数を保護する protected キーセットを使用し誤上書きを防止。
    - .env 読み込み失敗時は警告を発行して処理を継続。
  - 柔軟かつ堅牢な .env パーサを実装
    - export KEY=val 形式サポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理の扱いなどに対応。
  - Settings クラスを実装（settings = Settings()）
    - J-Quants / kabuステーション / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）などのプロパティを提供。
    - 必須値は未設定時に ValueError を送出。
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL の検証。
    - is_live / is_paper / is_dev の便宜プロパティ。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API からのデータ取得（株価日足、財務データ、JPX マーケットカレンダー）機能を実装。
  - 設計上の主要特徴:
    - レート制限遵守のための固定間隔スロットリング（120 req/min）を組み込んだ RateLimiter。
    - リトライロジック（指数バックオフ、最大 3 回）。対象: 408, 429, 5xx。429 の場合は Retry-After を優先。
    - 401 Unauthorized を検出した場合はリフレッシュトークンで id_token を自動更新して 1 回リトライ（無限再帰を防止）。
    - id_token のモジュールレベルキャッシュを実装（ページネーション間でトークン共有）。
    - ページネーション対応のフェッチ関数（fetch_daily_quotes, fetch_financial_statements）。
    - Look-ahead Bias 対策として取得時刻（fetched_at）を UTC で記録。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等（ON CONFLICT DO UPDATE）での挿入を行う。
    - HTTP レスポンスの JSON デコード失敗時に詳細を含む例外を投げる。
    - ユーティリティ関数 _to_float / _to_int を実装（安全な型変換、"1.0" 等を考慮した処理）。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - 3層（Raw / Processed / Feature）＋ Execution レイヤのテーブル定義を実装。
  - Raw, Processed, Feature, Execution レイヤの主要テーブルを DDL として定義:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 頻出クエリ向けのインデックスを定義（銘柄×日付スキャンやステータス検索など）。
  - init_schema(db_path) を提供:
    - DB ファイルの親ディレクトリを自動作成（":memory:" を除く）。
    - すべての DDL / インデックスを実行（冪等）。
    - 初期化済みの DuckDB 接続を返す。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- 監査ログ・トレーサビリティ (src/kabusys/data/audit.py)
  - シグナル→発注→約定までの監査テーブルを実装:
    - signal_events（戦略が生成したシグナルの記録。棄却やエラーも含む）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ。order_type に関するチェック制約を実装）
    - executions（証券会社から返る約定の記録。broker_execution_id をユニークな冪等キーとして扱う）
  - すべての TIMESTAMP を UTC で保存するために init_audit_schema は "SET TimeZone='UTC'" を実行。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（いずれも冪等）。
  - 検索性能向上のためのインデックス群を定義（signal_events の日付・銘柄、order_requests の status、broker_order_id 等）。

- サブパッケージプレースホルダ
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py, src/kabusys/monitoring/__init__.py を追加（将来の実装に備えたパッケージ構造）。

### 改善 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 破壊的変更 (Breaking Changes)
- （初回リリースのため該当なし）

### 備考 (Notes)
- .env 読み込みロジックは OS の既存環境変数を意図せず上書きしないよう配慮されています。意図的に上書きしたい場合は .env.local を使用してください。
- J-Quants クライアントの設計には API レート制限・リトライ・トークン自動更新の考慮が含まれています。運用時は settings.jquants_refresh_token を必ず設定してください。
- DuckDB スキーマは複数のレイヤーと外部キー制約を含みます。初回は init_schema() → 必要に応じて init_audit_schema() を実行してデータベースを初期化してください。

--- 

（補足）本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして使用する際は、実装・動作確認結果や API 利用者向けの注意事項を追記してください。