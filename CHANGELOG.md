# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
重大な変更はセマンティックバージョニングに従います。

## [Unreleased]

（現在のリポジトリ状態はバージョン 0.1.0 としてリリース済みのため、Unreleased に未確定の変更はありません。）

## [0.1.0] - 2026-03-16

最初の公開リリース。日本株自動売買システム「KabuSys」のコア基盤を実装しました。主な追加点は以下のとおりです。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージの初期化（__version__ = "0.1.0"、主要サブパッケージを __all__ に列挙）。
  - サブパッケージ用の空 __init__（execution, strategy, data）。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート探索（.git または pyproject.toml を基準）により CWD に依存しない自動 .env ロード。
  - .env のパース機能:
    - コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスでアプリ設定をプロパティとして提供（必須キー取得時は例外を送出）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）の既定値、環境（KABUSYS_ENV）とログレベル検証、is_live/is_paper/is_dev ヘルパー。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API クライアントを実装: 日次株価（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得。
  - レート制御: 固定間隔スロットリング（120 req/min を目安）。
  - リトライロジック: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx をリトライ対象。
  - 401 Unauthorized 受信時はリフレッシュトークンで自動的に id_token を更新して 1 回リトライ。
  - ページネーション対応（pagination_key の追跡）。
  - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）。
  - fetch_* 系関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存用関数（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE による重複排除
  - 取得時刻（fetched_at）を UTC ISO8601 形式で記録（Look-ahead bias 対策）。
  - 型変換ユーティリティ: _to_float, _to_int（安全に None を返す挙動）。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataLayer/スキーマ（Raw, Processed, Feature, Execution）を網羅する DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤー。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed レイヤー。
  - features, ai_scores などの Feature レイヤー。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance などの Execution レイヤー。
  - 適切な CHECK 制約、PRIMARY KEY、FOREIGN KEY を付与（データ整合性を強化）。
  - インデックス（頻出クエリに合わせた CREATE INDEX IF NOT EXISTS）を用意。
  - init_schema(db_path) で DB ファイルの親ディレクトリを自動作成し、すべてのテーブルとインデックスを作成（冪等）。
  - get_connection(db_path) による接続取得（スキーマ初期化はしない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL の一連実行を行う run_daily_etl 実装（カレンダー → 株価 → 財務 → 品質チェック）。
  - 各ジョブで差分取得を行う補助関数:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - run_prices_etl, run_financials_etl, run_calendar_etl
  - 差分更新ロジック:
    - 最終取得日から backfill_days（デフォルト 3 日）を遡って再取得し、API の後出し修正を吸収。
    - デフォルトの初回取得開始日は 2017-01-01。
  - 市場カレンダーの先読み（デフォルト 90 日）をサポートし、営業日調整用に利用。
  - ETL 結果を ETLResult dataclass で集約（取得数・保存数・品質問題・エラーなどを保持）。
  - 品質チェックを呼び出し、重大度に応じた判定用の情報を返す（Fail-Fast にはしない）。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - シグナルから約定に至るトレース用の監査テーブルを追加:
    - signal_events, order_requests, executions
  - UUID ベースのトレーサビリティ階層設計（order_request_id を冪等キーとして扱う等）。
  - order_requests に対する各種制約（limit/stop/market のチェック制約、status フィールド等）。
  - executions に broker_execution_id をユニークキーとして約定レベルの冪等性を確保。
  - init_audit_schema(conn) / init_audit_db(db_path) で監査用テーブルとインデックスを初期化。
  - タイムゾーンは UTC に固定（SET TimeZone='UTC' を実行）。

- データ品質チェック (kabusys.data.quality)
  - 欠損データ検出（open/high/low/close の NULL を検出）check_missing_data を実装。
  - スパイク検出（前日比が閾値 50% を超える急騰/急落）check_spike を実装（LAG ウィンドウ使用）。
  - QualityIssue dataclass によりチェック名・テーブル・重大度・サンプル行を返却。
  - 各チェックはサンプル（最大 10 行）と件数を返す設計で、呼び出し元が対応を判断可能。

### 変更 (Changed)
- 初期リリースのため既存コードからの変更はありません。

### 修正 (Fixed)
- 初期リリースのためバグ修正履歴はありません。

### 注意・既知の制約 (Notes / Known limitations)
- ネットワーク呼び出しは urllib を使用し timeout を 30 秒に設定しています。実運用では HTTP クライアントやバックオフ戦略の追加調整が必要な場合があります。
- save_* 関数は DuckDB のテーブルスキーマ（特に PK）に依存します。init_schema を実行せずに保存するとエラーになる可能性があります。
- get_id_token は settings.jquants_refresh_token に依存するため、該当環境変数が未設定だと例外が発生します。
- audit テーブルは削除前提ではなく、FK は ON DELETE RESTRICT を採用しています（監査証跡を保存）。
- 現在の品質チェックは raw_prices を対象に限定しており、将来的に他テーブルへのチェック拡張が想定されます。

### マイグレーション/導入手順 (Upgrade / Migration)
- 初回セットアップ手順（簡易）:
  1. 必須環境変数を設定: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（.env または OS 環境）。
  2. init_schema(settings.duckdb_path) を実行して DuckDB スキーマを初期化。
  3. run_daily_etl(conn) を実行してデータの初回取得を行う。
  4. 監査ログを別 DB に分けたい場合は init_audit_db() を利用。

今後の予定（参考）
- API クライアントのテストカバレッジ拡張、HTTP クライアントの差し替え可能化（requests/HTTPX 等）、並列取得やより柔軟なレート制御、strategy / execution 層の実装拡張。

---

開発/運用に関する質問や、CHANGELOG の追加情報が必要であれば教えてください。