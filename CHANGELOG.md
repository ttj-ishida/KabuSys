CHANGELOG
=========

すべての重要な変更は本ファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

[0.1.0] - 2026-03-16
-------------------

Added
- 初回リリース。日本株自動売買システムのコア基盤を実装。
  - パッケージ構成
    - kabusys パッケージ（__version__ = 0.1.0）。
    - サブパッケージのプレースホルダ: data, strategy, execution, monitoring。
  - 環境設定管理（kabusys.config）
    - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して特定）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサは "export KEY=val" 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
    - Settings クラスを提供（jquants_refresh_token / kabu_api_* / slack_* / DB パス / 環境（development/paper_trading/live） / ログレベル等）。
    - 必須環境変数未設定時は明示的なエラーを送出。
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - API 呼び出しラッパー _request を実装（JSON デコード、エラーハンドリング）。
    - レート制御: 固定間隔スロットリングで 120 req/min を順守（_RateLimiter）。
    - 再試行ロジック: 指数バックオフ（最大 3 回）、ネットワークエラー・特定ステータスコード(408,429,5xx) に対するリトライ。
    - 401 発生時はリフレッシュトークンから id_token を自動再取得して 1 回リトライ（無限再帰を回避）。
    - ページネーション対応およびページ間での id_token キャッシュ共有。
    - データ取得関数:
      - fetch_daily_quotes (日足 OHLCV、ページネーション対応)
      - fetch_financial_statements (四半期財務データ)
      - fetch_market_calendar (JPX マーケットカレンダー)
    - DuckDB への保存関数（冪等、ON CONFLICT DO UPDATE を使用）:
      - save_daily_quotes -> raw_prices
      - save_financial_statements -> raw_financials
      - save_market_calendar -> market_calendar
    - 型変換ユーティリティ: _to_float, _to_int（安全な変換と不正値の除外）
    - ログ出力により取得・保存件数を通知
  - DuckDB スキーマ定義と初期化（kabusys.data.schema）
    - 3 層データモデル（Raw / Processed / Feature）＋ Execution 層を定義
    - 多数のテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）
    - 監査や検索パターンを考慮したインデックスを作成
    - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成とテーブル作成（冪等）
    - get_connection(db_path) で既存 DB へ接続
  - 監査ログ・トレーサビリティ（kabusys.data.audit）
    - 戦略→シグナル→発注要求→約定 の完全トレースを目的とした監査テーブル群を定義
      - signal_events, order_requests (冪等キー order_request_id), executions（broker_execution_id を冪等キーとして扱う）
    - UTC タイムゾーンの強制（init_audit_schema は SET TimeZone='UTC' を実行）
    - init_audit_schema(conn) / init_audit_db(db_path) を提供
    - ステータス遷移・入力制約（チェック制約）を定義し、監査上の一貫性を担保
  - データ品質チェック（kabusys.data.quality）
    - QualityIssue データクラスを定義（チェック名・テーブル・重大度・詳細・サンプル行）
    - 実装されたチェック:
      - check_missing_data: raw_prices の OHLC 欠損検出（volume は除外）
      - check_duplicates: raw_prices の主キー重複検出
      - check_spike: 前日比によるスパイク検出（LAG ウィンドウ関数、デフォルト閾値 50%）
      - check_date_consistency: 未来日付・market_calendar と整合しない非営業日のデータ検出
    - run_all_checks(conn, ...) で全チェック実行・集約（エラー／警告のログ出力）
    - 各チェックはサンプル行（最大 10 件）とカウント情報を返す（Fail-Fast ではなく検出結果を収集）
  - その他
    - デザイン文書（モジュール docstring）における設計原則や制約（レート限界、リトライ、UTC、冪等性等）の明示

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 環境変数のロードは既存 OS 環境変数を保護する仕組み（protected set）を採用。  
- J-Quants の id_token はモジュール内でキャッシュされ、401 時にのみ安全にリフレッシュする（無限リフレッシュ回避ロジックあり）。

Notes / 移行・利用上の注意
- 初回に DuckDB スキーマを作成する場合は data.schema.init_schema(db_path) を使用してください。監査テーブルは init_audit_schema() / init_audit_db() を使って追加可能です。
- 自動 .env 読み込みはデフォルトで有効です。テストなどで無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を設定していない場合、Settings は ValueError を投げます。.env.example を参照してください。
- J-Quants API のレート制限（120 req/min）および再試行ポリシー（最大 3 回）をハードコードしています。必要に応じて将来パラメータ化を検討してください。
- DuckDB での ON CONFLICT DO UPDATE により一般的な二重挿入は防げますが、外部ソースからの不整合発生時には data.quality のチェックで検出できます。

Known limitations
- strategy / execution / monitoring サブパッケージは現時点では初期化ファイルのみで、具体的な戦略実装・発注フローは未実装。
- 一部のチェック（market_calendar 参照等）は該当テーブルが存在しない場合にスキップされます（エラーにはならない）。
- 設定値や振る舞いの多くは現状ハードコード（閾値・再試行回数等）。運用に合わせて設定化を推奨。

以上。