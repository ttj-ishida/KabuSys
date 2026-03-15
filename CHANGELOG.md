# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

なお、本CHANGELOGはコードベース（初期実装）から推測して作成しています。実装上の設計方針や注意点も併記しています。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムの基盤モジュールを実装。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として追加。
  - public API として data, strategy, execution, monitoring を公開（各サブパッケージを分離）。

- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込みする機能を実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルート判定は .git または pyproject.toml を上位ディレクトリから探索。
  - .env ファイルの堅牢なパーサを実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - OS環境変数を保護するため、読み込み時の上書き制御（override/protected）を実装。
  - Settings クラスを追加し、アプリケーション設定値（J-Quants トークン、kabuステーション API、Slack 設定、DB パス、実行環境・ログレベル判定など）をプロパティ経由で提供。
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - Path 型での duckdb/sqlite パス取得（デフォルト値設定）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API から株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する機能を実装。
  - レート制限制御: 固定間隔スロットリングで 120 req/min を厳守する _RateLimiter を実装。
  - リトライロジック: 指数バックオフによる最大 3 回リトライ（対象: 408/429/5xx）、429 の場合は Retry-After ヘッダを尊重。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回のみ）、および ID トークンのモジュール内キャッシュを実装（ページネーション間で共有）。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements）を実装。pagination_key の重複検出でループ終了。
  - 取得タイミング（fetched_at）を UTC ISO 形式で記録し、Look-ahead Bias のトレースを可能にした設計。
  - DuckDB への永続化関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - ON CONFLICT DO UPDATE を利用した冪等的なINSERT/UPDATEを実装。
    - プライマリキー欠損行はスキップし、スキップ件数をログ出力。
    - 各保存関数は挿入・更新したレコード数を返す。
  - JSON デコードエラーや HTTP エラーの詳細なログ/例外処理を実装。
  - ユーティリティ変換関数を実装: _to_float, _to_int（空文字・None扱いや、"1.0" のような float 文字列処理を考慮）。

- DuckDB スキーマ定義 / 初期化（kabusys.data.schema）
  - DataLayer に基づくスキーマを定義（Raw / Processed / Feature / Execution 層）。
  - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
  - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature 層: features, ai_scores
  - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - テーブルに対する豊富な CHECK 制約（値域・NOT NULL・enum チェック等）を定義してデータ品質を担保。
  - 頻出クエリ用のインデックスを作成（code/date 検索やステータス検索など）。
  - init_schema(db_path) で DB ファイル親ディレクトリを自動作成し、全テーブル・インデックスを冪等に作成して接続を返す。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- 監査ログ / トレーサビリティ（kabusys.data.audit）
  - 戦略 → シグナル → 発注 → 約定までを UUID 連鎖で完全トレースできる監査テーブルを実装。
  - テーブル:
    - signal_events: 戦略が生成した全シグナル（棄却やエラー含む）を記録
    - order_requests: 発注要求ログ（order_request_id を冪等キーとして利用）、order_type 毎の制約（limit/stop による価格必須チェック）
    - executions: 実際の約定ログ（broker_execution_id をユニークな冪等キーとして扱う）
  - すべての TIMESTAMP を UTC で保存するように設計（init_audit_schema は SET TimeZone='UTC' を実行）。
  - インデックスを追加して検索効率を確保（signal/events の日付・戦略検索、status キュー検索、broker_order_id 紐付け等）。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（既存接続に対して監査テーブルを追加することが可能）。

- パッケージ構成
  - data サブパッケージに複数モジュールを実装（jquants_client, schema, audit）。
  - strategy, execution, monitoring サブパッケージのプレースホルダー __init__.py を追加（将来的な拡張を想定）。

### Changed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes / 補足
- 設計上の主な方針
  - API のレート制御・リトライ・トークン管理を組み込み、運用での堅牢性を高める。
  - DuckDB を単一の分析/永続ストアとして利用。init_schema は既存テーブルを壊さず冪等に実行。
  - 監査ログは削除せず記録を残す前提（FK は ON DELETE RESTRICT）で、追跡可能性を重視。
  - .env パーサは POSIX シェル風の記法を多くサポートするが、特殊ケースは想定外の挙動になる可能性あり。複雑な .env を使う場合は注意。
  - strategy / execution / monitoring の具体実装はこのリリースでは含まれておらず、今後追加予定。

---

（注）この CHANGELOG はコード内容から推測して作成しています。実際のコミット履歴や変更日付はリポジトリの履歴に合わせて調整してください。