# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。セマンティックバージョニングを使用します。

## [Unreleased]
（今後の変更をここに記載）

## [0.1.0] - 2026-03-16
初回公開リリース。日本株自動売買システムのコアデータ基盤・ETL・監査・設定周りの実装を追加。

### Added
- パッケージ基本情報
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。バージョン 0.1.0 を設定。

- 環境設定管理
  - settings クラスによる環境変数ベースの設定管理を追加（src/kabusys/config.py）。
  - .env ファイルの自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env パース機能を強化：
    - export KEY=val 形式対応
    - シングル/ダブルクォートとバックスラッシュエスケープ対応
    - インラインコメント処理（クォートあり/なしの取り扱い差分）
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト等で使用）。
  - 環境値検証:
    - KABUSYS_ENV（development/paper_trading/live）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - 必須設定取得時に未設定なら ValueError を投げる _require 関数を提供。
  - デフォルト値（例：KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH）を設定。

- J-Quants API クライアント（データ取得/保存機能）
  - jquants_client モジュールを実装（src/kabusys/data/jquants_client.py）。
  - 取得可能データ:
    - 株価日足（OHLCV）
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー（祝日・半日・SQ）
  - 設計上の特徴:
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライ・バックオフ実装（最大 3 回、指数バックオフ、408/429/5xx をリトライ対象）。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰防止の allow_refresh フラグ）。
    - ページネーション対応（pagination_key によるループ）。
    - トークンキャッシュをモジュールレベルで共有（ページネーション間での再利用）。
    - 取得時の fetched_at を UTC タイムスタンプで付与し、Look-ahead Bias 防止を考慮。
  - DuckDB への冪等性ある保存関数を追加:
    - save_daily_quotes（raw_prices、ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials、ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar、ON CONFLICT DO UPDATE）
  - データ変換ユーティリティ:
    - _to_float, _to_int（安全な型変換、空値や不正値は None を返す）
  - ロギング出力で取得数・保存数・警告を記録。

- DuckDB スキーマ定義と初期化
  - data.schema モジュールを実装（src/kabusys/data/schema.py）。
  - 3層（Raw / Processed / Feature）＋ Execution レイヤーのテーブル定義を追加:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY / CHECK / FOREIGN KEY）を多数定義しデータ整合性を確保。
  - よく使われるクエリパターンに対するインデックスを追加（例: code/date 検索、status 検索など）。
  - init_schema(db_path) による初期化関数を提供（親ディレクトリ自動作成、:memory: サポート）。
  - get_connection(db_path) を提供（既存 DB への接続を返す）。

- ETL パイプライン
  - data.pipeline モジュールを実装（src/kabusys/data/pipeline.py）。
  - 機能:
    - 差分更新（DB の最終取得日を参照して未取得分のみを取得）。
    - バックフィル（デフォルト backfill_days=3）をサポートし API の後出し修正を吸収。
    - 市場カレンダー先読み（デフォルト lookahead_days=90）。
    - run_prices_etl / run_financials_etl / run_calendar_etl の個別ジョブを実装。
    - run_daily_etl による統合 ETL 実行:
      1. カレンダー ETL（先に取得）
      2. 株価日足 ETL（営業日調整あり）
      3. 財務データ ETL
      4. 品質チェック（オプション、fail-fast ではなく問題を収集）
    - ETLResult データクラスを追加（取得/保存件数・品質問題・エラー情報を格納）。
  - DB スキーマ未作成や空テーブルへのフォールバック処理を実装。
  - 例外ハンドリング: 各ステップは個別に try/except され、1つの失敗が全体を停止させない設計。

- 監査ログ（トレーサビリティ）
  - data.audit モジュールを実装（src/kabusys/data/audit.py）。
  - 監査用テーブル定義:
    - signal_events（戦略が生成したシグナルのログ）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社からの約定ログ）
  - トレーサビリティ階層設計（business_date → strategy_id → signal_id → order_request_id → broker_order_id）。
  - 各テーブルに created_at / updated_at を設け、UTC タイムゾーンでの保存を前提（init で SET TimeZone='UTC' を実行）。
  - 各種制約・チェック、ステータス列、インデックスを定義。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。

- データ品質チェック
  - data.quality モジュールを実装（src/kabusys/data/quality.py）。
  - チェック項目:
    - 欠損データ検出（raw_prices の OHLC 欄の NULL 検出）→ QualityIssue を返す（severity=error）
    - スパイク検出（前日比の絶対変動率が閾値を超えるレコードを検出）→ QualityIssue を返す
    - 重複チェック、日付不整合検出（将来日付・営業日外）を想定（モジュール内設計に基づく）
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - チェックは全件収集方式（Fail-Fast ではない）、DuckDB 上で SQL による効率的な実行。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- 認証トークンや .env の取り扱いに関する設計注意点を実装（保護された OS 環境変数は .env による上書きを回避）。

---

注:
- 本 CHANGELOG はソースコードから推測して作成しています。実際の変更履歴やリリースノートはプロジェクトの運用方針に従って調整してください。