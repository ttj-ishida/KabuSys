# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式とセマンティックバージョニングに従います。

フォーマット:
- 変更はカテゴリ別（Added, Changed, Fixed, …）に整理します。
- 日付はリリース日を示します。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース

### Added
- パッケージ初期化
  - kabusys パッケージの基本構成を追加（src/kabusys/__init__.py）。
  - public API として data, strategy, execution, monitoring をエクスポート。

- 環境・設定管理機能（src/kabusys/config.py）
  - .env および環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（配布後も動作）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途等）。
  - .env パーサーを実装（export プレフィックス対応、クォートおよびバックスラッシュエスケープ対応、コメント処理）。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得可能に。
    - J-Quants トークン、kabu API パスワード、Slack トークン/チャネル、DB パス、環境種別（development/paper_trading/live）、ログレベル等を取得。
    - env / log_level の入力バリデーションを実装（有効値チェック）。
    - is_live / is_paper / is_dev ヘルパーを追加。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得する機能を追加。
  - 設計上の特徴:
    - API レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回）。対象ステータスコードを考慮（408/429/5xx）。429 の場合は Retry-After ヘッダ優先。
    - 401 を受信した場合は自動でトークンをリフレッシュして 1 回リトライ（無限再帰防止のフラグ）。
    - ページネーション対応（pagination_key による繰り返し取得）。
    - id_token キャッシュをモジュールレベルで共有してページネーション間で再利用。
    - 取得日時（fetched_at）を UTC で記録して Look-ahead Bias を抑制。
    - JSON デコードエラーや HTTP エラーに対する明確な例外メッセージ。
  - DuckDB への保存関数を追加（冪等性を配慮した実装）。
    - save_daily_quotes / save_financial_statements / save_market_calendar: ON CONFLICT DO UPDATE による重複排除。
    - PK 欠損行はスキップして警告ログを出力。
    - 型安全な変換ユーティリティ (_to_float, _to_int) を実装。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DataLayer の三層（Raw / Processed / Feature）＋Execution レイヤー用のテーブル DDL を実装。
    - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
    - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature レイヤー: features, ai_scores
    - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム制約（CHECK / NOT NULL / PRIMARY KEY / FOREIGN KEY）を充実させ、データ整合性を担保。
  - パフォーマンス向上のためのインデックス定義を追加（銘柄×日付の典型的なスキャン、ステータス検索など）。
  - init_schema(db_path) により DB ファイルの親ディレクトリを自動作成し、全テーブル・インデックスを冪等的に作成して接続を返す。
  - get_connection(db_path) で既存 DB へ接続可能（スキーマ初期化は行わない）。

- 監査ログ（Audit）モジュール（src/kabusys/data/audit.py）
  - シグナルから約定に至るフローをトレースする監査用スキーマを追加。
    - signal_events（シグナル生成ログ）、order_requests（冪等キー付き発注要求ログ）、executions（約定ログ）。
  - 監査設計方針に則った制約（冪等キー、FK + ON DELETE RESTRICT、ステータス列など）を導入。
  - init_audit_schema(conn) により既存接続に監査テーブルを追加（TIMESTAMP を UTC で保存するため SET TimeZone='UTC' を実行）。
  - init_audit_db(db_path) で監査専用 DB の初期化と接続取得をサポート。

### Changed
- （初回リリースのため該当項目なし）

### Fixed
- （初回リリースのため該当項目なし）

### Deprecated
- （初回リリースのため該当項目なし）

### Removed
- （初回リリースのため該当項目なし）

### Security
- シークレット管理は Settings 経由で環境変数から取得する設計。トークンはメモリ内でのみキャッシュし、ログに直接出力しない想定。

---

注:
- 本 CHANGELOG は、ソースコードから推測可能な機能・設計意図に基づいて作成しています。実際の変更履歴やリリースノート作成時は、コミット履歴やリリース日付、担当者の確認に基づいて更新してください。