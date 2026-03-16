CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式で記載しています。  
慣例に従い、バージョンごとに「Added / Changed / Fixed / Security」などのセクションで要約しています。

Unreleased
----------

- なし

0.1.0 - 2026-03-16
------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基本機能を実装。
- パッケージ構成を導入:
  - kabusys.config: 環境変数/設定読み込みと Settings 抽象化
    - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能
    - export KEY=val 形式やクォート／エスケープ、インラインコメントなどを考慮した堅牢な .env パーサ
    - 必須設定取得用の _require と Settings クラス（J-Quants、kabu API、Slack、DBパス、実行環境、ログレベルなど）
    - 環境値の検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）
- データ層（kabusys.data）
  - jquants_client: J-Quants API クライアント実装
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）
    - 冪等性とページネーション対応の fetch_* API（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
    - 再試行（指数バックオフ、最大 3 回。HTTP 408/429/5xx およびネットワークエラーをリトライ対象）
    - 401 受信時に refresh token を用いた自動トークン更新を 1 回だけ行うロジック
    - レスポンスの JSON デコードとエラーハンドリング強化
    - DuckDB へ保存する idempotent な保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE を使用
    - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を抑止
    - 値変換ユーティリティ (_to_float, _to_int) を実装し不正値に寛容に対応
  - schema: DuckDB スキーマ定義と初期化
    - Raw / Processed / Feature / Execution レイヤのテーブル定義を実装（raw_prices, raw_financials, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）
    - 監査・実行に関するテーブル、必要なチェック制約、外部キーを定義
    - 検索性能を考慮したインデックス群を定義
    - init_schema(db_path) による冪等的なスキーマ初期化と get_connection を提供
  - pipeline: ETL パイプライン
    - 日次 ETL (run_daily_etl) を実装（市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）
    - 差分更新ロジック（DBの最終取得日を基に自動で date_from を決定）、backfill_days による後出し修正吸収
    - 市場カレンダーの先読み (lookahead_days) 機構
    - 各ステップは独立したエラーハンドリングとし、1 ステップ失敗でも他ステップを継続（結果は ETLResult.errors に蓄積）
    - ETL 結果を表す dataclass (ETLResult) を導入（品質問題やエラー集約、辞書変換をサポート）
  - quality: データ品質チェック
    - 欠損データ検出（OHLC 欄の欠損検出）
    - スパイク検出（前日比変動率の閾値検出）
    - 重複／日付不整合チェック等（設計に基づく実装方針と一部チェック）
    - QualityIssue データクラスによる問題表現（check_name, table, severity, detail, rows）
    - 各チェックは全件収集型（Fail-Fast ではなく呼び出し元で判定）
  - audit: 監査ログ / トレーサビリティ
    - signal_events / order_requests / executions といった監査テーブル群を定義
    - order_request_id を冪等キーとして二重発注防止（制約・チェックの追加）
    - すべての TIMESTAMP を UTC で扱う（init_audit_schema で SET TimeZone='UTC'）
    - init_audit_schema(conn) / init_audit_db(db_path) の初期化ユーティリティを提供
- パッケージ API
  - top-level __init__.py により kabusys.data / strategy / execution / monitoring を公開対象として定義
- ロギング
  - 各モジュールに logger を導入し重要な操作（取得件数、保存件数、リトライ、警告・エラー）を記録

Changed
- 該当なし（初回リリース）

Fixed
- 該当なし（初回リリース）

Security
- 環境変数の扱いにおいて OS 環境変数を保護するため .env ロード時に protected セットを利用（既存の環境変数を上書きしないデフォルト動作）
- .env 自動読み込みは環境変数で明示的に無効化可能（テスト等での安全対策）

Notes / その他
- DuckDB を前提とした実装で、init_schema により必要なディレクトリを自動作成する（":memory:" をサポート）
- J-Quants API の利用に際しては JQUANTS_REFRESH_TOKEN 等の必須環境変数を設定する必要あり（Settings._require によるチェック）
- 設計ドキュメント（DataPlatform.md, DataSchema.md 等）に基づく実装を反映（ソース内コメント・docstring に記載あり）
- 現時点では strategy / execution / monitoring の具象実装はエントリポイントを確保する形（パッケージとして公開）にとどまり、将来的な拡張を想定

既知の制限
- strategy / execution / monitoring の具体的戦略ロジックや取引所 API 連携の具象実装は含まれていない（監査・テーブル設計は提供）
- quality モジュールのチェックは主要な検査を実装しているが、運用で新たなチェックを追加する余地がある
- ネットワーク・API の堅牢化は行っているが、実運用では追加の監視・リトライポリシー調整が必要になる場合がある

以上。