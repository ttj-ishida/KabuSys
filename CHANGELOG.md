# Changelog

すべての注目すべき変更履歴はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに準拠しています。

フォーマット: 標準的なカテゴリ (Added, Changed, Fixed, Deprecated, Removed, Security)

## [0.1.0] - 2026-03-18

### Added
- 全体
  - 初回リリース。パッケージ名は `kabusys`。パッケージバージョンは `0.1.0` に設定。
  - モジュール構成を追加: `kabusys.config`, `kabusys.data`, `kabusys.strategy`（空のパッケージ初期化子あり）、`kabusys.execution`（空のパッケージ初期化子あり）。

- 設定管理 (`kabusys.config`)
  - 環境変数/設定管理モジュールを実装。`.env` / `.env.local` からの自動読み込みを行う（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）。
  - `.env` パーサーを実装（コメント行、`export KEY=val` 形式、シングル/ダブルクォート、インラインコメント処理、エスケープ処理に対応）。
  - 自動読み込みを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 必須設定取得ヘルパー `_require()` と、`Settings` クラスを提供。J-Quants、kabu API、Slack、データベースパス、環境/ログレベル等のプロパティを用意。
  - `KABUSYS_ENV` / `LOG_LEVEL` の検証（許可値のチェック）と便利な `is_live` / `is_paper` / `is_dev` プロパティ。

- J-Quants クライアント (`kabusys.data.jquants_client`)
  - J-Quants API 用クライアントを実装。主な機能:
    - レート制御（120 req/min）を行う固定間隔スロットリング `_RateLimiter`。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時にリフレッシュを一回だけ行うトークン自動更新（`get_id_token` とトークンキャッシュ `_ID_TOKEN_CACHE`）。
    - JSON パースエラー検出・詳細メッセージ。
  - データ取得関数を提供:
    - fetch_daily_quotes(...) — 日次株価（OHLCV）をページネーション対応で取得。
    - fetch_financial_statements(...) — 財務（四半期 BS/PL）をページネーション対応で取得。
    - fetch_market_calendar(...) — JPX マーケットカレンダー取得。
  - DuckDB への冪等保存関数を提供:
    - save_daily_quotes(conn, records) — `raw_prices` に ON CONFLICT DO UPDATE で保存。
    - save_financial_statements(conn, records) — `raw_financials` に ON CONFLICT DO UPDATE。
    - save_market_calendar(conn, records) — `market_calendar` に ON CONFLICT DO UPDATE。
  - データ型変換ユーティリティ `_to_float` / `_to_int`（不正値を安全に None に変換）。

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィードからニュースを収集して DuckDB に保存するモジュールを実装。
  - セキュリティ/堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - SSRF 対策: URL スキーム検証、プライベートアドレス判定（直接 IP と DNS 解決の両方）、リダイレクト時の検査用ハンドラ `_SSRFBlockRedirectHandler`。
    - 応答サイズ制限（最大 10 MB）と gzip 解凍後の追加サイズチェック（Gzip bomb 対策）。
    - 許可スキームは http/https のみ。
  - 正規化・前処理:
    - URL 正規化とトラッキングパラメータ削除（`_normalize_url`）。
    - 記事ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成（`_make_article_id`）。
    - 本文の前処理（URL 除去、空白正規化）`preprocess_text`。
    - pubDate の RFC2822 解析と UTC 変換 `_parse_rss_datetime`。
  - フィード取得・DB保存:
    - fetch_rss(url, source, timeout) — RSS を取得して NewsArticle リストを返す（XML パース失敗等は警告で空リストを返す）。
    - save_raw_news(conn, articles) — `raw_news` にチャンク挿入し、実際に挿入された記事ID一覧を返す（INSERT ... RETURNING を利用、トランザクションまとめ）。
    - save_news_symbols / _save_news_symbols_bulk — `news_symbols` テーブルへの銘柄紐付けを一括保存（重複排除、トランザクション）。
  - 銘柄コード抽出:
    - extract_stock_codes(text, known_codes) — 4桁数字パターンから既知コード集合に基づいて抽出。

- スキーマ管理 (`kabusys.data.schema`)
  - DuckDB 用のスキーマ定義と初期化関数を追加。
  - データレイヤーを意識したテーブル群を定義（Raw / Processed / Feature / Execution 層）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各カラムに型チェック制約や PRIMARY/FOREIGN KEY を付与。
  - パフォーマンスを考慮したインデックス群を作成。
  - init_schema(db_path) — DB ファイルの親ディレクトリ自動作成、全テーブルとインデックスを作成して接続を返す（冪等）。
  - get_connection(db_path) — 既存 DB への接続取得（スキーマ初期化は行わない）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - ETL 実行ロジックの骨格を実装。
  - ETLResult dataclass を追加して実行結果（取得数・保存数・品質問題・エラー）を構造化。
  - 差分更新ユーティリティ:
    - _table_exists, _get_max_date を用いた最終取得日の判定。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
    - _adjust_to_trading_day — 非営業日を直近の営業日に調整するヘルパー。
  - run_prices_etl(...) — 日次株価の差分 ETL を実装（最終取得日からの backfill、`jquants_client.fetch_daily_quotes` と `save_daily_quotes` を使用）。品質チェックモジュール `kabusys.data.quality` を参照する設計（品質チェックロジックは別モジュール想定）。
  - 設計方針: 差分更新、backfill による後出し修正吸収、id_token を注入可能にしてテスト容易性を確保。

- その他
  - デフォルト RSS ソースを `yahoo_finance` に設定（ビジネスカテゴリ RSS）。
  - 各モジュールでロギングを活用し情報・警告・例外の記録に対応。

### Security
- セキュリティ対策を多数実装:
  - RSS/HTTP フェッチにおける SSRF 対策・プライベートアドレス検出。
  - defusedxml による安全な XML パース。
  - レスポンスの最大サイズチェックと gzip 解凍後の追加チェック（DoS 対策）。
  - 環境変数の扱いで OS 環境変数を保護する仕組み（`.env` 読み込み時の protected パラメータ）。

### Fixed
- （初版のため該当なし）

### Changed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

---

注記:
- 本 CHANGELOG はコードベースから想定される機能・設計意図に基づいて作成しています。実際のリリースノート作成時は実装済み機能と差分をご確認の上、適宜更新してください。