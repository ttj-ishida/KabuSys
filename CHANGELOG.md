# CHANGELOG

すべての注目すべき変更をここに記録します。本ファイルは "Keep a Changelog" の形式に準拠します。  
初回リリースは 0.1.0 として公開しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-16

### Added
- パッケージ基盤を追加
  - パッケージ名: kabusys（src/kabusys）
  - __version__ = "0.1.0"
  - パッケージ公開インターフェース: data, strategy, execution, monitoring（空の __init__ でモジュール構成を確立）

- 環境設定・読み込み機能（src/kabusys/config.py）
  - .env / .env.local / OS 環境変数から設定を自動ロード（プロジェクトルートは .git または pyproject.toml を探索）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - .env パーサ実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - コメント処理（クォート外での # の取り扱い）
  - 読み込み時の上書き制御（.env と .env.local の優先度管理）と「保護」された OS 環境変数の保持
  - Settings クラスでアプリ設定を型付きプロパティとして提供
    - 必須キー取得時は未設定で ValueError を発生
    - サポートされる主要設定: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）, KABUSYS_ENV（development/paper_trading/live のバリデーション）, LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - ヘルパープロパティ: is_live / is_paper / is_dev

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - ベース機能:
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* API を実装
    - ページネーション対応（pagination_key を利用して全件取得）
    - 取得日時（fetched_at）を UTC ISO8601 で付与し、Look-ahead Bias 対応
    - モジュールレベルで ID トークンをキャッシュし、ページネーション間で使い回し
  - レート制限制御:
    - 固定間隔スロットリング実装（_RateLimiter）
    - デフォルトレート: 120 req/min（1リクエストあたり最小間隔 0.5 秒）
  - リトライ・エラーハンドリング:
    - 指数バックオフによるリトライ（最大 3 回、バックオフ係数 base=2.0 秒）
    - リトライ対象: HTTP 408, 429, および 5xx 系
    - 429 の場合は Retry-After ヘッダを優先
    - 401 受信時は自動でリフレッシュトークンから id_token を再取得して 1 回だけリトライ（無限再帰対策あり）
    - ネットワークエラー（URLError / OSError）に対する再試行
  - save_* 関数（DuckDB への保存）:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装
    - ON CONFLICT DO UPDATE による冪等な保存ロジック
    - PK 欠損行はスキップしてログ出力
  - ユーティリティ:
    - _to_float / _to_int: 型変換の堅牢化（空値・異常値は None、"1.0" のような float 文字列の int 変換など）

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - 3 層（Raw / Processed / Feature）+ Execution レイヤーのテーブル DDL を定義
  - 主なテーブル（抜粋）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（よく使うクエリパターンに最適化）
  - init_schema(db_path) で DB ファイルのディレクトリ自動作成と全テーブル初期化（冪等）
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL のメイン: run_daily_etl
    - ステップ: カレンダー ETL → 株価日足 ETL → 財務 ETL → 品質チェック（オプション）
    - 各ステップは独立してエラーハンドリングし、1 ステップ失敗でも他ステップを継続
  - 差分更新ロジック:
    - DB の最終取得日を基に差分のみを取得（初回は _MIN_DATA_DATE = 2017-01-01 から取得）
    - デフォルトのバックフィル日数 backfill_days = 3（最終取得日の数日前から再取得して API の後出し修正を吸収）
    - 市場カレンダーはデフォルトで target_date + 90 日先まで先読み（calendar_lookahead_days = 90）
  - 個別 ETL ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl（取得数と保存数を返す）
  - ETLResult データクラスを導入して実行結果（取得数、保存数、品質問題、エラー一覧）を返却
  - 品質チェックとの連携（quality モジュールを呼び出す。spike_threshold デフォルト 0.5）

- データ品質チェック（src/kabusys/data/quality.py）
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（必須カラムの NULL をエラーとして報告）
    - check_spike: 前日比での急騰・急落（LAG ウィンドウを用いて変動率が閾値を超えるレコードを検出）。デフォルト閾値は 0.5（50%）
  - 設計方針:
    - 各チェックは全件収集モード（Fail-Fast ではなく全ての問題を返却）
    - DuckDB のパラメータバインド（?）を使用して安全に SQL を実行

- 監査（Audit）ログとスキーマ（src/kabusys/data/audit.py）
  - シグナル生成 → 発注要求 → 約定のトレーサビリティを取る監査テーブルを定義
  - 主なテーブル:
    - signal_events: 戦略が生成した全シグナルを記録（棄却・エラーも含む）
    - order_requests: 発注要求（order_request_id が冪等キー。価格チェック制約付与）
    - executions: 証券会社からの約定ログ（broker_execution_id をユニークな冪等キーとして記録）
  - インデックス群を定義（status や日付・銘柄検索、ID 連携用）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供
  - 設計上の特徴:
    - すべての TIMESTAMP を UTC で保存（init で SET TimeZone='UTC' を実行）
    - created_at / updated_at を持ち監査証跡を保持
    - FK は ON DELETE RESTRICT（監査ログを削除しない前提）
    - order_request_id による冪等性の保証、ステータス遷移の想定（pending→sent→filled/...）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Notes / Known limitations
- strategy/ execution / monitoring モジュールはパッケージ構成として存在するが、実装はほとんど（または空）であり今後の拡張を想定。
- quality モジュールのトップドキュメントでは重複チェック・日付不整合チェック等が言及されているが、現時点で実装されているチェックは主に欠損とスパイク検出。追加のチェックは今後実装予定。
- J-Quants クライアントは urllib を用いて同期 API 呼び出しを行う。大規模並列取得が必要な場合は将来的に非同期化やコネクションプールの検討が必要。
- DuckDB の制約やインデックスの挙動はバージョンに依存する可能性があるため、運用環境での検証を推奨。

---

（今後のバージョンでは、戦略実装、実取引接続、監視/アラート機構、CI テストの充実化などを追記していく予定です。）