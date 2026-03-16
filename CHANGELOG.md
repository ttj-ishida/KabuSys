# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

## [Unreleased]
（なし）

## [0.1.0] - 初回リリース
リリース日: 未設定

概要:
初版リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。データ取得・保存・品質チェック・ETLパイプライン・監査ログ（トレーサビリティ）・設定管理など、データプラットフォームと発注監査を構成する基盤を提供します。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのエントリポイントを追加。バージョンは 0.1.0 に設定。
- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数の自動読み込み（優先順位: OS環境変数 > .env.local > .env）。
  - .env パーサ実装（export 前置、クォート・エスケープ、インラインコメントの取り扱いに対応）。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数チェックのための Settings クラスを追加。主な必須キー:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - env 値の検証: KABUSYS_ENV（development, paper_trading, live）、LOG_LEVEL（DEBUG/INFO/...）の検証を実装。
  - デフォルトの DB パス設定: DUCKDB_PATH, SQLITE_PATH。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API からのデータ取得を行うクライアントを実装。
  - サポートするデータ:
    - 株価日足（OHLCV）: fetch_daily_quotes
    - 財務データ（四半期 BS/PL）: fetch_financial_statements
    - JPX マーケットカレンダー: fetch_market_calendar
  - 設計上の特徴:
    - API レート制限を守る固定間隔レートリミッタ（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を考慮）。
    - 401 受信時にリフレッシュトークンで自動リフレッシュして1回リトライ。
    - ページネーション対応（pagination_key を用いた取得）。
    - 取得時刻（fetched_at）を UTC で記録する設計方針。
  - DuckDB への保存関数を実装（冪等性: ON CONFLICT DO UPDATE）
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - ユーティリティ: 型変換ヘルパ（_to_float, _to_int）を実装。特殊ケース（"1.0"等）に配慮。
- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - 3 層構造のスキーマ定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 主要なインデックスを作成（銘柄×日付、ステータス検索、JOIN 支援等）。
  - init_schema(db_path) による初期化 & get_connection 関数を追加（:memory: 対応、親ディレクトリ自動作成）。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新（差分取得 + バックフィル）を行う ETL ジョブを実装:
    - run_prices_etl（株価差分取得保存）
    - run_financials_etl（財務差分取得保存）
    - run_calendar_etl（市場カレンダー差分取得保存、先読み機能）
    - run_daily_etl（上記をまとめた日次 ETL。品質チェックオプション付き）
  - デフォルトバックフィルは過去 3 日、カレンダー先読みは 90 日。
  - 差分判定のためのヘルパ関数: get_last_price_date / get_last_financial_date / get_last_calendar_date。
  - 営業日調整ヘルパ: _adjust_to_trading_day（非営業日を直近の営業日に調整）。
  - ETL 結果を返す ETLResult データクラス（取得件数、保存件数、品質問題、エラー一覧 等）。
  - 品質チェックモジュールを呼び出せる設計（品質チェックに失敗しても他のステップは継続）。
- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - シグナル → 発注要求 → 約定 のフローを UUID 連鎖で完全トレースする監査テーブルを実装:
    - signal_events, order_requests, executions
  - order_request_id を冪等キーとして設計。発注時の重複防止が可能。
  - 全 TIMESTAMP を UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）。
  - インデックスを多数定義（ステータス検索、日付/銘柄検索、broker_order_id 紐付け等）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。
- 品質チェックモジュール (src/kabusys/data/quality.py)
  - DataPlatform に基づく品質チェックを実装:
    - 欠損データ検出（raw_prices の OHLC 欠損: check_missing_data）
    - 異常値（スパイク）検出（前日比 > 閾値: check_spike）
    - （設計として重複チェック・日付不整合検出も掲示。）
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - 各チェックは問題を収集してリストで返す（Fail-Fast ではない設計）。
- パッケージ構成
  - data, strategy, execution, monitoring のエクスポート（パッケージ __all__ に含む）。
  - 空の __init__ をそれぞれのサブパッケージに用意（将来的な拡張向け）。

### 変更 (Changed)
- 初回リリースのため該当なし

### 修正 (Fixed)
- 初回リリースのため該当なし

### 既知の問題 / 注意点 (Known issues / Notes)
- パラメータ不一致の疑い:
  - src/kabusys/data/jquants_client.py の fetch_market_calendar は (id_token, holiday_division) を受け取るシグネチャですが、pipeline.run_calendar_etl は jq.fetch_market_calendar(id_token=id_token, date_from=date_from, date_to=date_to) のように date_from/date_to を渡しています。現状では fetch_market_calendar が date_from/date_to を受け取らないため、実行時に TypeError になる可能性があります。カレンダー取得のインターフェース整合性（date 範囲指定をサポートするか、pipeline 側を holiday_division に合わせるか）の対応が必要です。
- run_daily_etl の実行中、個々のステップは例外を捕捉して継続する設計です。重大な品質問題を検出しても ETL 自体は継続され、呼び出し元が ETLResult の has_quality_errors / has_errors を見て対処する必要があります。
- DuckDB の UNIQUE / NULL の扱いや CHECK 制約等は利用するバージョンや環境に依存する可能性があります（運用時の検証を推奨）。

### 開発者向けメモ
- 環境変数の自動ロードはパッケージ読み込み時に行われます。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑制できます。
- J-Quants の認証はリフレッシュトークンを利用する設計です。JQUANTS_REFRESH_TOKEN を設定しておく必要があります。
- DuckDB スキーマは init_schema() で作成してください。監査ログは init_audit_schema() を追加で呼び出します。
- ETL / API 呼び出しのレート制御やリトライは jquants_client 側で実装済みです。ロギングにより失敗時の原因追跡が可能です。

---

（次回リリースでは、fetch_market_calendar の引数整合性修正、追加の品質チェック（重複・未来日付検出等）の実装、strategy / execution レイヤーの実装拡充を予定しています。）