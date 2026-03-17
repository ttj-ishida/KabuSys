# Changelog

すべての重要な変更は、このファイルに記録します。
フォーマットは「Keep a Changelog」（https://keepachangelog.com/）に従っています。

注: 以下はソースコード（src/ 配下）の内容から推測してまとめた初期リリース向けの変更履歴です。

## [0.1.0] - 2026-03-17

### Added
- 初期リリース。日本株自動売買システム「KabuSys」基盤を実装。
- パッケージ構成（モジュールの公開）を追加
  - src/kabusys/__init__.py にてバージョンと公開サブパッケージを定義（data, strategy, execution, monitoring）。
- 環境変数・設定管理（src/kabusys/config.py）
  - プロジェクトルート自動検出ロジック（.git または pyproject.toml を基準）を実装し、CWD に依存しない .env 自動ロードを採用。
  - .env / .env.local の順序で読み込み、OS 環境変数は保護（上書き抑止）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化フラグをサポート。
  - .env の行パーサーに対応（コメント、export プレフィックス、クォート内のエスケープ等）。
  - Settings クラスを公開し、J-Quants / kabu / Slack / データベースパス / 環境種別 / ログレベル等のプロパティを提供。環境値のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL）。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しの共通実装（_request）を提供。JSON デコードの検証、タイムアウト、ヘッダ設定等を含む。
  - 固定間隔のレートリミッタ実装（120 req/min に対応する _RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）を実装。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装。モジュールレベルで ID トークンをキャッシュしてページネーション間で共有可能。
  - データ取得関数を実装（ページネーション対応）:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB へ冪等に保存する save_* 関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 型変換ユーティリティ（_to_float, _to_int）を実装。細かな入力不整合に耐性を持たせる。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS からの記事収集パイプラインを実装（fetch_rss, save_raw_news, save_news_symbols 等）。
  - セキュリティ対策を重点実装:
    - defusedxml を利用した XML パース（XML Bomb 等への対策）。
    - SSRF 対策: リダイレクト時のスキーム検証・プライベートホスト拒否を行うカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）、および事前のホストプライベートチェック。
    - URL スキームは http/https のみ許可。
    - レスポンス受信サイズを MAX_RESPONSE_BYTES（10MB）で制限し、gzip 解凍後のサイズチェックも実施（Gzip Bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事ID生成（正規化 URL の SHA-256 の先頭32文字）。
  - テキスト前処理（URL 除去、空白正規化）。
  - 銘柄抽出ロジック（4桁数字を候補に既知コードセットでフィルタ）およびニュースと銘柄の紐付け保存を実装。INSERT ... RETURNING を利用して実際に挿入された件数を正確に取得。
  - DB 保存はチャンクとトランザクションで効率化・安全化（_INSERT_CHUNK_SIZE、トランザクションロールバック処理）。
  - HTTP 操作用フック (_urlopen) を用意しテスト時にモックしやすく設計。
- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - DataSchema に基づくテーブル群を定義・初期化する init_schema を実装（Raw / Processed / Feature / Execution 層を含む多数のテーブル）。
  - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等。
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）と頻出クエリ向けインデックス群を定義。
  - get_connection（既存 DB への接続取得）を提供。
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新を行う ETL ヘルパー群とジョブを実装（run_prices_etl 等の個別 ETL を想定した設計）。
  - デフォルトのバックフィル日数、カレンダー先読みなど運用に配慮した仕様を採用（_DEFAULT_BACKFILL_DAYS = 3, _CALENDAR_LOOKAHEAD_DAYS = 90）。
  - ETL 実行結果を表す ETLResult dataclass を実装（品質問題・エラーの集約、辞書化サポート）。
  - テーブルの存在確認、最大日付取得ユーティリティを実装（差分計算に利用）。
  - 取引日調整ヘルパー（_adjust_to_trading_day）を用意。カレンダー未取得時のフォールバックを考慮。
- パッケージ空の __init__ を各サブパッケージに追加（execution, strategy, data）。

### Security
- ニュース収集での SSRF / XML攻撃 / Gzip Bomb / レスポンス巨大化対策を実装（defusedxml、リダイレクト検査、プライベートホスト検査、受信バイト上限、gzip 解凍後の再チェック）。
- .env パーサーでクォート内のバックスラッシュエスケープを考慮し、誤った解釈を防止。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- J-Quants クライアントは API レート制限（120 req/min）を厳守する設計。大量のページネーション取得でもスロットリングで抑制される。
- jquants_client の _request は 401 を受けた際に id_token を自動リフレッシュして再試行するが、無限再帰を避けるため refresh 呼び出し元では allow_refresh=False をサポート。
- DuckDB への保存は冪等性を担保するために ON CONFLICT を活用している（重複や更新を安全に処理）。
- NewsCollector は記事IDを URL 正規化 + SHA256（先頭32文字）で決定するため、トラッキングパラメータ差分による重複挿入を防ぐ。
- パッケージはテストフレンドリに設計されており、接続や HTTP オープン周りを外部から差し替え可能（例: _urlopen のモック）。

---

将来のリリースでは、strategy / execution / monitoring 層の戦略本体・発注実行ロジック・監視・品質チェックモジュール（quality 参照）が追加されることが想定されます。必要があればこの CHANGELOG を拡張してリリース履歴を追記してください。