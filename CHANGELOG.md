# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトのバージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買プラットフォーム「KabuSys」の基礎機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ初期化（src/kabusys/__init__.py）:
    - バージョン情報 __version__ = "0.1.0"
    - public API を示す __all__ 定義（data, strategy, execution, monitoring）
  - strategy, execution, monitoring のモジュール雛形を追加（空の __init__.py）。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - .env パースの堅牢化:
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - OS 環境変数を保護する protected 上書きロジック（.env.local の override 挙動）。
  - Settings クラス:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite）/ 環境種別（development/paper_trading/live）/ログレベルなどの取得プロパティ。
    - env 値や LOG_LEVEL のバリデーションを実装。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- データ取得クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアント実装:
    - レート制限（120 req/min）の固定間隔スロットリング実装（内部 RateLimiter）。
    - リトライ戦略（指数バックオフ、最大 3 回）、対象ステータス（408, 429, 5xx）に対する再試行。
    - 401 Unauthorized 受信時の ID トークン自動リフレッシュ（1 回のみ）とトークンキャッシュの共有（モジュールレベル）。
    - GET/POST 汎用リクエストラッパ _request を実装（JSON デコードエラーハンドリングなど）。
  - データ取得関数:
    - fetch_daily_quotes: 日足（OHLCV）をページネーション対応で取得。
    - fetch_financial_statements: 四半期財務データ取得（ページネーション対応）。
    - fetch_market_calendar: JPX マーケットカレンダー取得。
  - DuckDB へ冪等的に保存する関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes: raw_prices へ保存、fetched_at を UTC ISO8601 で記録。
    - save_financial_statements: raw_financials へ保存。
    - save_market_calendar: market_calendar へ保存（is_trading_day / is_half_day / is_sq_day の解釈を含む）。
  - ユーティリティ:
    - _to_float / _to_int：型変換の堅牢処理（空値・不整値処理、"1.0" のような文字列対応、切り捨て回避ロジック）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS 収集の実装（デフォルトに Yahoo Finance のビジネス RSS を定義）。
  - セキュリティ重視の設計:
    - defusedxml による XML パース（XML BOM や攻撃対策）。
    - SSRF 対策: リダイレクトハンドラでスキーム検証およびプライベートIP の拒否（_SSRFBlockRedirectHandler、_is_private_host）。
    - URL スキームチェック（http/https のみ）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、読み取り時に超過判定（gzip 解凍後も検査）。
    - Content-Length の事前チェックと読み取りバイト数チェック。
  - データ処理:
    - URL 正規化（_normalize_url）で tracking パラメータ（utm_* など）を除去、クエリソート、フラグメント削除。
    - 記事ID を正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成（_make_article_id）。
    - テキスト前処理（URL 除去・空白正規化）を実装（preprocess_text）。
    - RSS pubDate のパースと UTC 換算（_parse_rss_datetime）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用いたチャンク挿入（トランザクションでまとめる）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等的に保存（チャンク、トランザクション、RETURNING カウント）。
  - 銘柄コード抽出:
    - extract_stock_codes: 正規表現により 4 桁の候補を抽出し、known_codes に基づいてフィルタ（重複排除）。
  - 統合収集ジョブ:
    - run_news_collection: 複数 RSS ソースからの収集→保存→（known_codes が与えられた場合）銘柄紐付けを実行。各ソースは独立してエラーハンドリング。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DataPlatform に基づく3層以上のスキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）を定義。
  - 利用頻度に応じたインデックスを作成（例: code/date 組合せ、status 検索用など）。
  - init_schema(db_path) を実装: ディレクトリ自動作成、全テーブル/インデックスを冪等的に作成して接続を返す。
  - get_connection(db_path): 既存 DB への接続取得（初期化は行わない）。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETLResult dataclass を導入（取得数、保存数、品質チェック結果、エラーリストなどを集約）。
  - 差分更新用ユーティリティ:
    - テーブル存在チェック、テーブル内の最大日付取得ヘルパー。
    - 市場カレンダーに基づく営業日調整（_adjust_to_trading_day）。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date ヘルパー。
  - run_prices_etl の雛形を実装:
    - date_from の自動決定（DB 最終取得日 - backfill_days ルール、初回ロード用の最小日付定義）。
    - J-Quants クライアントを使った fetch_daily_quotes → save_daily_quotes の流れを実装。
    - backfill_days のデフォルト値など ETL 設計方針を注釈として明記。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集周りで複数の攻撃対策を導入:
  - defusedxml 使用、XML パースエラーのハンドリング。
  - SSRF 対応（リダイレクト時のスキームチェック / プライベートIP拒否、初回ホスト検証）。
  - レスポンスサイズ制限と gzip 解凍後の再チェック（Gzip bomb 対策）。
  - RSS 内の不正スキーム（file:, javascript:, mailto: 等）を排除。

### Known limitations / Notes
- run_prices_etl は基本的な差分ロジックと保存処理を実装していますが、pipeline モジュール内の品質チェック（quality モジュール連携）や完全なエラー集約・ログ出力のワークフローは外部モジュール（kabusys.data.quality 等）に依存します。quality モジュールの実装状況により追加の統合が必要です。
- strategy / execution / monitoring モジュールは雛形のみ提供。発注ロジックや戦略、監視機能は今後実装予定です。
- API クライアントでは urllib を用いているため、より高度な HTTP 要求（セッション管理、接続プール化）が必要な場合は将来の改善候補です。
- DuckDB の SQL 実行文字列は直接組み立てる箇所があり（プレースホルダーで値は渡していますが）、SQL インジェクション対策は用途に応じて追加レビューを推奨します（現在は内部利用を想定）。

---

今後の予定:
- ETL の品質チェック実装と自動通知（Slack 等）統合。
- execution モジュールでの注文送信・約定管理（kabuステーション API 統合）。
- strategy モジュールにおける特徴量生成・シグナル生成ロジックの実装。
- 単体テスト・統合テストの拡充と CI パイプライン整備。