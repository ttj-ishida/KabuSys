# CHANGELOG

すべての重要な変更は Keep a Changelog の指針に従って記載しています。  
リリースはセマンティックバージョニングに従います。

フォーマット:
- Added: 新機能
- Changed: 変更
- Fixed: 修正
- Deprecated / Removed / Security: 該当があれば記載

## [Unreleased]
特になし。

## [0.1.0] - 2026-03-16
初期リリース

### Added
- パッケージ基本情報
  - パッケージ初期化: src/kabusys/__init__.py にて __version__ を "0.1.0" に設定し、主要サブパッケージをエクスポート。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイル自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して判定）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - .env の行パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ等に対応）。
  - protected 機能を用いた上書き制御（OS環境変数の保護）。
  - Settings クラスを提供し、必要な環境変数へのアクセスをプロパティで提供（J-Quants / kabu / Slack / DB パス等）。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）や is_live/is_paper/is_dev 等の補助プロパティを実装。
  - 必須変数未設定時は明確なエラーメッセージを送出する _require() を提供。

- データ取得クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - レート制限保護: 固定間隔スロットリング（120 req/min）を実装した _RateLimiter。
  - リトライロジック実装: 指数バックオフ、最大 3 回リトライ、対象ステータス (408, 429, 5xx)。
  - 401 Unauthorized 受信時の自動トークンリフレッシュを 1 回行ってリトライする仕組み（再帰防止フラグあり）。
  - ページネーション対応の取得関数を提供:
    - fetch_daily_quotes (株価日足、OHLCV)
    - fetch_financial_statements (四半期財務)
    - fetch_market_calendar (JPX カレンダー)
  - トークンのモジュールレベルキャッシュを実装（ページネーション間で共有）。
  - DuckDB へ冪等（idempotent）に保存する save_* 関数を実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - ON CONFLICT DO UPDATE を利用して重複上書きを防止
  - fetched_at（UTC）を記録してデータ取得時刻をトレース（Look-ahead Bias 対策）。
  - 型変換ユーティリティ _to_float, _to_int を実装して入力の堅牢性を確保。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataPlatform の 3 層構造に基づく包括的なスキーマ定義を実装（Raw / Processed / Feature / Execution）。
  - 生データテーブル: raw_prices, raw_financials, raw_news, raw_executions。
  - 処理済みデータ: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
  - 特徴量レイヤー: features, ai_scores。
  - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - インデックス定義を追加（頻出クエリの高速化目的）。
  - init_schema(db_path) による自動初期化機能を提供（親ディレクトリ自動作成、冪等）。
  - get_connection(db_path) による既存 DB への接続を提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL の高レベルワークフローを実装（run_daily_etl）。
  - セクション分割:
    - run_calendar_etl: 市場カレンダー差分取得（先読み lookahead）
    - run_prices_etl: 株価差分取得（バックフィル対応）
    - run_financials_etl: 財務差分取得（バックフィル対応）
  - 差分更新ロジック:
    - DB の最終取得日から自動で date_from を算出（未取得時は開始日を使用）。
    - デフォルトのバックフィル日数は 3 日（後出し修正を吸収）。
  - カレンダーはデフォルトで先読み 90 日（営業日調整に使用）。
  - ETL 実行結果を表す ETLResult dataclass を導入（取得数/保存数/品質問題/エラーを収集）。
  - 各ステップは独立して例外処理され、1 ステップ失敗でも他ステップは継続（Fail-Fast ではない）。
  - 品質チェックモジュール（quality）との統合点を提供（run_all_checks 呼出し）。

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - シグナルから約定までのトレーサビリティを確保する監査テーブルを実装:
    - signal_events, order_requests (冪等キー: order_request_id), executions
  - すべての TIMESTAMP を UTC で保存するため init_audit_schema() で SET TimeZone='UTC' を実行。
  - ステータス列、CHECK 制約、外部キー制約を適切に設定（削除制限や整合性保持）。
  - init_audit_db(db_path) による専用監査 DB の初期化補助を提供。
  - 監査用インデックスを定義（検索・ジョインの効率化）。

- データ品質チェック (src/kabusys/data/quality.py)
  - データ品質チェック用のモジュールを実装。
  - QualityIssue dataclass によりチェック結果の構造化（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（必須カラムの NULL を検出、重大度 error）
    - check_spike: 前日比スパイク検出（LAG ウィンドウを使用、デフォルト閾値 50%）
  - 各チェックはサンプル行（最大 10 件）を返し、Fail-Fast ではなく全件を収集する設計。
  - DuckDB 上での SQL 実行により効率的にチェックを実行。パラメータバインドを使用して SQL インジェクションを回避。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes / 設計上の注記
- J-Quants API のレート制限、リトライ、トークン更新、取得時刻記録、DuckDB への冪等書き込みなど、運用上重要な信頼性設計を中心に実装しています。
- ETL は品質チェックで重大な問題が検出されても自動的に停止しない（呼び出し元で判断する）設計です。
- audit テーブルは削除しない前提（FK は ON DELETE RESTRICT）で監査痕跡を保持します。
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後の利用環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を用いて制御可能です。

---

（初期リリースのため、今後のバージョンで機能追加・バグ修正・改善を行っていきます。ご要望や不具合報告は issue を作成してください。）