CHANGELOG
=========
すべての重要な変更点はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
（https://keepachangelog.com/ja/1.0.0/）

[Unreleased]
-------------

[0.1.0] - 2026-03-16
--------------------
Added
- 初期公開: kabusys パッケージの初期実装を追加。
  - パッケージのエントリポイントを設定（src/kabusys/__init__.py、バージョン 0.1.0）。

- 環境設定モジュール（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの検出は __file__ を基点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - 読み込み優先順位は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - 既存 OS 環境変数を保護する protected オプションを実装。
  - Settings クラスを提供（必須値取得時に明示的エラーを発生させる _require、値検証を含む）。
    - J-Quants、kabu API、Slack、DB パスや実行環境（development/paper_trading/live）、ログレベル検証等のプロパティを実装。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する API クライアントを実装。
  - 設計上の特徴:
    - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）を導入。
    - リトライ（指数バックオフ、最大 3 回）を実装。対象ステータス: 408, 429, 5xx。429 時は Retry-After を優先。
    - 401 受信時は自動でリフレッシュトークンから ID トークンを取得して一回リトライ（無限再帰防止の allow_refresh）。
    - ページネーション対応（pagination_key の追跡）を実装。
    - 取得時刻（fetched_at）を UTC ISO 形式で記録し、Look-ahead Bias に対処。
    - モジュールレベルの ID トークンキャッシュを保持し、ページネーション間でトークンを共有。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。
    - 冪等性を担保するため ON CONFLICT DO UPDATE を使用。
    - PK 欠損行はスキップし、スキップ件数はログ出力。
  - 数値変換ユーティリティ（_to_float, _to_int）を実装。float 文字列からの int 変換における安全性を考慮。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - 3 層（Raw / Processed / Feature）+ Execution 層のテーブルを定義する DDL を実装。
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 参照整合性・チェック制約やカラム型（DECIMAL 精度・CHECK 制約）を定義。
  - 頻出クエリ向けのインデックスを作成（コード×日付、ステータス検索など）。
  - init_schema(db_path) と get_connection(db_path) を提供（init_schema は親ディレクトリの自動作成を行う）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL のエントリ run_daily_etl を実装。処理フロー:
    1. 市場カレンダー ETL（先読み）
    2. 株価日足 ETL（差分 + バックフィル）
    3. 財務データ ETL（差分 + バックフィル）
    4. 品質チェック（オプション）
  - 差分更新ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）を実装。
  - 各ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）は差分取得・保存を行い、backfill_days と lookahead_days の設定をサポート。
  - ETLResult データクラスを導入し、取得数・保存数・品質問題・エラーの集約を提供。
  - 各ステップは個別に例外を捕捉して ETL 全体の継続を可能にする（Fail-Fast ではない設計）。

- 品質チェックモジュール（src/kabusys/data/quality.py）
  - QualityIssue データクラスを導入。
  - チェック実装:
    - 欠損データ検出（check_missing_data）: raw_prices の OHLC 欠損を検出（volume は除外）。
    - スパイク検出（check_spike）: 前日比の変化率を LAG ウィンドウで計算し、閾値超過を検出（デフォルト 50%）。
    -（設計上）重複チェック、日付不整合検出も仕様に含む（SQL ベース、パラメータバインドを使用）。
  - 各チェックは問題を全件収集して QualityIssue リストを返す設計。

- 監査ログ（トレーサビリティ）モジュール（src/kabusys/data/audit.py）
  - シグナル → 発注要求 → 約定の完全トレースを目的とした監査テーブルを実装。
    - signal_events（戦略のシグナルログ）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ、複数タイプのチェック制約）
    - executions（証券会社からの約定ログ、broker_execution_id をユニーク鍵として冪等性）
  - 監査用インデックス群を定義（status 検索、signal_id/日付の検索、broker_order_id 紐付けなど）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。
  - 全 TIMESTAMP を UTC で保存するため init_audit_schema で SET TimeZone='UTC' を実行。

- モジュール構成
  - data, strategy, execution, monitoring（パッケージ公開名に含める）。strategy と execution の __init__.py はプレースホルダを追加。

Other notes / design decisions
- DuckDB をデフォルトのローカル DB として採用し、ファイルパスの親ディレクトリ自動作成をサポート。
- API クライアントは id_token の注入を許可し、テスト容易性・ページネーション間でのトークン共有を配慮。
- ログ出力（logger）を適切に配置し、処理状況・警告・エラーを記録する。
- 各種操作は冪等に設計（ON CONFLICT / UNIQUE 制約 / 冪等キー）し、再実行可能性を確保。

Known limitations / TODO
- strategy、execution、monitoring の実装は本リリースでは主要ロジックを含まずプレースホルダのみ（今後の実装予定）。
- 品質チェックの項目は一部（重複・日付不整合）について関数実装が期待される（設計に含まれるが今後追加）。
- 外部 API 呼び出しのユニットテスト用のモックや統合テストは追加予定。

----- End of CHANGELOG -----