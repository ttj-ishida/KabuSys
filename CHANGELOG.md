KEEP A CHANGELOG
すべての変更は変更履歴（Keep a Changelog 準拠）に記録します。

フォーマット:
- すべての変更はカテゴリ（Added, Changed, Fixed, Security 等）に分類します。
- このファイルはコードベースから推測して作成しています。

## [0.1.0] - 2026-03-17
最初の公開リリース。日本株自動売買システムのコア基盤を実装。

### Added
- パッケージ基盤
  - kabusys パッケージの初期化（src/kabusys/__init__.py）。公開サブパッケージ: data, strategy, execution, monitoring。
  - パッケージバージョン: 0.1.0。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機構（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env / .env.local の読み込み順序と既存 OS 環境変数保護（.env.local は上書き許可、OS 環境は protected）。
  - .env のパース機能: クォート・エスケープ・インラインコメントの取り扱い、export KEY=val 形式のサポート。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供（型付きプロパティ）:
    - J-Quants / kabuステーション / Slack / データベースパス（DuckDB/SQLite）/環境（development, paper_trading, live）/ログレベル等の取得とバリデーション。
    - is_live / is_paper / is_dev 等のユーティリティプロパティ。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しの共通実装（_request）：JSON デコード、タイムアウト、ヘッダ管理。
  - レート制御: 固定間隔スロットリング実装で 120 req/min を遵守（_RateLimiter）。
  - 再試行戦略: 指数バックオフ、最大 3 回、HTTP 408/429/5xx のリトライ処理。
  - 401 Unauthorized への自動トークンリフレッシュ（get_id_token を使って一度だけリトライ）。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足 / OHLCV、pagination_key 処理）
    - fetch_financial_statements（四半期 BS/PL）
    - fetch_market_calendar（JPX 市場カレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 型安全な変換ユーティリティ: _to_float, _to_int（"1.0" などの変換ルールを明示）。
  - モジュールレベルの ID トークンキャッシュを搭載（ページネーション間で共有）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからのニュース収集機能:
    - fetch_rss: RSS 取得、XML パース（defusedxml を使用して安全化）、gzip 解凍サポート、最大受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）。
    - URL 正規化・トラッキングパラメータ除去（_normalize_url）、記事ID は正規化 URL の SHA-256 先頭32文字で生成（_make_article_id）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、プライベートアドレス検出（_is_private_host）、リダイレクト時に検証するカスタムハンドラ（_SSRFBlockRedirectHandler）。
    - テキスト前処理（URL 除去・空白正規化）および RSS pubDate の安全なパース（_parse_rss_datetime）。
  - DuckDB への保存（冪等/一括挿入）:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id をチャンク単位で実行し、新規挿入 ID を返す。トランザクションでまとめて実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING、INSERT ... RETURNING を利用）。
  - 銘柄コード抽出機能:
    - extract_stock_codes: テキスト中の 4 桁数字を抽出し、known_codes に基づきフィルタリング（重複排除）。
  - 統合収集ジョブ:
    - run_news_collection: 複数 RSS ソースからの収集を順次実行し、個別ソースの失敗を他に影響させず処理を継続。新規記事の銘柄紐付けを一括で処理。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DataPlatform に基づく 3 層＋実行層のテーブル定義（Raw / Processed / Feature / Execution）を実装:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY）と型を定義。
  - 頻出クエリ向けのインデックス群を定義（idx_prices_daily_code_date など）。
  - init_schema(db_path) によりディレクトリ作成→接続→DDL 実行で初期化を行う（冪等）。
  - get_connection(db_path) を提供（初期化済み DB に接続）。

- ETL パイプライン基礎（src/kabusys/data/pipeline.py）
  - ETL の設計方針と差分更新フローを実装（差分取得、保存、品質チェックの呼び出しを想定）。
  - 定数:
    - データ開始日: _MIN_DATA_DATE = 2017-01-01
    - カレンダー先読み: _CALENDAR_LOOKAHEAD_DAYS = 90
    - デフォルトバックフィル日数: _DEFAULT_BACKFILL_DAYS = 3
  - ETLResult dataclass により ETL 実行結果/品質問題/エラーを構造化して返却可能に（to_dict で品質問題をシリアライズ）。
  - DB ヘルパー: テーブル存在チェック、最大日付取得（_get_max_date）、最終取得日の取得ユーティリティ（get_last_price_date 等）。
  - 市場カレンダー参照のための trading day 調整ヘルパー（_adjust_to_trading_day）。
  - run_prices_etl の差分更新ロジック（最終取得日 - backfill を起点に取得、J-Quants クライアント経由で取得→保存）を実装（差分ETLの骨組み）。

- その他
  - 各モジュールに詳細なドキュメント文字列（docstring）を追加し設計方針・安全上の考慮点（Look-ahead 防止、冪等性、SSRF 対策、Gzip/XmlBomb 対策等）を明記。
  - 型アノテーションを広く採用し、テスト容易性を考慮した設計（例: id_token 注入、_urlopen の差し替え可能化など）。
  - ロギングを適切に配置（情報・警告・例外ログ）。

### Security
- RSS/HTTP 関連の安全対策を導入:
  - defusedxml による XML パース（XML Bomb 防止）。
  - URL スキーム検証（http/https のみ）とプライベートネットワーク判定で SSRF を防止。
  - リダイレクト時にもスキーム・ホストの検査を行うカスタムリダイレクトハンドラを導入。
  - レスポンスサイズ上限（10MB）と gzip 解凍後の再チェックでメモリ DoS を低減。

### Known limitations / Notes
- quality モジュール参照あり（pipeline から参照）が、今回提示されたコードでは quality モジュールの実装詳細は含まれていません（品質チェックは外部実装を想定）。
- run_prices_etl の実装はファイル末尾で切れているため、完全な ETL フロー（戻り値や追加処理）はソース全体の続きに依存します。
- strategy/execution/monitoring サブパッケージは __init__.py が存在し、将来的な機能実装のためのプレースホルダとなっています。

### Breaking Changes
- 初期リリースのため該当なし。

（以上）