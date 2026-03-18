Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」規約に準拠します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-18
--------------------

Added
- パッケージ初回リリース (kabusys v0.1.0)
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定/ロード機能（kabusys.config）
  - .env / .env.local からの自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使った自動ロード無効化に対応。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント処理など）。
  - Settings クラスを提供：
    - J-Quants / kabu API / Slack / DB パス等のプロパティを提供（必須キーは未設定時に例外を投げる）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性検証（開発・ペーパー・本番、ログレベルのホワイトリスト）。
    - is_live / is_paper / is_dev の便利プロパティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 基本機能：
    - 株価日足（fetch_daily_quotes）
    - 財務データ（fetch_financial_statements）
    - JPX マーケットカレンダー（fetch_market_calendar）
  - 設計上の特徴：
    - 固定間隔（120 req/min）を守る RateLimiter を実装。
    - リトライ（指数バックオフ、最大 3 回）と 429 の Retry-After ヘッダ優先対応。
    - 401 受信時は refresh トークンで自動リフレッシュして 1 回だけリトライ（再帰防止）。
    - ページネーション対応（pagination_key を利用した取得ループ）。
    - モジュールレベルのトークンキャッシュを提供（ページネーション間で共有）。
  - DuckDB への保存関数（冪等性）：
    - save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT DO UPDATE によるアップサート、fetched_at の UTC 記録、PK 欠損行のスキップログ。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからの記事取得と前処理機能：
    - RSS 取得（fetch_rss）、XML パース（defusedxml を使用）、gzip 対応、Content-Length / レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES）。
    - リダイレクト時のスキーム/ホスト検証（SSRF 対策）を行うカスタム RedirectHandler。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント削除）。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）。
    - RSS pubDate の堅牢なパース（UTC 正規化、パース失敗時は代替）。
  - DuckDB への保存（トランザクション・バルク挿入）：
    - save_raw_news：チャンク分割、INSERT ... ON CONFLICT DO NOTHING + RETURNING id による新規挿入ID取得、1 トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk：news_symbols の一括保存（重複除去、チャンク挿入、RETURNING による実挿入数取得）。
  - 銘柄抽出機能：
    - 4桁数字パターンから既知銘柄セットに基づく抽出（extract_stock_codes）。
  - 統合収集ジョブ（run_news_collection）：複数ソース処理、個別ソースのエラーハンドリング、新規記事の銘柄紐付けを一括で行う。

- DuckDB スキーマ定義/初期化（kabusys.data.schema）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）+ Execution レイヤーのテーブル定義を実装。
  - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等。
  - 各種制約・CHECK・PRIMARY KEY を含む DDL、頻出クエリ向けのインデックス群を定義。
  - init_schema(db_path) によりディレクトリ自動作成と DDL 実行（冪等）を行い、接続を返す。get_connection() を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass による ETL 実行結果の表現（品質問題・エラーの収集、辞書化メソッド）。
  - テーブル存在チェック、最大日付取得ユーティリティ。
  - market_calendar を参照した非営業日調整ヘルパー（_adjust_to_trading_day）。
  - 差分更新ロジックのサポート（最終取得日からの backfill 計算、_MIN_DATA_DATE、calendar lookahead など）。
  - run_prices_etl の差分取得処理（date_from 自動決定、jq.fetch_daily_quotes / jq.save_daily_quotes を使用）を実装。

Security
- ニュース収集での SSRF 対策:
  - リダイレクト先のスキーム/ホスト検証（_SSRFBlockRedirectHandler）。
  - 初回 URL と最終 URL のプライベートアドレス検査（_is_private_host）。
  - defusedxml を使った XML パース（XML Bomb 等の脆弱性緩和）。
  - レスポンスの最大サイズチェックと gzip 解凍後のサイズ検査（Gzip bomb 対策）。
- J-Quants クライアントではトークン管理・自動リフレッシュの設計により認証エラーに対処。

Notes / Known limitations
- run_prices_etl の実装で末尾の return が不完全（ソース上は "return len(records), " のみ）となっているため、そのままの状態では期待される (fetched_count, saved_count) タプルを返さない可能性があります。リリース後に修正が必要です。
- パッケージの一部 __init__.py（strategy, execution, data）等はプレースホルダ（空実装）であり、追加機能は今後のリリースで拡張予定です。
- DuckDB へ保存するスキーマ/型は厳密な CHECK を含むため、外部データの型・範囲エラーに注意が必要です（save_* 関数は PK 欠損行をスキップし、ログ出力します）。
- RSS パースやネットワーク呼び出しは外部依存が強いため、ユニットテストでは _urlopen や jq の HTTP 呼び出し等をモックすることを想定しています。

Acknowledgements / Design notes
- 各モジュールには設計原則（冪等性、Look-ahead Bias の防止、API レート制御、トランザクションまとめ挿入など）が明記されています。今後は品質チェック（kabusys.data.quality 想定）の統合や、戦略／実行層の実装を進めます。

---- 

（この CHANGELOG はコードベースから推測して作成しました。実際のリリースノート作成時は、変更者による確認・追記を推奨します。）