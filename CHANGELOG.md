# Changelog

すべての注目すべき変更はこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、この CHANGELOG はコードベースから推測して作成したものであり、実際のコミット履歴や意図と異なる場合があります。

## [Unreleased]

## [0.1.0] - 2026-03-15
最初の公開リリース。主要なモジュールの骨組み、J‑Quants 連携、DuckDB スキーマ、環境設定管理、監査ログなどの実装を含みます。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にバージョン情報と公開モジュール一覧を追加（__version__ = 0.1.0）。

- 環境変数・設定管理モジュール（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定値を読み込む自動ロード機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は上書き許可）。
    - OS 環境変数を保護する protected ロジックを実装。
  - .env 行パーサー実装（export プレフィックス対応、クォート内エスケープ、インラインコメントの扱いなど）。
  - Settings クラスを追加し、アプリ用設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV 検証（development / paper_trading / live のみ許可）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API から以下を取得する機能を実装:
    - 日足（OHLCV）fetch_daily_quotes（ページネーション対応）
    - 財務データ（四半期 BS/PL）fetch_financial_statements（ページネーション対応）
    - JPX マーケットカレンダー fetch_market_calendar
  - 認証処理: get_id_token（リフレッシュトークンから ID トークン取得）
  - HTTP リクエスト基盤:
    - レート制限を守る固定間隔スロットリング実装（120 req/min => 最小間隔 0.5 秒）
    - 冪等のトークンキャッシュ（モジュールレベルの ID トークンキャッシュ）
    - リトライロジック（最大 3 回、指数バックオフ、対象ステータス: 408/429/5xx／ネットワークエラー）
    - 401 発生時は自動トークンリフレッシュを 1 回行って再試行（無限再帰防止）
    - 429 の場合は Retry-After ヘッダの尊重
    - JSON デコード失敗時の明示的エラー
  - データ取得時に fetched_at を UTC で付与する設計方針（Look‑ahead bias 対策）を採用。
  - DuckDB 保存関数（冪等）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE による保存
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE による保存
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE による保存
  - 数値変換ユーティリティ:
    - _to_float: 安全な float 変換（失敗時は None）
    - _to_int: "1.0" 形式対応、非整数の小数文字列は None を返す等の安全仕様

- DuckDB スキーマ定義・初期化モジュール（src/kabusys/data/schema.py）
  - DataPlatform/ DataSchema に基づく多層スキーマを定義（Raw / Processed / Feature / Execution 層）。
  - 主要テーブル（抜粋）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに妥当性チェック（CHECK）、主キー、外部キー制約等を定義。
  - 頻出クエリ向けのインデックスを定義（銘柄×日付、ステータス検索、JOIN 用など）。
  - init_schema(db_path) を実装: 指定パスの DuckDB を初期化して全テーブル・インデックスを作成（冪等）。
  - get_connection(db_path) を実装（既存 DB への接続、初期化は行わない）。

- 監査ログ（トレーサビリティ）モジュール（src/kabusys/data/audit.py）
  - シグナルから約定までの完全トレースを目的とした監査テーブルを実装（UUID 連鎖モデル）。
  - テーブル:
    - signal_events: 戦略が生成したシグナルを全件保存（rejected 等の理由も含む）
    - order_requests: 冪等キー（order_request_id）を持つ発注要求ログ（limit/stop のチェック制約含む）
    - executions: 証券会社からの約定ログ（broker_execution_id を一意キーとして冪等性確保）
  - インデックス: シグナル日付・銘柄検索、戦略別検索、status スキャン、broker_order_id 検索など。
  - UTC タイムゾーン固定（init_audit_schema は conn.execute("SET TimeZone='UTC'") を実行）。
  - init_audit_schema(conn) / init_audit_db(db_path) 実装（監査専用 DB の初期化も可能）。

- パッケージ構成（プレースホルダ）
  - src/kabusys/execution/__init__.py（存在）
  - src/kabusys/strategy/__init__.py（存在）
  - src/kabusys/data/__init__.py（存在）
  - src/kabusys/monitoring/__init__.py（存在）
  - これらは将来的な実装向けにモジュール境界を用意（現時点では初期化ファイルのみ）。

### Changed
- 新規リリースのため該当なし。

### Fixed
- 新規リリースのため該当なし。

### Security
- 新規リリースのため該当なし。

### Notes / Design decisions（主な設計方針）
- API 周りはレート制限とリトライ、トークン自動リフレッシュで堅牢化。Look‑ahead bias 防止のため取得時刻を UTC の fetched_at に保存。
- DuckDB の INSERT は ON CONFLICT DO UPDATE を多用して冪等性を確保。
- 監査ログは削除しない前提で設計（FOREIGN KEY は ON DELETE RESTRICT を使用）。
- .env の自動読み込みはプロジェクトルート探索によりパッケージ配布後も動作するよう配慮。

---

今後のリリースでは、strategy / execution / monitoring 層の具体的実装、テスト・例外・ログの強化、CI/CD 設定、ドキュメント追加（DataSchema.md や DataPlatform.md の参照ドキュメント化）などが想定されます。