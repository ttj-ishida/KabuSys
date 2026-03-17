CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

[unreleased]: https://example.com/kabusys/compare/0.1.0...HEAD

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買プラットフォームのコア機能群を実装しました。
主要な追加点、設計方針、既知の問題を以下にまとめます。

Added
-----
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - パブリックAPIとして data, strategy, execution, monitoring をエクスポート（注: monitoring モジュールは現状ソースに含まれていません。後続リリースで追加予定）。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動ロード（プロジェクトルートは .git または pyproject.toml から検出）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 読み込みの優先順位: OS環境変数 > .env.local > .env。既存OS環境変数は保護（上書き回避）。
  - .env パーサーは export KEY=val 形式、引用符付き値（エスケープ対応）、インラインコメントの扱い等に対応。
  - Settings クラスを提供し、主要設定プロパティを型付きで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL,
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID,
    - DUCKDB_PATH, SQLITE_PATH,
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）,
    - LOG_LEVEL（DEBUG/INFO/... のバリデーション）,
    - is_live / is_paper / is_dev ヘルパー。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 基本機能:
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得メソッドを実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - ページネーション対応（pagination_key を利用して複数ページを結合）。
  - レート制御とリトライ:
    - レート制限: 固定間隔スロットリングで 120 req/min を保証（_RateLimiter）。
    - リトライ: 指数バックオフ（最大 3 回）を実装。HTTP 408/429/5xx やネットワークエラーをリトライ対象に。
    - 429 の場合は Retry-After を優先して待機。
  - 認証:
    - リフレッシュトークンから ID トークンを取得する get_id_token を提供（POST）。
    - 401 を受信した場合は ID トークンを自動リフレッシュして 1 回のみリトライ（無限再帰防止）。
    - モジュールレベルの ID トークンキャッシュを保持（ページネーションなどでトークンを共有）。
  - DuckDB 保存:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - 保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で、fetched_at を UTC（Z 表記）で記録。
    - 不完全な PK を持つ行はスキップし警告ログ出力。
  - ユーティリティ:
    - _to_float / _to_int 変換ユーティリティ（空値・変換失敗時は None。_to_int は "1.0" のようなケースに注意して扱う）。

- ニュース収集（RSS）モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事収集と DuckDB への保存機能を実装（fetch_rss, save_raw_news, save_news_symbols 等）。
  - セキュリティ / 安全性設計:
    - defusedxml を利用して XML 攻撃を防御。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルでないことを検査（DNS 解決して A/AAAA を確認）、リダイレクト先も検査。
    - 受信サイズ上限 MAX_RESPONSE_BYTES（デフォルト 10 MB）を導入しメモリDoSを防止。gzip 解凍後もサイズチェック。
    - User-Agent と Accept-Encoding を設定して取得。
  - データ整備:
    - URL の正規化（小文字化、トラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - 記事IDは正規化 URL の SHA-256 ハッシュ先頭32文字で生成し冪等性を確保。
    - テキスト前処理（URL 除去、空白正規化）。
    - pubDate の RFC 2822 パース（失敗時は UTC 現在時刻で代替し警告）。
  - DB 保存の工夫:
    - save_raw_news はチャンク毎に INSERT ... ON CONFLICT DO NOTHING RETURNING id を行い、実際に挿入された新規記事IDのみを返す。トランザクションでまとめて処理。
    - save_news_symbols / _save_news_symbols_bulk は (news_id, code) ペアを重複排除してチャンク挿入、INSERT ... RETURNING を利用して正確な挿入数を返却。
  - 銘柄抽出:
    - 4桁数字パターンで候補を抽出し、known_codes セットでフィルタ（extract_stock_codes）。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）および Execution レイヤーのテーブル定義を実装。
  - 代表的なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（PRIMARY KEY / CHECK / FOREIGN KEY）を設定。
  - パフォーマンスを考慮したインデックス群（code×date 検索、status 検索など）を作成。
  - init_schema(db_path) でディレクトリ作成（必要なら）→ テーブル/インデックス作成、get_connection で既存 DB へ接続。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETLResult dataclass による ETL 実行結果の構造化（品質問題とエラーメッセージの集約、辞書変換）。
  - 差分取得支援:
    - DB の最終取得日を取得するヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダーを参照して非営業日を直近営業日に調整する _adjust_to_trading_day。
  - run_prices_etl 実装（差分更新、backfill 対応、fetch → save のフロー）。デフォルトの backfill_days = 3。
  - 設計方針:
    - 差分単位は営業日ベース、backfill により API の後出し修正を吸収。
    - 品質チェックモジュール（quality）と連携する想定（品質問題が発生しても ETL は継続し、呼び出し側が対応判断を行う）。

Changed
-------
- （初版リリースのため「変更」はなし。今後のリリースで差分を記載予定。）

Fixed
-----
- （初版リリースのため「修正」はなし。）

Security
--------
- 外部入力処理・ネットワーク取得に対するセキュリティ対策を各所に導入:
  - defusedxml による XML パースの安全化（XML Bomb 等の緩和）。
  - SSRF 対策（スキーム検証、プライベートIP検査、リダイレクト検査）。
  - レスポンスサイズ上限・gzip 解凍後のサイズ検査によりメモリ DoS を緩和。
  - .env ファイル読み込みではファイル読み取り失敗に対して警告を出すのみで安全にフォールバック。

Known Issues / Notes
--------------------
- run_prices_etl の戻り値に関するバグ:
  - 実装では最後に "return len(records)," としており、型注釈 (tuple[int,int]) と一致しません。意図としては (fetched_count, saved_count) を返すべきで、現状は単要素のタプルを返却してしまいます（実行時に呼び出し側で混乱を招く恐れあり）。次版で修正予定（return len(records), saved）。
- パッケージ公開 API に含めている monitoring は現行ソースに存在しません。monitoring 機能・モジュールは未実装／別ブランチ扱いの可能性があるため注意。
- strategy/ と execution/ の __init__.py はプレースホルダ（現状内部実装は未追加）。戦略実装および発注ロジックは今後のリリースで提供予定。
- quality モジュールは pipeline で参照しているが、品質チェックの具体的な実装（QualityIssue の定義や個別チェック）は別途実装が必要（現状のコードは quality モジュールの存在を前提としている）。

開発・運用上の補足
-----------------
- DuckDB を利用したスキーマ設計はローカル実行/テストに適しており、":memory:" を利用した一時 DB もサポートします。
- J-Quants API 周りはトークン管理とレート制御を取り入れているため、実運用では環境変数 JQUANTS_REFRESH_TOKEN を確実にセットすること（Settings.jquants_refresh_token が必須）。
- ニュース収集で銘柄抽出を有効にするには known_codes のセットを渡す必要があります（run_news_collection の引数）。

署名
----
このリリースはコアデータ取得・保存・ETL の基盤を備えた初期実装です。今後のリリースで以下を予定しています:
- strategy / execution の具体的戦略とバックテスト・発注の統合
- monitoring モジュールの追加（Slack 通知等）
- quality モジュールの具体的チェック群と自動アラート
- 単体テスト・統合テストの拡充と CI 設定

[0.1.0]: https://example.com/kabusys/releases/tag/0.1.0