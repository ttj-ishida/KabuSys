Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
この CHANGELOG は Keep a Changelog の形式に従っています（推定・コード内容に基づき作成）。

フォーマット
-----------
- 変更は "Added", "Changed", "Fixed", "Deprecated", "Removed", "Security" のカテゴリで分類しています。
- 日付はリリース日を表します（このファイルはコードベースの内容から推測して作成しています）。

未リリース
---------
- なし

[0.1.0] - 2026-03-16
--------------------
初回公開リリース（推定）。以下はコードベースから推測した主要な追加点・仕様。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）: バージョン情報と主要サブパッケージ（data, strategy, execution, monitoring）を公開。
- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出（.git または pyproject.toml による）により、CWD に依存しない自動ロードを実現。
  - .env のパース機能実装（コメント、exportプレフィックス、クォートやエスケープ対応）。
  - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。
  - Settings クラスで以下などの設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）、LOG_LEVEL（ログレベルのバリデーション）
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）を実装。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）を実装。
  - 401 応答時の自動トークンリフレッシュ（1回限り）と ID トークンのモジュールレベルキャッシュを実装。
  - ページネーション対応（pagination_key を用いた繰返しフェッチ）。
  - DuckDB 向けの冪等な保存関数（ON CONFLICT DO UPDATE）を提供:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ取得時の fetched_at（UTC）記録や型安全な変換ユーティリティ（_to_float/_to_int）を実装。
- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の多層スキーマを定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 制約（CHECK, PRIMARY KEY, 外部キー）および運用を考慮したインデックスを定義。
  - init_schema(db_path) による初期化関数と get_connection() を提供。":memory:" のサポートや親ディレクトリ自動作成を含む。
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL の実装（run_daily_etl）: 市場カレンダー取得 → 株価差分取得（backfill）→ 財務差分取得 → 品質チェック の流れを実現。
  - 差分更新ロジック: DBの最終取得日を基に自動で date_from を計算、デフォルトのバックフィル日数は 3 日。
  - 市場カレンダーの先読み（デフォルト 90 日）と営業日調整機能（_adjust_to_trading_day）。
  - 個別 ETL ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl（それぞれ取得数・保存数を返す）。
  - ETL実行結果を表す ETLResult データクラス。品質問題やエラーの収集・レポートを可能にする。
  - 品質チェック実行フラグや閾値を呼び出し側で指定可能（テスト容易性を考慮）。
- 監査ログ（audit）モジュール（src/kabusys/data/audit.py）
  - シグナル生成 → 発注要求 → 約定のトレーサビリティを確保する監査スキーマを定義。
  - signal_events, order_requests（冪等キー: order_request_id）, executions テーブルを提供。
  - すべての TIMESTAMP を UTC で保存する設計（init_audit_schema は SET TimeZone='UTC' を実行）。
  - init_audit_schema(conn) と init_audit_db(db_path) による初期化機能を提供。
- データ品質チェック（src/kabusys/data/quality.py）
  - 欠損データ（OHLC 欄の NULL）検出（check_missing_data）。
  - 株価スパイク検出（前日比の絶対値が閾値を超えるものを検出する check_spike）。デフォルト閾値は 50%。
  - QualityIssue データクラスにより、チェック名・対象テーブル・重大度・詳細・サンプル行を返す設計。
  - DuckDB を使った SQL ベースの効率的なチェックと、Fail-Fast ではなくすべての問題を収集する方針。

Changed
- （初回リリースのため該当なし）

Fixed
- .env パーサでの細かなケース（export prefix、クォート内のバックスラッシュエスケープ、インラインコメントの扱い、クォート無し時の '#' のコメント判定条件）に対応して堅牢化。

Security
- 認証周りの配慮:
  - ID トークンは必要に応じて自動リフレッシュし、無限再帰を避ける仕様（get_id_token 呼び出し時は allow_refresh=False）。
  - 環境変数読み込み時に OS 環境変数を保護する protected 機構を導入（.env を上書きしない既定動作）。

Notes / Migration / Operations
- 初回セットアップ:
  - DuckDB スキーマを作成するには data.schema.init_schema(db_path) を実行してください。
  - 監査ログを別 DB に作成する場合は data.audit.init_audit_db(db_path) を使用できます。
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings のプロパティ参照）。
  - 自動 .env ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途等）。
- UTC ポリシー:
  - 監査ログは UTC タイムスタンプで保存することを前提としています（init_audit_schema が TimeZone を設定）。
- バックフィル/品質チェック:
  - デフォルトのバックフィル日数は 3 日。必要に応じて run_daily_etl の引数で調整してください。
  - 品質チェックは ETL 後に実行し、重大な問題は ETLResult 経由で検出可能です（呼び出し側で処理方針を決定）。

Acknowledgements / TODO（コードから推測）
- strategy/, execution/, monitoring/ はパッケージに含まれるが現行コードでは未実装（プレースホルダ）。今後の戦略実装、発注処理、監視連携の追加が想定される。
- quality モジュールは重複チェック・日付不整合チェックなどを行う設計だが、将来的に追加のチェックや通知連携（Slack 等）を実装する余地がある。
- jquants_client の例外ハンドリングやログ粒度・監査連携の拡張、テスト用フックス（モックIDトークン注入等）は今後の改善点。

以上。コードの内容からの推測に基づく CHANGELOG です。追加のリリースや過去履歴があれば、その情報をいただければより正確に更新できます。