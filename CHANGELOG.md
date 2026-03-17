# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般ルール:
- 重大度の高い変更（互換性を壊す可能性のある変更）は Breaking Changes として明示します。
- 日付はリリース日を示します。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコアモジュール群を実装しました。
主にデータ収集・保存、設定管理、ETLパイプライン、スキーマ定義、ニュース収集の機能を提供します。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名・バージョンを定義（__version__ = "0.1.0"）。
  - パブリックモジュールとして data, strategy, execution, monitoring を __all__ に登録。

- 環境変数 / 設定管理モジュール
  - src/kabusys/config.py を追加。
  - .env / .env.local ファイルと OS 環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
  - 自動ロード無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装: export 形式対応、クォート処理、インラインコメント処理。
  - 必須設定の取得・検証ヘルパ（_require）。
  - 設定プロパティ群:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
    - ヘルパ: is_live, is_paper, is_dev

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py を追加。
  - 提供 API:
    - get_id_token(refresh_token=None)
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
    - save_daily_quotes(conn, records)
    - save_financial_statements(conn, records)
    - save_market_calendar(conn, records)
  - 設計上の特徴:
    - API レート制御（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 429 の場合は Retry-After ヘッダを優先。
    - 401 の受信時はトークンを自動リフレッシュして1回リトライ（再帰防止）。
    - モジュールレベルで ID トークンをキャッシュしてページネーション間で共有。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し look-ahead bias のトレースを可能に。
    - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複排除。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py を追加。
  - RSS フィードから記事を取得し raw_news に保存、銘柄紐付けを行う一連処理を実装。
  - 主な機能:
    - デフォルトソース: Yahoo Finance のビジネスカテゴリ RSS を登録。
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）。
    - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先の検査、プライベートアドレス判定（IP と DNS 解決を用いる）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - fetch_rss, save_raw_news, save_news_symbols, _save_news_symbols_bulk, extract_stock_codes, run_news_collection を提供。
    - DB 保存はチャンク化＆トランザクションで実行し、INSERT ... RETURNING を使って実際に挿入された件数を取得。

- DuckDB スキーマ定義と初期化
  - src/kabusys/data/schema.py を追加。
  - Raw / Processed / Feature / Execution の各レイヤーに対応するテーブル群を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など）。
  - 各テーブルに適切な CHECK 制約・PRIMARY KEY・FOREIGN KEY を設定。
  - 頻出クエリ用のインデックス定義を追加。
  - init_schema(db_path) でフォルダ自動作成・DDL 実行（冪等）。get_connection で既存 DB に接続可能。

- ETL パイプライン
  - src/kabusys/data/pipeline.py を追加（差分更新と ETL ロジックの土台）。
  - 特徴:
    - 差分更新ロジック（DB 最終取得日から backfill_days さかのぼって再取得）。
    - 市場カレンダー先読み（_CALENDAR_LOOKAHEAD_DAYS）。
    - ETLResult dataclass により ETL の結果・品質問題・エラーを構造化して返却。
    - 品質チェックモジュール（quality）との連携用フックを想定。
    - テスト容易性を考慮し id_token 注入可能、内部ユーティリティ関数を分離。

- テスト/モック支援
  - news_collector._urlopen はテストで差し替え可能（モックしやすい設計）。
  - jquants_client の _request 等も id_token の注入やキャッシュクリアでテスト可能。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集で以下の対策を実装:
  - defusedxml による XML パース（XXE 等の緩和）。
  - SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクト事前検査）。
  - レスポンスサイズ上限と gzip 解凍後サイズ検査（リソース消費攻撃防止）。
- J-Quants クライアント:
  - 認証トークンの自動リフレッシュとキャッシュにより認証漏れ・無限再帰を回避する設計を採用。

### Notes / Usage
- 初期化:
  - DuckDB スキーマの作成: from kabusys.data import schema; schema.init_schema(settings.duckdb_path)
- 必須環境変数（未設定時は ValueError を発生）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env 読み込みの動作:
  - プロジェクトルートは本ファイル位置から親ディレクトリを上向きに探索し .git または pyproject.toml を探す。
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
  - 読み込み順序: OS 環境 > .env.local（上書き） > .env（上書きしない）
- J-Quants API のレート制限:
  - デフォルトで 120 req/min を守る固定間隔レートリミッタを実装。大量リクエスト時は考慮が必要。
- テストしやすさ:
  - ネットワーク呼び出し部分はモックを入れ替え可能に実装。

---

参考: 実装ファイル一覧
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/data/schema.py
- src/kabusys/data/pipeline.py
- （strategy, execution, monitoring の __init__ は空のプレースホルダとして存在）

このリリース以降の変更は本ファイルにて追記してください。