# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

履歴
----

### [0.1.0] - 2026-03-16

Added
- 基本パッケージ構成
  - パッケージ名: kabusys（__version__ = 0.1.0）
  - 公開サブパッケージ: data, strategy, execution, monitoring

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動ロード（プロジェクトルート判定: .git または pyproject.toml を探索）
  - 自動ロード順序: OS 環境変数 > .env.local > .env
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ実装:
    - export KEY=val 形式対応
    - シングル／ダブルクォート内のエスケープ処理
    - インラインコメント処理（クォート無し時は直前が空白/タブの '#' をコメントとみなす）
  - _load_env_file による上書き制御（override）と保護キーセット（protected）対応
  - Settings クラスでアプリ設定をラップ:
    - J-Quants / kabu / Slack / DB パスなどのプロパティを提供
    - 必須環境変数未設定時は ValueError を送出（_require）
    - KABUSYS_ENV の有効値検証（development, paper_trading, live）
    - LOG_LEVEL の有効値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - duckdb/sqlite パスは Path 型で返却（ホーム展開対応）

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアント実装（/v1 ベース）
  - レート制御: 120 req/min を満たす固定間隔スロットリング（_RateLimiter）
  - リトライ戦略:
    - 指数バックオフ（base=2.0 秒）、最大 3 回
    - リトライ対象: HTTP 408, 429, および 5xx
    - 429 の場合は Retry-After ヘッダ優先
    - ネットワークエラー（URLError/OSError）もリトライ
  - 認証トークン処理:
    - refresh_token から id_token を取得する get_id_token
    - 401 受信時は id_token を自動リフレッシュして 1 回リトライ（無限再帰防止フラグ allow_refresh）
    - モジュールレベルの id_token キャッシュ（ページネーション間で共有可能）
  - ページネーション対応の取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - HTTP レスポンス JSON パース失敗時は明示的エラー

- DuckDB 保存ロジック（jquants_client の save_*）
  - save_daily_quotes, save_financial_statements, save_market_calendar を提供
  - 挿入は冪等（ON CONFLICT DO UPDATE）で重複を回避
  - fetched_at を UTC (ISO 8601 Z) 形式で記録し、Look-ahead Bias 防止
  - PK 欠損行はスキップしてログ出力
  - 型変換ユーティリティ: _to_float, _to_int（"1.0" のような表現を考慮、非整数小数は None）

- DuckDB スキーマ定義 / 初期化（kabusys.data.schema）
  - 3層アーキテクチャに基づくテーブル群を定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を付与
  - 頻出クエリ向けのインデックスを作成
  - init_schema(db_path) でディレクトリ自動作成とテーブル/インデックスの冪等作成
  - get_connection(db_path) により既存 DB への接続を取得（スキーマ初期化は行わない）

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL を実現する run_daily_etl を実装（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新ロジック:
    - DB の最終取得日を基に date_from を自動算出（未取得時は _MIN_DATA_DATE = 2017-01-01）
    - バックフィル日数デフォルト 3 日（backfill_days）で後出し修正を吸収
  - 市場カレンダーは先読み（lookahead_days デフォルト 90 日）して営業日調整に利用
  - 各ステップは個別に例外処理され、1ステップ失敗でも他ステップを継続（エラーログ収集）
  - id_token を注入可能（テスト容易性）
  - ETLResult dataclass を導入:
    - 取得数／保存数、品質問題、エラー一覧を保持
    - has_errors / has_quality_errors プロパティ
    - to_dict() は品質問題をシリアライズ可能な形で返す
  - 主要なジョブ関数:
    - run_prices_etl, run_financials_etl, run_calendar_etl（差分取得 + 保存）

- 監査 / トレース（kabusys.data.audit）
  - シグナル→発注→約定のトレーサビリティを担保する監査スキーマを定義:
    - signal_events（戦略が出力した全シグナル）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社提供の約定を記録、broker_execution_id をユニークとする）
  - 各種制約・ステータス列・created_at/updated_at を採用し監査証跡を保証
  - DuckDB 上で UTC タイムゾーン固定（init_audit_schema 内で SET TimeZone='UTC'）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供
  - 監査向けのインデックスも作成（status や日付検索の高速化）

- データ品質チェック（kabusys.data.quality）
  - QualityIssue dataclass を導入（check_name, table, severity, detail, rows）
  - 実行可能なチェックを提供（SQL ベース、DuckDB 接続を使用、パラメータバインド採用）
    - 欠損データ検出: raw_prices の OHLC 欄の欠損を検出（check_missing_data、重大度 "error"）
    - スパイク検出: 前日比の絶対変動率が閾値（デフォルト 50%）を超えるレコードを検出（check_spike）
    - （設計上）重複チェック、日付不整合（将来日付・非営業日）なども想定／実装方針あり
  - 各チェックは問題を全件収集して返し、呼び出し元が重大度に応じた対応を決定できる設計

Other
- ロギングや警告出力を多数に追加し運用時のトラブルシュートを支援
- SQL はパラメータバインド（?）で実行し、インジェクションリスクを低減
- 多くの機能で冪等性と再実行安全性を重視（ON CONFLICT / 冪等キー / キャッシュ設計 など）

Fixed
- なし（初期リリース）

Changed
- なし（初期リリース）

Security
- なし（初期リリース）

Notes / 今後の改善候補（コードから推定）
- quality.run_all_checks 等の統合エントリ（pipeline が呼ぶ機能）の整備とドキュメント化
- strategy・execution・monitoring パッケージの実装（現状は __init__ のみ）
- 単体テストおよび外部 API 呼び出しをモックするテストケースの整備
- エラーやメトリクスを収集するためのモニタリング連携（Prometheus / Sentry 等）
- 大規模データ処理時の性能チューニング（DuckDB のパーティショニングや並列処理）

--- 

(この CHANGELOG は提供されたソースコードの内容から推測して作成しています。詳細なリリースノートは実際のコミット履歴・追加ドキュメントに基づいて更新してください。)