# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載します。  
フォーマット: https://keepachangelog.com/ja/

注意: 以下はコードベースの現状から推測して作成した初期リリースの変更履歴です。

## [Unreleased]
- 

## [0.1.0] - 2026-03-16
初期リリース

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API を定義（data, strategy, execution, monitoring を __all__ に含める）。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を起点に探索）。
  - .env 自動ロード機能を実装（優先順: OS 環境変数 > .env.local > .env）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env 行パーサーを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応）。
  - 設定項目（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）を Settings のプロパティで提供。KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
  - settings オブジェクトをモジュール公開。

- J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。以下のデータ取得に対応:
    - 株価日足（OHLCV）
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー
  - レート制限保護: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
  - 再試行ロジック: 指数バックオフを用いた最大 3 回のリトライ（408/429/5xx 対象）。429 の場合は Retry-After ヘッダを優先。
  - 認証トークン自動リフレッシュ: 401 受信時にリフレッシュを 1 回行い再試行。モジュールレベルの ID トークンキャッシュを共有（ページネーション間でトークンを再利用）。
  - ページネーション対応で全件取得（pagination_key を利用）。
  - DuckDB へ保存するための冪等的な保存関数を提供（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE を利用して重複更新を抑止。
  - データ変換ユーティリティ（_to_float, _to_int）を実装し、安全に None を返す挙動を定義。

- DuckDB スキーマ (kabusys.data.schema)
  - DataPlatform の 3 層（Raw / Processed / Feature）および Execution 層を想定したテーブル定義を追加。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw レイヤーテーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed レイヤーテーブルを定義。
  - features, ai_scores など Feature レイヤーを定義。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など Execution レイヤーを定義。
  - パフォーマンス向けのインデックス群を追加（頻出クエリに対応する複数の CREATE INDEX）。
  - init_schema(db_path) による冪等なスキーマ初期化と接続取得機能を提供。親ディレクトリの自動作成や ":memory:" 対応あり。
  - 既存 DB へ接続する get_connection() を提供。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL パイプラインを実装（run_daily_etl）。
  - 個別ジョブを分離（run_calendar_etl, run_prices_etl, run_financials_etl）。各ジョブは差分取得ロジック（最終取得日からの差分、バックフィル）に対応。
  - 差分取得のデフォルト単位は営業日 1 日分。backfill_days により最終取得日から遡って再取得（デフォルト 3 日）。
  - 市場カレンダーは先読み（lookahead_days, デフォルト 90 日）を行い、営業日調整に利用。
  - ETL 実行結果を集約する ETLResult dataclass を追加（取得数・保存数・品質問題・エラーの収集、ヘルパー判定プロパティ含む）。
  - 各ステップは独立したエラーハンドリング（1 ステップ失敗でも他は継続）とし、エラー情報を収集して返す設計。
  - quality モジュールによる品質チェックの実行フックを追加（run_quality_checks フラグ）。

- 品質チェック (kabusys.data.quality)
  - データ品質チェックフレームワークを追加。QualityIssue データクラスで問題を表現（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（サンプル行の取得とカウント、重大度 "error"）。
    - check_spike: 前日比スパイク検出（LAG ウィンドウを使い絶対変動率が閾値を超えるレコードを検出）。
  - 設計上は重複チェック・日付不整合検出なども想定（モジュール文書に記載）。チェックは全件収集方式で Fail-Fast しない設計。
  - SQL はパラメータバインディングを使用して安全に実行。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - シグナルから約定までの監査用テーブル群を追加（signal_events, order_requests, executions）。
  - 冪等キー（order_request_id）や broker_execution_id のユニーク制約など、二重発注防止とトレーサビリティを考慮した設計。
  - 全 TIMESTAMP を UTC で扱う方針（init_audit_schema で SET TimeZone='UTC' を実行）。
  - init_audit_schema(conn) による既存接続への監査テーブル追加機能、init_audit_db(db_path) による専用 DB の初期化機能を提供。
  - 監査用インデックス群を定義（検索・ジョイン・キュー処理を想定）。

### Security
- 環境変数のロードにおいて OS 環境変数を保護する仕組みを導入（env 読み込み時に protected set を利用して上書きを抑止）。

### Notes / Behavior
- J-Quants API へのリクエストは固定間隔（60 / 120 秒）でスロットリングされ、過剰なリクエストを避ける実装になっています。
- save_* 関数は ON CONFLICT DO UPDATE を用いた冪等的な保存を行うため、再実行耐性があります。
- ETL は後出し修正（API の後出し更新）を吸収するためバックフィルを行います（デフォルト 3 日）。
- settings から取得する DB パスのデフォルトは duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db。
- .env のパースはクォート中のエスケープや行内コメントを考慮するため、一般的な .env フォーマットをかなり忠実にサポートしています。

### Known / TODO (コードコメントに基づく設計意図)
- quality モジュールの追加チェック（重複・日付不整合など）は設計に記載されているが、個別の実装は順次充実が必要。
- strategy / execution / monitoring の各パッケージは初期化ファイルがあるが、具体的な戦略・発注ロジックは今後実装想定。

---

参照:
- パッケージバージョン: kabusys.__version__ = 0.1.0
- 実装日付はコード提示日（2026-03-16）を使用して記載しています。