# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

（現時点の変更はなし）

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買プラットフォームの基礎機能をまとめて実装しています。

### 追加 (Added)

- パッケージ基礎
  - kabusys パッケージの初期化（バージョン 0.1.0、公開モジュール: data／strategy／execution／monitoring）。
  - __version__ を "0.1.0" に設定。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD に依存しない）。
  - .env の行パーサ実装:
    - コメント・空行を無視、`export KEY=val` 形式対応。
    - シングル/ダブルクォート中のバックスラッシュエスケープ処理、インラインコメントの無視等を実装。
    - 非クォート値では '#' の直前が空白／タブのみコメントとして扱う等のルールを実装。
  - .env 読み込み時の保護機能:
    - OS の既存環境変数は protected として上書き不可。
    - override 引数で上書きの挙動を制御。
  - Settings クラスで必須設定の抽象化を提供（プロパティ経由で取得）。
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を発生）。
    - その他設定:
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development|paper_trading|live の検証）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - 環境判定ユーティリティ: is_live / is_paper / is_dev。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
    - 基本 URL: https://api.jquants.com/v1
    - RateLimiter によるレート制限遵守（デフォルト 120 req/min、固定間隔スロットリング）。
    - リトライロジック: 指数バックオフ、最大 3 回（対象: 408/429/5xx、ネットワークエラー含む）。
    - 401 受信時はリフレッシュトークンで id_token を自動リフレッシュして 1 回リトライ（無限再帰対策あり）。
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）。
    - ページネーション対応でデータを継続取得。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録して Look-ahead Bias の防止を支援。
  - 公開関数:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(...): 日足（OHLCV）取得（ページネーション対応）
    - fetch_financial_statements(...): 四半期財務（BS/PL）取得（ページネーション対応）
    - fetch_market_calendar(...): JPX マーケットカレンダー取得
    - save_daily_quotes(conn, records): DuckDB の raw_prices に冪等に保存（ON CONFLICT DO UPDATE）
    - save_financial_statements(conn, records): raw_financials に冪等保存
    - save_market_calendar(conn, records): market_calendar に冪等保存
  - ユーティリティ: 型安全な変換関数 _to_float, _to_int を実装。

- DuckDB スキーマと初期化 (src/kabusys/data/schema.py)
  - DataPlatform 設計に基づく 3 層＋実行層スキーマを定義・初期化する DDL を実装。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PK / CHECK / FOREIGN KEY）を付与。
  - 頻出クエリに対するインデックスを定義。
  - init_schema(db_path) で DB ファイルの親ディレクトリ自動作成 → テーブルとインデックスを作成（冪等）。
  - get_connection(db_path) により既存 DB への接続を取得（初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL のエントリポイント run_daily_etl を実装。
    - 処理フロー: 市場カレンダー ETL → 株価日足 ETL（差分＋バックフィル）→ 財務 ETL（差分＋バックフィル）→ 品質チェック（オプション）
    - 差分更新ロジック: DB の最終取得日をもとに自動で date_from を計算。backfill_days による再取得によって API の後出し修正を吸収（デフォルト backfill_days=3）。
    - calendar の先読み（lookahead）をサポート（デフォルト 90 日）。
    - 各ステップは独立したエラーハンドリングを行い、1 ステップ失敗でも他は継続（Fail-Fast ではない）。
  - ETLResult データクラスを導入（取得件数、保存件数、品質問題、エラーメッセージ等を収集）。
  - 補助関数:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - run_prices_etl / run_financials_etl / run_calendar_etl
    - _adjust_to_trading_day: 非営業日の調整（market_calendar を使用、最大 30 日遡る）

- 監査ログ（トレーサビリティ）モジュール (src/kabusys/data/audit.py)
  - シグナルから約定までを追跡する監査用テーブル群を実装。
    - signal_events（戦略が生成した全シグナル）
    - order_requests（発注要求、order_request_id を冪等キーとして利用）
    - executions（証券会社からの約定ログ、broker_execution_id をユニーク冪等キーとして保存）
  - すべての TIMESTAMP を UTC に固定（init_audit_schema は SET TimeZone='UTC' を実行）。
  - 各テーブルの制約・チェックとインデックス（status や日付検索用など）を定義。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。

- データ品質チェックモジュール (src/kabusys/data/quality.py)
  - DataPlatform.md に基づく品質チェック群を実装。
    - check_missing_data(conn, target_date): raw_prices の OHLC 欠損検出（欠損は重大度 error）
    - check_spike(conn, target_date, threshold): 前日比スパイク（閾値デフォルト 0.5 = 50%）の検出
    - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）
  - 各チェックは問題のサンプルを返す（最大 10 行）し、Fail-Fast ではなく全件収集を行う。
  - DuckDB を用いた効率的な SQL 実装とパラメータバインドを採用。

### 変更 (Changed)

- （初回リリースのため該当なし）

### 修正 (Fixed)

- （初回リリースのため該当なし）

### 非推奨 (Deprecated)

- （初回リリースのため該当なし）

### 削除 (Removed)

- （初回リリースのため該当なし）

### セキュリティ (Security)

- （初回リリースのため該当なし）

---

注記:
- デフォルト値や閾値:
  - J-Quants API レート上限想定: 120 req/min（最小間隔 60/120 = 0.5 秒）
  - リトライ回数: 3 回、指数バックオフ係数ベース 2.0 秒
  - ETL のデフォルト backfill_days: 3
  - カレンダー先読み: 90 日
  - スパイク検出閾値デフォルト: 0.5 (50%)
- DuckDB 初期化関数は db_path の親ディレクトリを自動作成します。":memory:" を渡すことでインメモリ DB を使用可能です。
- このリリースでは strategy、execution、monitoring パッケージのエントリポイントは用意されていますが、各モジュールの具体的な戦略ロジックや注文実行ロジックはまだ実装フェーズです。次バージョンでの追加予定機能として、発注ブリッジ（kabuステーション連携）、戦略の実装、監視/通知機能の強化などを想定しています。