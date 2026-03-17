Keep a Changelog に準拠した形式で、コードベースから推測した変更履歴（日本語）を作成しました。

CHANGELOG.md
=============

全般
----
- 本リポジトリは日本株自動売買システム「KabuSys」の初期リリース相当の内容を含みます。
- パッケージバージョン: 0.1.0
- リリース日: 2026-03-17

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ構成（モジュールの追加）
  - kabusys パッケージの初期公開 API を定義（__version__ = 0.1.0、__all__ に data, strategy, execution, monitoring を設定）。
- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - .git または pyproject.toml を起点にプロジェクトルートを探索して .env/.env.local を読み込む仕組みを提供（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env のパース処理を詳細に実装（export プレフィックス、クォート内のエスケープ、行末コメントの取り扱いなど）。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス等の設定をプロパティ経由で取得。値検証（KABUSYS_ENV, LOG_LEVEL）やパス型変換（DuckDB/SQLite）を実装。
  - 必須環境変数未設定時は明確なエラーメッセージを出す _require() を提供。
- J-Quants クライアント（kabusys.data.jquants_client）
  - J-Quants API から株価日足、財務データ（四半期 BS/PL）、市場カレンダーを取得するクライアントを実装。
  - API レート制限を守る固定間隔スロットリング実装（_RateLimiter、120 req/min 相当）。
  - 再試行ロジック（最大3回、指数バックオフ、408/429/5xx をリトライ対象）。429 の場合は Retry-After ヘッダを優先。
  - 401 発生時はリフレッシュトークンで id_token を自動更新して 1 回だけリトライする仕組み（トークンキャッシュ共有）。
  - ページネーション対応の取得関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB に対する冪等保存（ON CONFLICT DO UPDATE）を行う save_* 関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正値を安全に扱う。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead Bias のトレースを可能に。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュースを収集し raw_news, news_symbols へ保存するモジュールを実装。
  - セキュリティ対策を多数実装:
    - defusedxml を使った XML パース（XML Bomb 等の回避）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベート/ループバック判定、リダイレクト検査用ハンドラ (_SSRFBlockRedirectHandler)。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）、gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事IDの SHA-256（先頭32文字）による生成で冪等性を担保。
  - fetch_rss: RSS 取得＆パース、content:encoded を優先する本文抽出、記事テキストの前処理（URL除去・空白正規化）を実装。
  - save_raw_news: INSERT ... RETURNING を用いて新規挿入された記事IDのみを返す。チャンク挿入、トランザクション制御により効率的かつ安全に保存。
  - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括保存（ON CONFLICT DO NOTHING、RETURNING で挿入数取得）。重複ペアの除去、チャンク処理、トランザクション制御を実装。
  - 銘柄コード抽出ロジック（extract_stock_codes）: 正規表現で4桁数値を抽出し、既知銘柄セットでフィルタして重複を除去。
  - run_news_collection: 複数RSSソースを順次処理し、エラーが発生しても他ソースを継続。新規保存数を返す集約ジョブ。
- DuckDB スキーマ管理（kabusys.data.schema）
  - DataSchema に基づく多層スキーマを定義（Raw / Processed / Feature / Execution 層）。
  - 主要テーブルを網羅的に定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 各テーブルに制約（PRIMARY KEY、CHECK 等）を付与し、外部キー依存を考慮した作成順を実装。
  - 頻出クエリ向けのインデックスを定義（code/date や status 等）。
  - init_schema(db_path) によりディレクトリ作成/DDL 実行を行い、DuckDB 接続を返す。get_connection(db_path) で既存DBへ接続可能。
- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計（差分更新、backfill、品質チェックの方針）に沿った基盤を実装。
  - ETLResult dataclass を導入し、処理結果（取得数、保存数、品質問題、エラー）を集約して保持可能。
  - DB テーブル存在チェック、最大日付取得ユーティリティ（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダーを用いた営業日調整ヘルパー (_adjust_to_trading_day) を実装。
  - run_prices_etl: 差分取得ロジック（最終取得日に基づく date_from の自動算出、backfill_days による再取得）を実装。jquants_client の fetch/save を使って差分ETLを行う。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Notes / 補足
- 設計上の注意点・強化点（コードから推測）
  - 環境変数読み込みはプロジェクトルート検出に依存するため、配布後の挙動はプロジェクト配布方式により影響を受ける可能性あり（パッケージ化時は自動ロードを明示的に管理することを推奨）。
  - ニュース収集での URL 正規化やトラッキングパラメータ除去ルールは既知のプレフィックスに依存しており、追加のプレフィックスが必要になる可能性がある。
  - run_prices_etl の戻り値処理（tuple の返却等）や pipeline の品質チェック連携は今後の拡張対象（コード断片の末尾に未完の返却が見られるため実装の最終調整が必要な箇所がある可能性あり）。
  - DuckDB のトランザクション実装や INSERT ... RETURNING を活用しているが、実運用でのパフォーマンス監視・チューニングを推奨。

今後の TODO（推測）
- ETL の全ジョブ（財務・カレンダー含む）を統合した上での監査ログとスケジューリングの実装。
- strategy / execution / monitoring モジュールの具体実装（現状はパッケージとしてプレースホルダ）。
- 単体テスト・統合テスト、外部 API モックによる CI の構築。
- 詳細なエラーハンドリング方針のドキュメント化（品質チェックが検出した場合の運用フロー等）。

以上。必要であれば、各モジュールごとにより詳細な変更点（関数一覧や公開 API 列挙）を含めた拡張版の CHANGELOG を作成します。どのレベルの詳細が必要か教えてください。