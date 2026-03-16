Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

フォーマット
-----------
* 追加 (Added)
* 変更 (Changed)
* 修正 (Fixed)
* 削除 (Removed)
* セキュリティ (Security)

Unreleased
----------
（現在なし）

0.1.0 - 2026-03-16
------------------
初回リリース。日本株自動売買プラットフォームの基盤モジュール群を導入します。以下の主要コンポーネントと機能を含みます。

Added
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" として設定。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索して行う（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。
  - .env パーサーは以下に対応:
    - export KEY=val 形式
    - シングル／ダブルクォート対応（バックスラッシュエスケープを考慮）
    - 行末コメントの扱い（クォートあり/なしの違いを適切に処理）
    - 無効行（空行、コメント、等）を無視
    - 読み込み失敗時は警告を出す
    - OS 環境変数を保護する protected セットをサポート（上書き制御）
  - Settings クラスでアプリ設定を提供（プロパティベース）
    - 必須環境変数の取得（未設定時は ValueError を投げる）
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値を持つ設定:
      - KABUS_API_BASE_URL のデフォルト: http://localhost:18080/kabusapi
      - DUCKDB_PATH / SQLITE_PATH のデフォルトパス
      - KABUSYS_ENV の許容値チェック: development / paper_trading / live
      - LOG_LEVEL の許容値チェック: DEBUG / INFO / WARNING / ERROR / CRITICAL
    - ヘルパープロパティ: is_live / is_paper / is_dev

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出し用ユーティリティを実装:
    - ベースURL: https://api.jquants.com/v1
    - 固定間隔スロットリングによるレート制御（_RateLimiter、120 req/min に対応）
    - リトライ戦略: 最大 3 回、指数バックオフ（2^attempt 秒）、対象ステータス 408/429/5xx
      - 429 の場合は Retry-After ヘッダを優先
    - 401 Unauthorized を受けた場合は id_token を自動リフレッシュして 1 回リトライ（無限再帰防止）
    - ページネーション対応（pagination_key を利用）
    - JSON デコードエラーやネットワークエラーの取り扱い（詳細ログ/例外）
    - モジュールレベルで id_token をキャッシュし、ページネーション間で共有
  - 認証ヘルパー: get_id_token(refresh_token=None)（POST /token/auth_refresh）
  - データ取得関数:
    - fetch_daily_quotes (株価日足、ページネーション対応)
    - fetch_financial_statements (四半期財務、ページネーション対応)
    - fetch_market_calendar (JPX マーケットカレンダー)
  - DuckDB へ冪等的に保存する関数:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE を用いた保存
      - fetched_at を UTC ISO フォーマットで保存（Look-ahead bias 対策のため取得時刻を記録）
      - PK 欠損行はスキップし警告を出す
    - save_financial_statements: raw_financials テーブルへ同様に保存
    - save_market_calendar: market_calendar テーブルへ同様に保存（HolidayDivision を解釈して is_trading_day / is_half_day / is_sq_day を決定）
  - ユーティリティ変換関数:
    - _to_float, _to_int（入力の安全な型変換。float 文字列→int の取り扱いに注意）

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - 3 層（Raw / Processed / Feature）＋ Execution 層を含むスキーマを定義。
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature 層: features, ai_scores
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 多数のデータ型制約（CHECK/NOT NULL/PRIMARY KEY/FOREIGN KEY）を定義し、データ整合性を強化
  - 頻出クエリに対するインデックスを定義
  - init_schema(db_path) で DB とテーブルを冪等に作成（親ディレクトリ自動作成）
  - get_connection(db_path) による単純接続関数

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL のワークフローを実装（run_daily_etl）
    - 処理順:
      1. 市場カレンダー ETL（先読み: デフォルト 90 日）
      2. 株価日足 ETL（差分更新 + バックフィル: デフォルト 3 日）
      3. 財務データ ETL（差分更新 + バックフィル）
      4. 品質チェック（オプション）
    - 差分取得ロジック:
      - DB の最終取得日から backfill_days 分さかのぼって再取得し、API の後出し修正を吸収
      - 初回は J-Quants が提供する最小日付（2017-01-01）から取得
    - カレンダーの先読みは target_date + lookahead_days まで取得
    - 各ステップは独立したエラーハンドリング（1 ステップ失敗でも他は継続）。結果は ETLResult に集約
  - ヘルパー:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _adjust_to_trading_day: 非営業日の場合、直近の営業日に調整（カレンダーが未取得の場合はフォールバックでそのまま返す）
  - ETLResult クラス: 取得数/保存数、品質問題、エラー一覧などを保持。品質問題はシリアライズ可能な辞書に変換可能

- データ品質チェック (kabusys.data.quality)
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）
  - チェック実装:
    - check_missing_data: raw_prices の OHLC 欠損を検出（volume は許容）
    - check_spike: 前日比スパイク（デフォルト閾値 50%）を LAG ウィンドウで検出
    - （設計により重複チェック・日付不整合チェック等を想定／拡張可能）
  - すべてのチェックはサンプル行（最大 10 件）とともに全件収集し、呼び出し元が重大度に応じて判断できる設計

- 監査ログ / トレーサビリティ (kabusys.data.audit)
  - シグナル〜約定までのトレーサビリティを担保する監査スキーマを実装
    - signal_events（戦略が生成したすべてのシグナルを記録）
    - order_requests（冪等キー order_request_id を持つ発注要求）
    - executions（証券会社からの約定ログ、broker_execution_id をユニークとして冪等化）
  - ステータス遷移や各種制約（CHECK、FK、created_at/updated_at）を定義
  - init_audit_schema(conn) / init_audit_db(db_path) により監査テーブルを冪等に初期化
  - 全 TIMESTAMP は UTC 保存（init_audit_schema は SET TimeZone='UTC' を実行）
  - 細かなインデックスを追加し、クエリ効率を向上

Other notes / Usage hints
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token 内で使用）
  - KABU_API_PASSWORD: kabuステーション API 用パスワード
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視用): data/monitoring.db
- ETL デフォルトパラメータ:
  - backfill_days: 3
  - calendar_lookahead_days: 90
  - spike_threshold: 0.5 (50%)
- ロギングや例外は適切に記録される設計で、ETL は Fail-Fast ではなく問題を収集して報告する方針
- セキュリティ:
  - トークンの自動リフレッシュにより 401 発生時に短時間で復旧するが、失敗時は明確な例外を返す
  - .env の読み込みは OS 環境変数を保護（上書き不可）する仕組みあり

Changed
- （該当なし。初回リリースのため変更履歴はなし）

Fixed
- （該当なし。初回リリースのため修正履歴はなし）

Security
- （該当なし）

Known limitations / TODO
- strategy, execution, monitoring の各サブパッケージは __init__ が存在するが具体的実装は本バージョンでは含まれていない（拡張予定）。
- quality モジュールは基礎的チェックを提供。重複チェックや日付不整合チェックは設計に含まれるが追加実装やチューニングが必要。
- 現在のネットワーク・HTTP ラッパーは urllib を使用。将来的に requests 等への切替や非同期化を検討。

貢献・バグ報告
----------------
バグ報告や機能要望は issue を作成してください。API 使用上の注意（レート制限等）に関する質問はドキュメント参照または issue で相談してください。