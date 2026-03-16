Keep a Changelog に準拠した CHANGELOG.md（日本語）

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の慣習に従います。
各リリースには変更カテゴリ（Added, Changed, Fixed, Deprecated, Removed, Security）を付けています。

## [0.1.0] - 2026-03-16

Added
- パッケージ初期リリース: kabusys — 日本株自動売買システムの基盤実装を追加。
  - パッケージメタ:
    - src/kabusys/__init__.py に __version__ = "0.1.0"、公開モジュール一覧を定義（data, strategy, execution, monitoring）。
- 環境設定管理:
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動読み込み（優先順位: OS環境 > .env.local > .env）。プロジェクトルートは .git または pyproject.toml を基準に探索し、CWD に依存しない方式を採用。
    - .env パーサーを実装（export 形式、シングル/ダブルクォート、エスケープ、コメント処理などに対応）。
    - 自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス 等の設定をプロパティ経由で取得。必須環境変数未設定時は ValueError を送出。KABUSYS_ENV と LOG_LEVEL のバリデーションを実装。
- J-Quants API クライアント:
  - src/kabusys/data/jquants_client.py
    - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX 市場カレンダーを取得する fetch_* 関数群を実装（ページネーション対応）。
    - 認証: リフレッシュトークンから ID トークンを取得する get_id_token() を実装。モジュールレベルのトークンキャッシュを実装してページネーション間で共有。
    - HTTP リクエストユーティリティ:
      - 固定間隔スロットリングによるレート制御（_RateLimiter、デフォルト 120 req/min）。
      - リトライロジック（最大 3 回、指数バックオフ、408/429/>=500 を対象）。429 の場合は Retry-After ヘッダを尊重。
      - 401 受信時はトークンを自動リフレッシュして 1 回だけリトライ（無限再帰を回避）。
      - JSON デコード失敗時の明示的なエラーメッセージ。
    - DuckDB への保存関数 save_*:
      - raw_prices, raw_financials, market_calendar への保存を実装し、ON CONFLICT DO UPDATE により冪等性を確保。
      - fetched_at を UTC ISO8601（Z表記）で記録し、Look-ahead Bias のトレースを可能に。
      - PK 欠損行はスキップし、スキップ数をログ出力。
    - 型変換ユーティリティ _to_float / _to_int を実装（安全な変換・不正値は None）。
- DuckDB スキーマ定義・初期化:
  - src/kabusys/data/schema.py
    - DataPlatform の 3 層（Raw / Processed / Feature）＋Execution 層に基づくテーブル定義を実装。
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw 層テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層テーブル。
    - features, ai_scores 等の Feature 層テーブル。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層テーブル。
    - 効率的な検索のための索引（idx_...）群を追加。
    - init_schema(db_path) により DB ファイルの親ディレクトリを自動作成し、全テーブルとインデックスを冪等に作成可能（":memory:" をサポート）。
    - 既存 DB へ接続を返す get_connection() を提供（初回は init_schema を推奨）。
- ETL パイプライン:
  - src/kabusys/data/pipeline.py
    - 差分更新（差分算出、backfill による後出し修正吸収）、保存（jquants_client の save_* を利用）、品質チェック（quality モジュール呼び出し）を行う ETL 実装。
    - run_prices_etl / run_financials_etl / run_calendar_etl を個別に実行可能（差分ロジック、backfill、calendar の lookahead をサポート）。
    - run_daily_etl により一括実行（時計回りで calendar → prices → financials → quality checks の順に処理）。各ステップは独立してエラーハンドリングされ、1 ステップ失敗でも他は継続。
    - ETLResult dataclass を提供し、取得件数・保存件数・品質問題・エラー履歴を収集・返却。品質問題は辞書化可能（監査ログ等に利用）。
    - デフォルト挙動: 最小データ日付は 2017-01-01、calendar lookahead デフォルト 90 日、backfill デフォルト 3 日。
    - id_token を引数注入可能にしてテスト容易性を確保。
- 品質チェック:
  - src/kabusys/data/quality.py
    - QualityIssue dataclass を導入（check_name, table, severity, detail, rows）。
    - check_missing_data: raw_prices の OHLC 欠損検出（サンプルを最大 10 件返す）。欠損は重大度 "error" として報告。
    - check_spike: LAG を用いて前日比のスパイク（デフォルト閾値 50%）を検出。サンプルとカウントを返す。
    - 各チェックは Fail-Fast ではなく全件収集する設計。DuckDB の SQL とパラメータバインドで効率化。
- 監査ログ（トレーサビリティ）:
  - src/kabusys/data/audit.py
    - シグナル→発注→約定までのトレーサビリティ用テーブルを実装（signal_events, order_requests, executions）。
    - order_request_id を冪等キーとして扱い、再送時の二重発注を防止する設計。
    - created_at / updated_at を持ち、TIMESTAMP は UTC 保存（init_audit_schema で SET TimeZone='UTC' を実行）。
    - 各種整合性チェック（注文種別ごとの price チェック等）を DB 側 CHECK 制約で実装。
    - init_audit_schema(conn) と init_audit_db(db_path) を提供。インデックス群も作成。

Changed
- 設計上の注意点と方針をドキュメントコメントに明記（API レート制限、リトライ方針、冪等性、Look-ahead Bias 対策、品質チェックの振る舞いなど）。

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- 認証情報は環境変数経由で管理する設計（Settings で必須項目チェック）。自動ロードされる .env は OS 環境変数で保護され、override の扱いを厳密に制御。

Notes（補足）
- DuckDB への保存は SQL の ON CONFLICT DO UPDATE を使って冪等化しているため、再実行や部分的な再取得でデータの上書きが安全に行えます。
- run_daily_etl 等は各ステップで例外を捕捉して result.errors にメッセージを追加するため、呼び出し側で結果を検査して適切な対処（アラート送信や再実行など）を行ってください。
- ID トークン自動リフレッシュは 401 を検出した場合のみ 1 回実行されるため、想定外の認証失敗は速やかに失敗として扱われます。
- テストのために id_token を外部注入でき、DuckDB は ":memory:" 指定でインメモリ DB を利用できます。

今後の予定（例）
- strategy / execution / monitoring 層の実装拡張（現在はパッケージエントリのみ）。
- 品質チェックの拡張（重複チェック、日付不整合検出の追加等）。
- Slack 通知や運用監視の統合。

以上。ご要望があれば、各モジュールごとの変更点をさらに細分化した CHANGES（コミット単位/PR 単位）の記載や英語版の追加も作成します。