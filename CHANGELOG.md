# Changelog

すべての重要な変更点はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

なお、このCHANGELOGはリポジトリ内のコードから推測して作成した初期リリース記録です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-16

### Added
- パッケージ基盤
  - kabusys パッケージを追加。トップレベルのバージョンは `0.1.0`。
  - __all__ に ["data", "strategy", "execution", "monitoring"] を公開。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を自動読み込みするロジックを実装。
    - プロジェクトルート検出は __file__ から親ディレクトリを探索し、`.git` または `pyproject.toml` を基準に判定（配布後も動作）。
    - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 読み込み順序: OS 環境変数 > .env.local > .env。`.env.local` は上書き（override）を許可。
    - OS 側の既存環境変数は protected として上書きから保護。
  - .env パーサー (`_parse_env_line`) を実装:
    - `export KEY=val` 形式対応、単・二重引用符で囲まれた値のバックスラッシュエスケープ処理、コメント処理などに対応。
  - Settings クラスを実装し、アプリ設定をプロパティ経由で提供:
    - J-Quants、kabuステーション、Slack、データベースパス等を取得するプロパティを提供。
    - 必須値が未設定の場合は `_require` により ValueError を投げる。
    - `KABUSYS_ENV` のバリデーション（development / paper_trading / live）と `LOG_LEVEL` の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - デフォルトのデータベースパス: DuckDB `data/kabusys.duckdb`、SQLite `data/monitoring.db`（expands ~）。

- J-Quants クライアント (`kabusys.data.jquants_client`)
  - J-Quants API から株価日足（OHLCV）、財務データ（四半期BS/PL）、JPX マーケットカレンダーを取得するクライアント実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング `_RateLimiter` を実装。
  - リトライロジック（最大3回、指数バックオフ、対象: 408/429/5xx）を実装。429 の場合は `Retry-After` を優先。
  - 401 Unauthorized 受信時は ID トークンを自動リフレッシュして1回だけリトライする仕組みを実装。
  - モジュールレベルの ID トークンキャッシュを導入し、ページネーションでの再取得を軽減。
  - fetch 系関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）はページネーション対応。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等性を考慮した実装（ON CONFLICT DO UPDATE）。
  - データの型変換ユーティリティ `_to_float` / `_to_int` を追加（安全な変換、空値や不正値は None）。

- スキーマ定義と初期化 (`kabusys.data.schema`)
  - DataPlatform の3層（Raw / Processed / Feature / Execution）に基づく DuckDB テーブル定義を追加。
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型制約、CHECK 制約、PRIMARY KEY、外部キーを付与。
  - 頻出クエリを想定したインデックスを多数定義（例: code×date のインデックス、status 検索用など）。
  - `init_schema(db_path)` によりディレクトリ作成を含めてテーブルとインデックスを一括作成（冪等）。
  - `get_connection(db_path)` を提供（スキーマ初期化は行わない旨を明示）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - 日次 ETL フローを提供する pipeline 実装（DataPlatform.md を想定した設計）。
  - 差分更新ロジック（DB の最終取得日を確認して新規データのみ取得、未取得時は初期日付から取得）。
  - バックフィル（backfill_days デフォルト 3 日）で最終取得日の数日前から再取得し API の後出し修正を吸収。
  - カレンダーの先読み（lookahead_days デフォルト 90 日）をサポート。
  - 各ステップ（calendar → prices → financials → quality）を独立して実行し、個別に例外をキャッチして ETL 全体を止めない設計。
  - ETL 実行結果を表す `ETLResult` データクラスを追加（品質問題リスト、エラー一覧、取得/保存件数等を含む）。
  - 補助関数: テーブル存在チェック、最大日付取得、営業日調整（非営業日を直近営業日に調整）を実装。
  - run_*_etl 系関数（run_prices_etl / run_financials_etl / run_calendar_etl）を実装。
  - run_daily_etl により一括実行・品質チェックの呼び出しを行う。

- 監査ログ（トレーサビリティ） (`kabusys.data.audit`)
  - シグナル → 発注 → 約定 のフローを UUID 連鎖で完全トレース可能にする監査テーブルを実装。
    - signal_events, order_requests, executions テーブルを定義（各種制約、ステータス管理、冪等キーなど）。
  - 監査用インデックスを複数追加（signal/strategy 検索、status キュー等）。
  - `init_audit_schema(conn)` により既存の DuckDB 接続に監査ログを追加（UTC タイムゾーン固定）。
  - `init_audit_db(db_path)` により監査専用 DB を初期化するユーティリティを提供。

- データ品質チェックモジュール (`kabusys.data.quality`)
  - 欠損データ検出（OHLC 欄の NULL）、スパイク検知（前日比の絶対変化 > threshold）、重複チェック、日付不整合チェックなどの基本品質チェックを実装方針として導入。
  - QualityIssue データクラスを導入し、各チェックは複数の QualityIssue を返す設計（Fail-Fast ではない）。
  - 実装済みチェック例:
    - check_missing_data: raw_prices の open/high/low/close 欠損を検出（重大度: error）。
    - check_spike: LAG を使って前日比スパイクを検出（デフォルト閾値 0.5 = 50%）。
  - DuckDB 経由で効率的に SQL を実行する実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- J-Quants のアクセストークンは Settings を通して環境変数から取得し、モジュール内部でのみキャッシュ・更新することでトークン漏洩リスクを低減する設計。

### Notes / Design Decisions
- DuckDB を永続ストアとして採用し、スキーマは将来的な分析・バックテストに耐えうる構成（Raw → Processed → Feature → Execution）を採用。
- ETL は後出し修正（API の差し替えや修正）を吸収するためバックフィルをデフォルトで行う。
- すべての TIMESTAMP は監査用テーブルでは UTC で保存する方針。
- API 呼び出しはレート制限・リトライ・トークンリフレッシュなど堅牢性を重視した実装。
- .env パーサは一般的なシェル形式（export、引用符、コメント）を想定して堅牢に実装。

---

もし追加で以下の情報が必要であれば提供します:
- 各テーブルのカラム一覧の要約（用途別）
- ETL の実行例（コードスニペット）
- 必須環境変数の一覧（.env.example 相当）