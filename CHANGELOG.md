# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-16
初回リリース

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（バージョン 0.1.0）。
  - パッケージメタ情報: __version__ = "0.1.0"、__all__ に data/strategy/execution/monitoring を設定。

- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート判定: .git または pyproject.toml を起点に探索し、自動ロードを行う（配布後の動作を考慮）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーの実装:
    - 空行・コメント行（#）や `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理。
    - インラインコメント処理（クォート無しは '#' の直前が空白/タブであればコメント扱い）。
  - Settings クラスを提供（settings インスタンス経由で利用）。
    - 必須項目は _require によって未設定時に ValueError を送出。
    - J-Quants / kabu / Slack / DB パス等のプロパティを提供（デフォルト値や Path 変換を含む）。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証を実装。
    - is_live / is_paper / is_dev の補助プロパティを追加。

- データアクセス / ETL（kabusys.data）
  - J-Quants API クライアント（data.jquants_client）を実装。
    - 取得対象: 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー。
    - レート制御: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
    - 再試行ロジック: 指数バックオフ（最大 3 回）、対象ステータス: 408/429/5xx、429 の場合は Retry-After を優先。
    - 401 Unauthorized 受信時はリフレッシュを自動実行して 1 回リトライ（無限再帰を回避）。
    - ページネーション対応（pagination_key を利用して全ページ取得）。
    - 取得時刻のトレーサビリティ: fetched_at を UTC で記録（Look-ahead Bias 防止）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
      - 冪等性確保: INSERT ... ON CONFLICT DO UPDATE を使用して重複を排除・更新。
      - 必要な主キー欠損レコードはスキップしてログ出力。
    - 値変換ユーティリティ: _to_float, _to_int（安全に None を返す挙動、"1.0" などの扱いを明示）。
    - モジュール内で ID トークンのページネーション間キャッシュを提供。

  - DuckDB スキーマ管理（data.schema）
    - DataPlatform 設計に基づくスキーマを定義（Raw / Processed / Feature / Execution 層）。
    - 代表的テーブル:
      - raw_*（raw_prices, raw_financials, raw_news, raw_executions）
      - processed（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）
      - feature（features, ai_scores）
      - execution（signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）
    - 制約・型・CHECK を多用してデータ整合性を担保。
    - パフォーマンス向けインデックス定義（頻出クエリに合わせた INDEX）。
    - init_schema(db_path) による初期化 API と get_connection(db_path) を提供。
      - db_path の親ディレクトリを自動作成。
      - ":memory:" によるインメモリ DB サポート。

  - ETL パイプライン（data.pipeline）
    - run_daily_etl を中心とした日次 ETL フローを実装（市場カレンダー → 株価 → 財務 → 品質チェック）。
    - 差分更新ロジック:
      - DB の最終取得日から差分のみを取得。
      - デフォルトバックフィル日数: 3 日（後出し修正を吸収）。
      - 株価データの最小開始日を定義（_MIN_DATA_DATE = 2017-01-01）。
    - カレンダー先読み: デフォルト 90 日先まで取得（取引日判定に利用）。
    - 個別ジョブ API: run_prices_etl, run_financials_etl, run_calendar_etl（取得数・保存数を返す）。
    - ETLResult dataclass:
      - 実行結果の詳細を保持（取得件数、保存件数、品質問題、発生エラーなど）。
      - has_errors / has_quality_errors プロパティを提供。
      - to_dict によるシリアライズ補助。

  - 品質チェック（data.quality）
    - QualityIssue dataclass を定義（check_name, table, severity, detail, rows）。
    - 実装済みチェック:
      - check_missing_data: raw_prices の OHLC 欠損検出（volume は除外）。
      - check_spike: 前日比スパイク検出（デフォルト閾値 50%）。
    - 各チェックは DuckDB 上の SQL で効率的に実行し、サンプル行を返す。
    - Fail-Fast ではなく全件収集の方針（呼び出し元で重大度に応じた扱いを行う）。

  - 監査ログ（data.audit）
    - 戦略→シグナル→発注要求→約定を UUID 連鎖でトレースする監査テーブル群を実装。
    - テーブル:
      - signal_events（戦略が生成したシグナルの監査ログ）
      - order_requests（冪等キー order_request_id を持つ発注要求ログ）
      - executions（ブローカーから返る約定ログ、broker_execution_id をユニークに管理）
    - ステータス制御と入力チェック（order_type に応じた price 必須チェック等）を実装。
    - init_audit_schema(conn) / init_audit_db(db_path) API を提供。
    - すべての TIMESTAMP を UTC で保存するために初期化時に SET TimeZone='UTC' を実行。

- パッケージ構成
  - data / strategy / execution / monitoring の基本パッケージを準備（strategy/execution は __init__ のみで将来拡張想定）。

### 変更 (Changed)
- 該当なし（初回リリースのため）。

### 修正 (Fixed)
- 該当なし（初回リリースのため）。

### 既知の注意点 (Notes)
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN（J-Quants リフレッシュトークン）
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DUCKDB_PATH / SQLITE_PATH はデフォルト値あり（data/kabusys.duckdb / data/monitoring.db）
- 自動 .env 読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテストなどで便利です）。
- DuckDB スキーマの初期化は init_schema() を使用してください。監査ログのみ追加する場合は init_audit_schema() を既存接続に対して呼び出してください。
- J-Quants API クライアントは 120 req/min のレート制限を守る設計ですが、運用環境ではさらに上位の呼び出し間隔管理やバッチ化を検討してください。

以上。今後のリリースでは戦略ロジック、注文実行のブローカー連携、監視・通知機能の強化などを追加予定です。