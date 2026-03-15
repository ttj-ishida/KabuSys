# Changelog

すべての注目すべき変更を記載します。フォーマットは Keep a Changelog に準拠しています。  
リリース日はパッケージの __version__（0.1.0）と合わせて記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-15
最初の公開リリース。日本株自動売買システムのコア基盤（設定管理、データ取得・保存、データベーススキーマ、監査ログ）を実装。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ に __version__ = "0.1.0"、および public モジュール一覧を定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルート検出: .git または pyproject.toml を基準にプロジェクトルートを探索（カレントワーキングディレクトリ非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応（テスト用途）。
    - OS 環境変数を保護する protected 機能（.env の上書き制御）。
  - .env パーサ実装:
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの取り扱い、無効行（空行／# コメント）スキップ。
  - Settings による設定プロパティ（J-Quants トークン、kabu API 設定、Slack トークン・チャンネル、DuckDB/SQLite パス、環境種別/ログレベル）を提供。
  - KABUSYS_ENV と LOG_LEVEL に対するバリデーション（有効値セットを定義）と利便性フラグ（is_live, is_paper, is_dev）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants API からのデータ取得機能を実装:
    - 株価日足（OHLCV）取得: fetch_daily_quotes（ページネーション対応）
    - 財務データ（四半期 BS/PL）取得: fetch_financial_statements（ページネーション対応）
    - JPX マーケットカレンダー取得: fetch_market_calendar
  - 認証 / トークン管理:
    - get_id_token: リフレッシュトークンから ID トークンを取得（POST）。
    - モジュールレベルの ID トークンキャッシュを導入し、ページネーション間で共有。
    - 401 受信時に自動リフレッシュして 1 回リトライするロジック（無限再帰防止の allow_refresh 制御）。
  - レート制御と耐障害性:
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。HTTP 408/429/5xx をリトライ対象に含む。429 の場合は Retry-After を優先。
    - ネットワークエラー（URLError/OSError）にもリトライ。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes: raw_prices テーブルへ保存（ON CONFLICT DO UPDATE によるアップサート）、fetched_at を UTC タイムスタンプで記録。
    - save_financial_statements: raw_financials テーブルへ保存（アップサート）。
    - save_market_calendar: market_calendar テーブルへ保存（アップサート）。HolidayDivision の解釈を実装（取引日/半日/SQ の判定）。
    - キー欠損行のスキップとログ出力。
  - JSON デコードエラーハンドリングと詳細なエラーメッセージ（デコード失敗時にレスポンス一部を含む）。
  - ユーティリティ変換関数:
    - _to_float: 空値や変換失敗は None。
    - _to_int: 文字列や float 表現を考慮。小数部が非ゼロの場合は None を返して意図しない切り捨てを防止。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）および Execution 層のテーブル定義を実装。
  - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions 等。
  - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等。
  - Feature レイヤー: features, ai_scores 等。
  - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等。
  - 頻出クエリ向けのインデックスを定義（コード・日付スキャン、ステータス検索、外部キー参照用など）。
  - init_schema(db_path): ディスク上の DuckDB ファイル（および :memory:）を初期化し、テーブルとインデックスを作成するユーティリティ（親ディレクトリの自動作成含む）。
  - get_connection(db_path): 既存 DB への接続取得ユーティリティ（スキーマ初期化は行わない旨を明記）。

- 監査ログ（トレーサビリティ）モジュール (kabusys.data.audit)
  - シグナル → 発注 → 約定までの完全トレーサビリティを実現する監査スキーマを実装。
  - トレーサビリティ階層（business_date / strategy_id / signal_id / order_request_id / broker_order_id）設計を反映。
  - テーブル:
    - signal_events: 戦略が生成したすべてのシグナル（棄却やエラー含む）を記録。decision と reason、created_at を保持。
    - order_requests: 発注要求ログ（order_request_id を冪等キーとして扱う）。order_type ごとのチェック制約（limit/stop/market）やステータス遷移管理用フィールドを提供。
    - executions: 証券会社からの約定ログを記録（broker_execution_id を冪等キーとしてユニーク制約）。
  - インデックス: 日付・銘柄検索、戦略別検索、status ベースの待ち行列検索、broker_order_id による紐付け等を想定した索引を定義。
  - init_audit_schema(conn): 既存の DuckDB 接続に監査テーブルを追加（すべての TIMESTAMP を UTC で保存するために TimeZone='UTC' を設定）。
  - init_audit_db(db_path): 監査ログ専用データベースの初期化ユーティリティ（親ディレクトリの自動作成含む）。

- パッケージ構成
  - data, strategy, execution, monitoring といったモジュールパスを確立。strategy/execution/monitoring には将来的機能追加のためのプレースホルダを用意。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- 機密情報（トークンなど）は環境変数経由で取得する設計。自動 .env ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

注:
- 実装はコード内のドキュメント（関数 docstring や設計コメント）に基づいて記載しています。
- schema / audit の DDL は冪等（CREATE IF NOT EXISTS）で定義されており、既存 DB への再適用やバージョンアップ時の互換性を考慮した作りになっています。