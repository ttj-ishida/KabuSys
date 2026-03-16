# CHANGELOG

すべての注目すべき変更を記録します。形式は「Keep a Changelog」に準拠します。

現在のリリースポリシー: 互換性のない変更は Breaking Changes に記載します。

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買向けのデータプラットフォーム、ETL、監査ログ基盤、および環境設定ユーティリティを含む最小限の実装を追加しました。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージを追加。公開モジュール: data, strategy, execution, monitoring（__all__ に定義）。
  - strategy/, execution/ の初期化モジュールをプレースホルダとして追加。

- 環境設定 (kabusys.config)
  - .env/.env.local または OS 環境変数から設定を自動読み込みする仕組みを追加。
    - 読み込み優先度: OS環境 > .env.local > .env
    - 環境変数自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - プロジェクトルート検出は `.git` または `pyproject.toml` を起点に行い、CWD に依存しない実装。
  - .env パーサーは `export KEY=val` 形式やクォートされた値、インラインコメント処理、エスケープ対応をサポート。
  - Settings クラスを追加。環境変数経由で各種設定を取得:
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション: KABU_API_PASSWORD、KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN、SLACK_CHANNEL_ID（必須）
    - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - システム環境: KABUSYS_ENV（development/paper_trading/live のいずれか。値検証あり）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API との通信クライアントを実装:
    - API ベース URL とエンドポイント実装（日足 prices, 財務 statements, 市場カレンダー trading_calendar）。
    - レート制限を尊重する固定間隔スロットリング（_RateLimiter、デフォルト 120 req/min）。
    - リトライロジック（最大 3 回、指数バックオフ）。HTTP 408/429 および 5xx をリトライ対象に設定。
    - 429 に対しては Retry-After ヘッダを優先。ネットワークエラー（URLError/ OSError）にもリトライ。
    - 401 Unauthorized 受信時は自動で一度だけトークンをリフレッシュして再試行（無限再帰防止）。
    - id_token のモジュール内キャッシュを実装し、ページネーション間で共有。
    - ページネーション対応で全ページを取得（pagination_key 管理）。
    - 取得時刻を UTC ISO8601（fetched_at）で記録し、Look-ahead bias のトレースを容易に。
  - データを DuckDB に保存する関数を実装（冪等性を担保する INSERT ... ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes: raw_prices テーブルへの保存（PK(date, code)）。PK 欠損行はスキップし警告出力。
    - save_financial_statements: raw_financials テーブルへの保存（PK(code, report_date, period_type)）。PK 欠損行はスキップ。
    - save_market_calendar: market_calendar テーブルへの保存（PK(date)）。HolidayDivision を解釈し is_trading_day / is_half_day / is_sq_day を設定。
  - 型変換ユーティリティ: _to_float, _to_int（"1.0" 等の文字列変換への配慮、小数部がある場合は int 変換を拒否して None を返すなど）。

- DuckDB スキーマ (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の 3 層（＋監査層）に基づく DDL を追加:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）を設定。
  - 頻出クエリ向けのインデックスを作成（例: code × date スキャン、ステータス検索用インデックス等）。
  - init_schema(db_path) を実装。db の親ディレクトリ自動作成、DDL の冪等実行、DuckDB 接続を返す。
  - get_connection(db_path) を実装（スキーマ初期化は行わず既存 DB に接続）。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL パイプラインを実装（run_daily_etl）:
    - 処理ステップ順序: 1) 市場カレンダー ETL（先読み） → 2) 株価日足 ETL（差分 + backfill） → 3) 財務データ ETL → 4) 品質チェック（オプション）
    - 差分更新ロジック: DB の最終取得日からの差分取得。date_from 未指定時は最終取得日 - backfill_days（デフォルト 3 日）を算出。
    - バックフィルデフォルト: 3 日（後出し修正を吸収）。
    - カレンダー先読みデフォルト: 90 日（市場カレンダーは target_date + 90 日まで取得）。
    - ETLResult データクラスを導入し、各ステップの取得/保存数、品質チェック結果、エラー一覧を集約。
    - 各ステップは独立して例外を捕捉し、1 ステップの失敗がパイプライン全体を止めない設計（Fail-Fast ではなく全件収集）。
    - run_prices_etl / run_financials_etl / run_calendar_etl を個別に呼べるように実装。
    - 市場カレンダー取得後に非営業日調整を行うユーティリティ (_adjust_to_trading_day)。

- 品質チェック (kabusys.data.quality)
  - データ品質チェック基盤を追加:
    - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
    - 実装済みチェック:
      - check_missing_data: raw_prices の必須カラム (open/high/low/close) 欠損検出（サンプル行を最大 10 件返す）。欠損はエラー扱い。
      - check_spike: LAG を使った前日比スパイク検出（デフォルト閾値 50%）。サンプル行と件数を報告。
    - 各チェックは問題のリストを返し、呼び出し元で重大度に応じた対応を判断できる設計。

- 監査ログ (kabusys.data.audit)
  - シグナルから約定に至る監査トレース用テーブルを追加:
    - signal_events: 戦略が生成したシグナル（決定、棄却理由など）を永続化。
    - order_requests: 発注要求（order_request_id を冪等キーとして利用）。order_type ごとの制約（limit/stop/market の価格必須・不要ルール）を導入。
    - executions: 証券会社から返された約定情報（broker_execution_id をユニークな冪等識別子として扱う）。
  - 監査用インデックス群を追加（signal_events の日付/銘柄検索、order_requests のステータス検索、broker_order_id / broker_execution_id 関連など）。
  - init_audit_schema(conn) を実装。接続に対して監査テーブルを追加（SET TimeZone='UTC' を実行して UTC 保存を保証）。
  - init_audit_db(db_path) を実装。監査専用 DB を初期化して接続を返す。

### 変更 (Changed)
- 初回リリースのためなし

### 修正 (Fixed)
- 初回リリースのためなし

### 既知の注意点 / 制約
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされる（パッケージ配布後の安全設計）。
- J-Quants クライアントは HTTP レスポンスの JSON デコード失敗やネットワークエラーに対して詳細な例外を投げます。呼び出し側で適切に捕捉してください。
- quality モジュールのドキュメントでは複数チェック（欠損・スパイク・重複・日付不整合）を想定していますが、実装済みのチェックは現状 check_missing_data / check_spike です。その他のチェックは順次実装予定です。

### 互換性のない変更 (Breaking Changes)
- 初回リリースのためなし

---

注: 本 CHANGELOG はコードベースの内容から推測して記載しています。実際の変更履歴や設計意図はリポジトリのコミット履歴やドキュメント（DataPlatform.md, DataSchema.md 等）を参照してください。必要であれば、より細かいリリースノート（コミット別、ファイル別）も作成できます。