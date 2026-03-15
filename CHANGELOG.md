# CHANGELOG

すべての注記は Keep a Changelog の形式に準拠しています。  
このプロジェクトの初期リリースに関する変更履歴を以下に示します。

すべての非公開のバグ修正や内部リファクタリングは明記していません。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を定義（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開モジュール一覧を __all__ に定義（data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動環境変数ロード機能:
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env を自動読み込み。
    - 読み込み順序: OS環境 > .env.local (上書き) > .env（未設定キーのみセット）。
    - 自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - OS 環境変数は保護され、.env による上書きから除外。
  - .env パーサ実装:
    - コメント行、export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理を考慮。
  - Settings で利用可能なプロパティを提供:
    - J-Quants / kabu ステーション / Slack / データベース (DuckDB/SQLite) / 環境 (development/paper_trading/live) / ログレベル
  - バリデーション:
    - 必須環境変数未設定時は ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の値チェック。

- J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - 主な機能:
    - ID トークン取得 (get_id_token)（refresh token を使用）。
    - 株価日足（fetch_daily_quotes）、財務データ（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）の取得。
    - ページネーション対応（pagination_key を使用し重複防止）。
    - レート制限 (120 req/min) を守る固定間隔スロットリング（内部 RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 Unauthorized を検出した場合はトークンを自動リフレッシュして 1 回リトライ。
    - JSON デコード失敗やネットワークエラーに対する明示的なエラーメッセージ。
    - モジュールレベルの ID トークンキャッシュ（ページネーションなどで共有）。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - すべて冪等（INSERT ... ON CONFLICT DO UPDATE）で重複を排除。
    - fetched_at を UTC ISO フォーマットで保存し、Look-ahead Bias 防止のため取得時刻を記録。
    - PK 欠損行はスキップし警告ログを出力。
  - 値変換ユーティリティ:
    - _to_float, _to_int 実装。空値や不正値は None を返却。_to_int は "1.0" のような文字列を float 経由で検査し、小数部がある場合は None を返す。

- DuckDB スキーマ (kabusys.data.schema)
  - データレイヤ構成に基づくスキーマ定義と初期化 API を実装。
    - 層: Raw / Processed / Feature / Execution
  - Raw Layer テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
  - Processed Layer テーブル:
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature Layer テーブル:
    - features, ai_scores
  - Execution Layer テーブル:
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 多数のインデックス定義（銘柄×日付検索、ステータス検索、外部キー結合等を加速）。
  - 初期化 API:
    - init_schema(db_path) — DB ファイルを作成（必要なら親ディレクトリ自動作成）し、全テーブル/インデックスを冪等に作成して接続を返す。
    - get_connection(db_path) — 既存 DB への接続を返す（スキーマ初期化は行わない）。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - 監査用テーブル群と初期化 API を実装。ビジネス要件に基づく監査階層をサポート（signal → order_request → execution）。
  - テーブル:
    - signal_events（戦略が生成したシグナルのログ）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ。種別ごとに入力チェックを実装）
    - executions（証券会社からの約定ログ。broker_execution_id を冪等キーとして扱う）
  - インデックス: 日付/銘柄検索、status スキャン、broker_order_id/broker_execution_id 関連など。
  - 初期化 API:
    - init_audit_schema(conn) — 既存の DuckDB 接続に監査ログテーブルを追加し、SET TimeZone='UTC' を実行（すべての TIMESTAMP を UTC で保存）。
    - init_audit_db(db_path) — 監査ログ専用 DB を初期化して接続を返す。

- 空のパッケージ初期化ファイル
  - kabusys.data.__init__, kabusys.execution.__init__, kabusys.strategy.__init__, kabusys.monitoring.__init__ を追加（将来の拡張のためのプレースホルダ）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 破壊的変更 (Deprecated / Removed / Security)
- （初回リリースのため該当なし）

### 注意事項 / マイグレーション
- .env 読み込み:
  - 自動読み込みはプロジェクトルートの検出に依存するため、配布後に CWD が変わっても正しく動作する設計。ただし、プロジェクトルートが検出できない場合は自動ロードをスキップします。
  - OS 環境変数は .env や .env.local による上書きを保護されます。テスト等で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ:
  - init_schema は冪等なので既存テーブルがあればスキップされます。初回のみ init_schema を呼び出してください。
  - 監査ログ初期化 (init_audit_schema) は既存接続を受け取り、UTC タイムゾーンを設定します。監査ログは削除しない前提（FK は ON DELETE RESTRICT）です。
- J-Quants API:
  - レート制限 (120 req/min) を内部で遵守します。大量データ取得の際は時間あたりのリクエスト数に注意してください。
  - 401 を検出した際の自動トークンリフレッシュは 1 回のみ行い、失敗時はエラーとなります。

---

今後のリリースでは、strategy / execution / monitoring 層の具体的な実装、テスト、ドキュメント、CI/CD 設定などを追記していく予定です。