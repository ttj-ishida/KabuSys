CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
初回リリース (0.1.0) として、パッケージのコア機能（設定、データ取得・保存・スキーマ、ニュース収集、ETLパイプラインの基礎）を実装しています。

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージの初期公開 (kabusys) とバージョン定義
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env/.env.local の自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - .env の各行のパースロジックを実装（export プレフィックス、クォート、インラインコメントの扱いに対応）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを公開し、J-Quants トークン、kabu API 設定、Slack トークン、DBパス、環境（development/paper_trading/live）などのプロパティを提供。
  - env/log_level の値検証（許可値チェック）と is_live/is_paper/is_dev ヘルパーを追加。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足、財務、マーケットカレンダー取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - API 呼び出し共通処理で以下を実装:
    - 固定間隔のレート制限 (120 req/min) を守る RateLimiter。
    - 冪等性確保のための id トークンキャッシュと自動リフレッシュ (401 時に 1 回自動更新)。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象、429 の Retry-After 優先）。
    - JSON デコード失敗時の明示的なエラー化。
  - DuckDB への保存用ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を追加。すべて ON CONFLICT による更新で冪等性を確保。
  - レコード変換ユーティリティ（_to_float, _to_int）を実装し、空値や不正値を安全にハンドリング。
  - fetch_*/save_* 間のページネーション処理に対応（pagination_key）。
  - fetched_at に UTC ISO タイムスタンプを付与して「いつデータを取得したか」をトレース可能に。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得して raw_news に保存する一連の処理を実装（fetch_rss, save_raw_news, save_news_symbols, _save_news_symbols_bulk, run_news_collection）。
  - セキュリティ・堅牢性対策を多数実装:
    - defusedxml を用いた XML パース（XML Bomb 等への対応）。
    - SSRF 対策: URL スキーム検証、ホストがプライベート/ループバック/リンクローカルかを検査、リダイレクト時にも検証するカスタムリダイレクトハンドラを提供。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) を導入し、受信・gzip 解凍後のサイズチェックを実施。
    - 受信時の Content-Length 前検査および実際の読み込みでの上限判定。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と SHA-256 ハッシュの先頭32文字を記事IDとして採用（冪等性確保）。
    - URL 抽出と本文前処理（URL 除去・空白正規化）。
  - DB 保存ではバルクチャンク挿入とトランザクション管理を実装。INSERT ... ON CONFLICT DO NOTHING と RETURNING を使い、新規挿入された記事のみを正確に把握。
  - 記事本文から 4 桁銘柄コードを抽出する extract_stock_codes を実装し、既知コードセットで絞り込み（run_news_collection で news_symbols への紐付けをバッチで実行）。

- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層を含むデータベース DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw 層テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed 層を定義。
  - features, ai_scores など Feature 層、signals, signal_queue, orders, trades, positions, portfolio_performance など Execution 層を定義。
  - 頻出クエリ向けのインデックス定義を追加（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) でディレクトリ作成→接続→全DDL/インデックス実行の初期化処理を提供。get_connection() で既存 DB へ接続。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETL 実行結果を表す dataclass ETLResult を実装（品質問題リストやエラーを格納、辞書化メソッドを提供）。
  - 差分取得ヘルパー（テーブル存在確認、最大日付取得）を実装。
  - 市場カレンダーを考慮した trading day 調整関数 _adjust_to_trading_day を追加。
  - run_prices_etl の差分更新ロジック（最終取得日からの backfill 日数の導入、デフォルト backfill_days = 3）および jq.fetch_* / save_* の呼び出しで差分更新を行う仕組みを実装。
  - 最小データ開始日 _MIN_DATA_DATE およびカレンダー先読み日数定数を追加。
  - 品質チェック module (kabusys.data.quality) を想定した設計（ETLResult で品質問題を扱う）を導入。

Changed
- パッケージ構成（モジュール分割）
  - data, strategy, execution, monitoring を __all__ に公開している（src/kabusys/__init__.py）。サブパッケージのスケルトンが整備済み。

Fixed
- （初回リリースのためこのセクションは空）

Security
- ニュース収集の SSRF 対策、defusedxml による XML パース保護、レスポンスサイズ制限、URL スキーム検証などを導入（src/kabusys/data/news_collector.py）。
- API クライアントの例外とリトライ処理を厳格化することで想定外のネットワーク/HTTP エラーを安全に扱う設計（src/kabusys/data/jquants_client.py）。

Notes / Implementation details
- DuckDB を使用した永続化を前提としており、settings.duckdb_path / settings.sqlite_path 等でパスを指定可能。
- jquants_client のレート制御は固定スロット方式（_RateLimiter）で実装されており、120 req/min をデフォルトとする。
- ニュース記事 ID は URL 正規化後の SHA-256 ハッシュ先頭 32 文字を使用し、utm_* 等のトラッキングパラメータは除去することで同一記事の重複登録を抑制する。
- ETL ではバックフィル日数により「最終取得日の数日前から再取得」して API の後出し修正を吸収する戦略を採用。

今後の予定（例）
- pipeline.run_prices_etl の継続実装（メソッド末尾が途中で終わっている箇所の完成）。
- quality モジュールの実装と ETL による品質チェック統合。
- strategy / execution / monitoring の具象実装（現在はパッケージスケルトン）。

--------------------------------
この CHANGELOG はソースコードからの推測に基づいて作成しています。実際のリリースノートに使用する場合は、差分の正確性をリポジトリの変更履歴（コミット/PR）と照合してください。