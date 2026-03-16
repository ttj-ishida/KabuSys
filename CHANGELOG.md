CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載します。  
日付は本ドキュメント作成日 (2026-03-16) を使用しています。

フォーマット:
- Unreleased: 今後の変更（現時点では空）
- 各バージョン: そのリリースで追加・変更・修正された内容

Unreleased
----------
（なし）

0.1.0 - 2026-03-16
-----------------

初回リリース — KabuSys 日本株自動売買システムの基礎モジュール群を実装しました。

Added
- パッケージ基礎
  - kabusys パッケージを追加。公開バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を含めたモジュール構成を定義。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの検出は .git または pyproject.toml に基づく（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いに対応。
    - 既存 OS 環境変数は protected として上書き回避（.env.local は override=True だが protected は保護）。
  - Settings クラスを提供。プロパティ経由で必須設定値を取得（未設定時は ValueError）。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を想定。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）、実行環境（KABUSYS_ENV: development|paper_trading|live）、ログレベル（LOG_LEVEL）等の既定値とバリデーションを実装。
    - is_live / is_paper / is_dev 判定プロパティを提供。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API の基本操作（認証・ページネーション・取得・保存）を実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を厳守する RateLimiter を実装。
  - 再試行ロジック:
    - 指数バックオフ、最大 3 回のリトライ（デフォルト）。
    - リトライ対象ステータス: 408, 429, 5xx（429 は Retry-After を尊重）。
    - ネットワークエラー (URLError / OSError) に対してもリトライ。
  - トークン処理:
    - refresh token から id_token を取得する get_id_token（POST /token/auth_refresh）。
    - 401 受信時は id_token を自動リフレッシュして 1 回だけリトライ（無限再帰回避のため allow_refresh 制御）。
    - モジュールレベルで id_token をキャッシュし、ページネーション間で共有。
  - データ取得 API:
    - fetch_daily_quotes: 株価日足（OHLCV）をページネーション対応で取得。
    - fetch_financial_statements: 四半期財務データ（BS/PL）をページネーション対応で取得。
    - fetch_market_calendar: JPX マーケットカレンダーを取得（祝日 / 半日 / SQ 判定）。
    - 取得時にログ出力（取得件数）。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes: raw_prices テーブルへ保存（ON CONFLICT DO UPDATE）。fetched_at を UTC ISO (Z) で記録。PK 欠損行をスキップして警告ログ。
    - save_financial_statements: raw_financials テーブルへ保存（ON CONFLICT DO UPDATE）。fetched_at を記録。PK 欠損行のスキップ。
    - save_market_calendar: market_calendar テーブルへ保存（ON CONFLICT DO UPDATE）。HolidayDivision に基づき is_trading_day / is_half_day / is_sq_day を判定。
  - ユーティリティ: 型変換関数 _to_float / _to_int を実装（安全な変換と不正値の None 化、"1.0" のような文字列対応等）。

- DuckDB スキーマ (kabusys.data.schema)
  - DataSchema.md を意識した 3+1 層スキーマ（Raw / Processed / Feature / Execution）を定義。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw レイヤー。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤー。
  - features, ai_scores 等の Feature レイヤー。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等の Execution レイヤー。
  - パフォーマンス向けインデックス群を定義（銘柄×日付スキャンやステータス検索等の想定クエリに最適化）。
  - init_schema(db_path) でディレクトリ自動作成・テーブル作成（冪等）、get_connection(db_path) で既存 DB への接続を提供。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL の総合エントリ run_daily_etl を実装。処理順序:
    1. 市場カレンダー ETL（先読み lookahead）
    2. 株価日足 ETL（差分 + backfill）
    3. 財務データ ETL（差分 + backfill）
    4. 品質チェック（オプション）
  - 差分更新ロジック:
    - DB の最終取得日を基に差分を自動算出。初回ロードは 2017-01-01 から。
    - backfill_days（デフォルト 3）で最終取得日の数日前から再取得して API の後出し修正を吸収。
    - カレンダーは target_date + lookahead_days（デフォルト 90）まで先読み。
  - 各 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）を提供。各ジョブは取得件数と保存件数を返す。
  - ETLResult データクラスを導入。target_date, fetched/saved カウント、品質問題リスト、エラーリストを含む。to_dict で監査ログ向け辞書化。
  - エラーハンドリング方針:
    - 各ステップは独立して例外をキャッチし、処理を継続（Fail-Fast ではない）。発生したエラーは ETLResult.errors に蓄積。

- 監査ログ (kabusys.data.audit)
  - 戦略 → シグナル → 発注 → 約定 のトレーサビリティを保証する監査スキーマを実装。
  - テーブル:
    - signal_events（シグナル生成ログ: strategy_id, decision, reason, created_at）
    - order_requests（冪等キー order_request_id、価格チェック制約、status, error_message, created_at/updated_at）
    - executions（broker_execution_id を一意キーとして証券会社約定を記録）
  - init_audit_schema(conn) で UTC タイムゾーン設定とテーブル/インデックスの初期化（冪等）。
  - init_audit_db(db_path) で専用監査 DB を作成可能。
  - 設計原則: created_at を全テーブルに持たせ削除しない方針、ON DELETE RESTRICT を採用。

- 品質チェック (kabusys.data.quality)
  - DataPlatform の品質チェック実装。
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の必須 OHLC 欄の欠損検出（重大度: error）とサンプル取得。
    - check_spike: 前日比のスパイク（デフォルト閾値 50%）を LAG ウィンドウで検出し、サンプルを返却。
    - （重複チェック、日付不整合などは設計方針に言及。既存のインターフェースに沿って追加実装可能）
  - 各チェックは DuckDB の SQL（パラメータバインド）で効率的に実行し、全件収集方針を採用。

Documentation / Notes
- すべての timestamp は UTC を想定。監査ログ初期化時に SET TimeZone='UTC' を実行。
- DuckDB に対する INSERT は可能な限り ON CONFLICT DO UPDATE で冪等を確保。
- ETL と品質チェックは分離され、呼び出し元が重大度に応じて処理を止めるかどうかを決定できる設計。
- 必須環境変数が未設定の場合、Settings のプロパティは ValueError を送出するため、実運用前に .env を準備すること。
- .env のパース挙動は厳格に実装されているため、引用符やエスケープ、コメントの扱いに注意。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Security
- J-Quants の id_token をキャッシュしつつ、401 時の自動リフレッシュで漏洩リスクを増やさないよう allow_refresh フラグで無限再帰を防止。  
- .env ファイル読み込みでは既存の OS 環境変数を保護（protected set）して誤って上書きしない実装。

Migration Notes
- 初回利用時は data.schema.init_schema(db_path) を呼んでスキーマを作成してください。
- 監査専用 DB を使う場合は data.audit.init_audit_db(db_path) を利用してください。
- 自動 .env 読み込みをテスト等で無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

今後検討事項（想定）
- quality モジュールへの追加チェック（重複チェック、未来日／営業日外データ検出など）の拡充。
- strategy / execution / monitoring モジュールの実装充実（現状はパッケージ構成のみ）。
- より柔軟なレートリミッタ（トークンバケット等）の導入やメトリクス出力。
- エラー分類や通知（Slack 連携）の実装（Settings に Slack 設定はあるが、送信実装は今後）。

貢献者
- 実装コードに基づく自動生成ドキュメント（初期実装）。

--- 

本 CHANGELOG はコード内容から推測して作成しました。実際のリリースノートとして使用する場合は、差分やコミット履歴に基づいて適宜調整してください。