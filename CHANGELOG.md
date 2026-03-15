# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記録します。  
このファイルは、提示されたコードベースの内容から推測して作成した初回リリース向けの変更履歴です。

※日付はリリース時点の想定日です。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-15

### Added
- 初期リリース: KabuSys 日本株自動売買システムのコアモジュールを追加。
  - パッケージ初期化
    - src/kabusys/__init__.py にパッケージ名・バージョン（0.1.0）および公開サブモジュール一覧を定義（data, strategy, execution, monitoring）。
  - 環境設定管理
    - src/kabusys/config.py を追加。
      - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点に探索）。
      - .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - 複雑な .env 行パースに対応（export プレフィックス、シングル/ダブルクォート、エスケープ、コメントの扱い等）。
      - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）やログレベルの検証機能を実装。未設定必須変数は _require により明示的にエラーを返す。
  - J-Quants API クライアント
    - src/kabusys/data/jquants_client.py を追加。
      - J-Quants API からのデータ取得（株価日足、財務データ、JPX マーケットカレンダー）をサポート。
      - レート制限（120 req/min）を順守する固定間隔スロットリング（_RateLimiter）を実装。
      - リトライロジック（指数バックオフ、最大 3 回）、HTTP 429 の Retry-After ヘッダ尊重、ネットワークエラーのリトライ処理を実装。
      - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライする仕組みを実装（無限再帰回避のため allow_refresh フラグを使用）。
      - ページネーション対応（pagination_key の追跡）で全ページを取得。
      - 取得日時（fetched_at）を UTC で記録し、Look-ahead Bias 防止のため「いつシステムがデータを知り得たか」をトレース可能に。
      - DuckDB への保存用関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等なアップサートを実行し、PK 欠損行はスキップして警告を出力。
      - 型変換ユーティリティ（_to_float, _to_int）を実装し、空値・不正値の安全な扱いと float 文字列の扱い（"1.0" → 1）を定義。
  - DuckDB スキーマ管理
    - src/kabusys/data/schema.py を追加。
      - Raw / Processed / Feature / Execution の 3 層（+監査層）に対応したテーブル定義を実装（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等多数）。
      - 各種制約（PRIMARY KEY, CHECK）やインデックスを定義し、パフォーマンスと整合性を重視した設計。
      - init_schema(db_path) でデータベースファイルの親ディレクトリ自動作成 -> DuckDB 接続生成 -> 全 DDL とインデックス実行を行い冪等に初期化する API を提供。get_connection() で既存 DB への接続を返す。
  - 監査ログ（トレーサビリティ）
    - src/kabusys/data/audit.py を追加。
      - signal_events, order_requests, executions など監査用テーブルを定義。
      - order_request_id を冪等キーとする設計、全 TIMESTAMP を UTC で保存する方針（init_audit_schema は SET TimeZone='UTC' を実行）。
      - init_audit_schema(conn) および init_audit_db(db_path) による監査スキーマ初期化 API を提供。
      - 発注・約定フローを UUID 連鎖で完全にトレースできる構造を採用（戦略→シグナル→発注要求→証券会社受付→約定）。
  - パッケージ構造
    - strategy, execution, monitoring のパッケージ初期化ファイル（空の __init__.py）を追加し、将来的な拡張を準備。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の取り扱いで OS 環境変数保護（.env の上書き制御）を実装。自動ロードは明示的に無効化可能。

### Notes / 設計上の重要点（運用・移行注意）
- .env 自動読み込みはプロジェクトルートの検出に依存するため、配布後やパッケージ化環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って明示的に制御することを推奨。
- J-Quants API に対するレート制限（120 req/min）を厳守するため、長時間で大量のデータを取得する場合は処理時間の確保と実行間隔の調整が必要。
- DuckDB スキーマは多くの制約・外部キーを含むため、既存 DB へのマイグレーション時はバックアップを推奨。
- audit テーブルは削除しない運用を想定（ON DELETE RESTRICT）。監査履歴は基本的に残すことを前提とする。
- get_id_token() は settings.jquants_refresh_token を使用する。CI / 本番環境では必須環境変数（JQUANTS_REFRESH_TOKEN 等）を適切に設定すること。

---

以上が提示されたコードベースから推測して作成した CHANGELOG.md です。必要であれば、個々の変更項目をより詳細に分割したり、日付を実際のコミット日付に合わせて更新したりできます。どのように出力するか（ファイル追加、別フォーマット等）も指示してください。