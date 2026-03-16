# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の原則に従い、Semantic Versioning を採用しています。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買システムのコアライブラリを追加。

### 追加
- パッケージのエントリポイントを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ に data, strategy, execution, monitoring を定義（strategy / execution / monitoring は初期プレースホルダとして __init__ を用意）。

- 環境設定モジュール（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml で探索）。
  - .env のパース機能を実装（コメント、export 形式、シングル／ダブルクォート、エスケープ対応）。
  - .env 読み込み順序: OS 環境変数 > .env.local > .env、既存 OS 環境変数は protected として上書きから保護。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供（必須変数取得の _require、各種プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV 検証、LOG_LEVEL 検証、is_live/is_paper/is_dev）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得を実装。
  - レート制限制御: 固定間隔スロットリング（120 req/min を想定、最小間隔を計算）。
  - retry・バックオフ:
    - 最大リトライ回数: 3
    - 指数バックオフ係数: 2.0
    - 再試行対象ステータス: 408, 429 および 5xx
    - 429 時は Retry-After ヘッダを優先
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）と再試行。get_id_token 呼び出し時の無限再帰を防止。
  - id_token のモジュールレベルキャッシュを導入（ページネーション間で共有可能）。
  - ページネーション対応 fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供。各関数は冪等（INSERT ... ON CONFLICT DO UPDATE）で fetched_at を記録。
  - 型変換ユーティリティ _to_float / _to_int（空値・不正値ハンドリング、"1.0" のような float 文字列対応、切り捨て回避ロジック）。

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - DataPlatform に基づく多層スキーマを実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約 (PRIMARY KEY, CHECK 等) を定義。
  - インデックス定義を含む（頻出クエリパターンに対する索引）。
  - init_schema(db_path) でディレクトリ作成 → テーブル作成（冪等）・DuckDB 接続を返す。
  - get_connection(db_path) による既存 DB 接続取得（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL のエントリポイント run_daily_etl を実装。
  - 処理フロー:
    1. 市場カレンダー ETL（先読み: デフォルト 90 日）
    2. 株価日足 ETL（差分更新 + バックフィル: デフォルト 3 日）
    3. 財務データ ETL（差分更新 + バックフィル）
    4. 品質チェック（オプション）
  - 差分更新の自動算出（raw テーブルの最終日を参照）、バックフィルで API の後出し修正を吸収。
  - ETL 実行結果を表す ETLResult データクラスを提供（品質問題・エラーを集約）。品質問題は severity によって判定可能。
  - 市場カレンダーを取得後、target_date を最も近い営業日に調整するヘルパー実装（最大 30 日さかのぼり）。
  - 各ステップは独立して例外処理され、1 ステップ失敗でも他は継続（Fail-Fast ではない設計）。

- 品質チェックモジュール（kabusys.data.quality）
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損を検出（volume は除外）。
    - スパイク検出 (check_spike): 前日比の変動率が閾値を超えるレコードを検出（デフォルト閾値 0.5 = 50%）。
    - （設計で重複チェック・日付不整合の検出も想定。実装の拡張ポイントあり）
  - 各チェックは問題を全件収集して QualityIssue リストを返す。DuckDB の SQL を用いて効率的に実行。

- 監査ログ（トレーサビリティ）モジュール（kabusys.data.audit）
  - シグナル〜発注〜約定の監査テーブルを定義・初期化する API を提供:
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求ログ、order_request_id を冪等キーとして使用）
    - executions（証券会社戻りの約定ログ）
  - テーブルに厳密な制約・チェックと外部キーを定義（ON DELETE RESTRICT）。
  - init_audit_schema(conn) と init_audit_db(db_path) を用意。init_audit_schema は SET TimeZone='UTC' を実行し、すべての TIMESTAMP が UTC で保存されることを保証。
  - 監査用インデックスを複数作成（処理待ち検索、紐付け、broker_order_id 検索など）。
  - ステータス遷移や、order_type による価格必須チェック（limit / stop / market）の整合性チェックを導入。

- その他
  - DuckDB ファイル作成時に親ディレクトリを自動作成するユーティリティを追加。
  - ロギング（logger）を各モジュールに導入して ETL、API 呼び出し、保存処理の状況を出力。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の注意点 / TODO
- strategy、execution、monitoring パッケージは現時点では初期化用 __init__ のみ（具体的な戦略ロジックや発注実装は今後追加予定）。
- quality モジュールは欠損・スパイク検出を実装済み。重複チェック・日付不整合チェックの追加や拡張は今後の課題。
- jquants_client の HTTP 層は urllib を使用した実装。将来的に requests 等へ切り替えることで実装を簡潔化することが可能。
- DuckDB の UNIQUE インデックスや NULL の扱いなど DB 特性に依存する箇所があるため、別 DB への移植には注意が必要。

---

今後のリリースでは、戦略実装、実際の発注ブリッジ（証券会社 API 連携）、監視・アラート（Slack 連携）、テストカバレッジと CI/CD の整備を計画しています。