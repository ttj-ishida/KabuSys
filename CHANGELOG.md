# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従います。  
このプロジェクトはセマンティックバージョニングに従います。

現在のリリース
- [0.1.0] - 2026-03-15

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買プラットフォーム「KabuSys」の基本コンポーネントを実装しました。

### Added
- パッケージ初期化
  - パッケージ名 kabusys、バージョン __version__ = "0.1.0" を追加。
  - パッケージ公開モジュールとして data, strategy, execution, monitoring を宣言。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により、CWD に依存しない自動 .env 読み込みを実現。
  - 読み込み順序: OS 環境変数 > .env.local > .env。（.env.local は既存の OS 環境変数を保護しつつ上書き可能）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - .env の行パーサ実装:
    - コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープに対応。
    - クォートなしの行でのインラインコメント判定（直前が空白/タブの場合のみ）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, DUCKDB_PATH 等）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - HTTP リクエストユーティリティを実装:
    - API ベース URL 定義。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - 冪等トークンキャッシュ（モジュールレベル）と自動トークンリフレッシュ (401 → 1 回のみリフレッシュして再試行)。
    - 再試行ロジック（指数バックオフ、最大 3 回）、対象ステータスコード指定（408, 429, 5xx）。429 の場合は Retry-After ヘッダを優先。
    - JSON デコード失敗時は詳細メッセージで例外発生。
  - DuckDB への保存関数を提供（save_daily_quotes, save_financial_statements, save_market_calendar）:
    - fetched_at を UTC タイムスタンプで記録し、Look-ahead バイアス防止を考慮。
    - INSERT ... ON CONFLICT DO UPDATE により冪等性を確保（重複時は更新）。
    - PK 欠損行のスキップとログ出力。
  - 型変換ユーティリティ _to_float / _to_int を実装。_to_int は "1.0" のような文字列を float 経由で安全に変換し、小数部非ゼロの場合は None を返すことで誤った丸めを防止。

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - DataLayer（Raw / Processed / Feature / Execution）に基づくテーブル定義を実装。
  - 主なテーブル:
    - Raw layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature layer: features, ai_scores
    - Execution layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約 (PRIMARY KEY, CHECK など) を付与してデータ整合性を強化。
  - 頻出クエリに対するインデックスを定義（例: 銘柄×日付、ステータス検索、外部キー・結合用）。
  - init_schema(db_path) により DB の親ディレクトリを自動作成し、DDL とインデックスを適用する冪等な初期化を提供。
  - get_connection() により既存 DB への接続を取得可能（スキーマ初期化は行わない）。

- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定までトレースする監査スキーマを実装（signal_events, order_requests, executions）。
  - order_request_id を冪等キーとして設計し、再送による二重発注を防止。
  - すべての TIMESTAMP を UTC で保存するため init_audit_schema() は "SET TimeZone='UTC'" を実行。
  - 監査用のインデックス群を追加し、日付/銘柄/戦略/ステータス などの検索を高速化。
  - init_audit_db(db_path) により監査専用 DB を初期化して接続を返す（親ディレクトリ自動生成）。

- プレースホルダパッケージ
  - execution, strategy, monitoring モジュールのパッケージ構成ファイルを追加（将来の実装準備）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 認証トークン取得周りで allow_refresh フラグを導入し、get_id_token 呼び出しからの無限再帰を防止。
- 環境変数の取り扱いにおいて OS 環境変数を保護する protected キーセットを導入。

### Notes / Implementation decisions
- J-Quants API のレート制限は 120 req/min を前提とし、単純な固定間隔スロットリング（最小間隔 0.5 秒）で実装。将来的に並列処理やトークンバケットが必要な場合は改修を検討。
- DuckDB の ON CONFLICT と各種制約で冪等性とデータ整合性を重視。運用中にスキーマ変更が必要になった場合はマイグレーション機構を導入する予定。
- .env のパースは多数のシェル風表記に対応しているが、すべての edge case を網羅するわけではないため、複雑な .env を使用する場合は注意。

---

今後の予定（例）
- execution / strategy / monitoring の実装拡充
- CI テストと型チェック（mypy）・リンティング（flake8 等）の追加
- J-Quants クライアントの統合テスト、Retry/RateLimit の細かいチューニング
- DuckDB スキーマに対するマイグレーション機能の追加

---