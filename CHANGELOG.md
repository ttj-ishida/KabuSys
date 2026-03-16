# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
[Unreleased] セクションは将来の変更用に残しています。

## [Unreleased]

## [0.1.0] - 2026-03-16
初回リリース — 日本株自動売買システムのコアライブラリを追加。

### Added
- パッケージ初期化
  - kabusys パッケージの基本を導入（バージョン: 0.1.0）。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルや環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは __file__ を基点に `.git` または `pyproject.toml` を探索して特定（CWD 非依存）。
    - 自動ロードの無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` に対応（テスト等で利用）。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は .env を上書き）。
    - OS 環境変数を保護する protected キーセットの仕組みを実装。
  - .env パーサーの強化:
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
    - クォートなし値中のインラインコメント判定は直前が空白/タブの場合のみコメントと扱う。
  - Settings クラスを実装し、主要設定値をプロパティ経由で取得可能に:
    - J-Quants / kabu ステーション / Slack / DB パス等のプロパティ（必須値は未設定時に ValueError を送出）。
    - KABUSYS_ENV の許容値検証（development, paper_trading, live）。
    - LOG_LEVEL の許容値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - デフォルトの DuckDB/SQLite パスを設定。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアント実装:
    - エンドポイントから株価日足（OHLCV）、四半期財務（BS/PL）、JPX マーケットカレンダーを取得。
    - API レート制御（120 req/min）を固定間隔スロットリング方式で実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。対象ステータス: 408/429/5xx。
    - 429 の場合は Retry-After ヘッダを優先。
    - 401 受信時はリフレッシュトークンから id_token を再取得して 1 回リトライ（無限再帰防止仕様あり）。
    - ページネーション対応（pagination_key を追跡し重複防止）。
    - fetched_at を UTC (ISO 8601, "Z") で記録して Look-ahead Bias を防止。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で重複・更新を吸収。
    - PK 欠損行はスキップし、スキップ数をログに出力。
    - 型変換ヘルパー _to_float / _to_int を実装（空値/不正値は None、"1.0" 型の扱い等のルールあり）。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataPlatform の 3 層（Raw / Processed / Feature）＋ Execution 層に基づくスキーマを定義。
  - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions。
  - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
  - Feature レイヤー: features, ai_scores。
  - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - テーブルの制約（PRIMARY KEY、CHECK、外部キー）を細かく定義。
  - 検索性能を考慮した INDEX を多数定義（code/date 検索、ステータス検索、JOIN 最適化等）。
  - init_schema(db_path) によりファイル作成（親ディレクトリ自動作成）→ テーブル作成（冪等）し接続を返す。
  - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL の実装:
    - run_daily_etl: 市場カレンダー → 株価日足 → 財務 → 品質チェック の順で処理。
    - run_prices_etl / run_financials_etl / run_calendar_etl の差分更新ロジック。
      - 最終取得日を基に差分更新を行い、未取得時は最小データ日付（2017-01-01）から取得。
      - バックフィル日数の設定（デフォルト backfill_days=3）により後出し修正を吸収。
      - カレンダーは lookahead_days=90（日先読み）をデフォルトで取得。
    - ETLResult データクラスによる結果集約（取得数/保存数/品質問題/エラー一覧）。
    - 各ステップは独立してエラーハンドリング（1ステップ失敗でも他は継続、エラーは収集）。
    - 品質チェックはオプションで有効化可能（デフォルトで有効）。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - signal_events / order_requests / executions の監査テーブルを追加。
  - order_request_id を冪等キーとして設計し二重発注を防止。
  - すべての TIMESTAMP を UTC で保存する旨を明示（init_audit_schema では SET TimeZone='UTC' を実行）。
  - 発注状態遷移や詳細ステータス列を定義。
  - インデックス群を用意（signal/strategy/日付検索、status スキャン、broker_order_id 連携等）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。

- データ品質チェック (kabusys.data.quality)
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損（volume は対象外）を検出。検出時は severity="error"。
    - スパイク検出 (check_spike): 前日比（LAG を使用）での急騰・急落検出。閾値デフォルト 50%。
    - （今後）重複チェック・日付不整合検出等を想定する設計。
  - DuckDB の SQL を用いた効率的な実装、サンプル行（最大10件）取得の仕組み。

- モジュール構成
  - data パッケージを中心に主要機能を実装。strategy/execution パッケージは初期構成ファイル (空の __init__.py) を追加。

### Notes / Usage
- 環境変数の必須項目が未設定の場合、Settings の該当プロパティアクセス時に ValueError を送出します（例: JQUANTS_REFRESH_TOKEN や SLACK_BOT_TOKEN）。
- 自動 .env 読み込みはプロジェクトルートが検出できない場合はスキップされます（パッケージ配布後の安全性確保）。
- DuckDB 初期化時、ファイル版を指定した場合は親ディレクトリを自動作成します。":memory:" でインメモリ DB を使用可能。
- jquants_client は内部で id_token キャッシュを持ち、ページネーション中はキャッシュを共有して効率化する（force_refresh により更新可能）。
- ETL は品質チェックでエラー（重大）を検出しても自動的に全体を停止せず、結果として問題点を収集して返します。呼び出し元が結果を見て対処します。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- J-Quants のトークン処理で id_token をリフレッシュする際に無限再帰が起きないように設計（allow_refresh フラグ）。
- .env 読み込みは OS 環境変数を上書きしないデフォルト挙動で、上書き時も保護キー群を尊重。

----

今後のリリース案内:
- strategy 層（シグナル生成ロジック）と execution 層（証券会社接続・発注実行）の実装を進める予定。
- 追加の品質チェック、ニュース取得パイプライン、Slack/監視連携などを計画中。