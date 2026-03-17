# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

※パッケージバージョン: 0.1.0（src/kabusys/__init__.py の __version__ に準拠）

## [0.1.0] - 2026-03-17

Added
- 初版リリース。日本株自動売買基盤 KabuSys のコアモジュール群を追加。
  - パッケージ骨格: kabusys、サブパッケージ data, strategy, execution, monitoring（__all__ で公開）。
- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env のパース実装（コメント行、export プレフィックス、クォート・エスケープ、インラインコメント処理を考慮）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - settings オブジェクトによる環境変数取得と必須検証（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
  - 環境名 (KABUSYS_ENV) とログレベル (LOG_LEVEL) の値検証および is_live / is_paper / is_dev ヘルパー。
  - パス設定（DuckDB / SQLite）の Path 型返却。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 株価日足、財務（四半期）データ、マーケットカレンダー取得の実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装 (_RateLimiter)。
  - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダ優先。
  - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動リフレッシュして 1 回リトライ（無限再帰回避のため allow_refresh 管理）。
  - モジュールレベルの id_token キャッシュ（ページネーション間で共有）。
  - 取得データに fetched_at を UTC で付与して「いつ知得したか」を追跡（Look-ahead Bias 対策）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）：
    - ON CONFLICT を使った冪等保存（重複時は更新）。
    - PK 欠損行のスキップとログ出力。
  - 型安全な数値変換ユーティリティ（_to_float / _to_int、"1.0" 等の扱いを明示）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得と raw_news への保存、news_symbols での銘柄紐付けを実装。
  - defusedxml を使った XML パース（XML Bomb 対策）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト時のスキーム・ホスト検証ハンドラ（_SSRFBlockRedirectHandler）。
    - ホスト名を DNS で解決し、プライベート/ループバック/リンクローカル/マルチキャストの検出。
  - レスポンスサイズ制限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後の再検査（Gzip bomb 対策）。
  - 記事IDは URL 正規化後の SHA-256（先頭32文字）で生成し、トラッキングパラメータ（utm_ など）を除去して冪等性を担保。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB への保存はチャンク化・トランザクションでまとめて実行し、INSERT ... RETURNING を用いて実際に挿入された件数を返却。
  - 銘柄コード抽出ロジック（本文/タイトルから4桁の数値を抽出し、既知のコードセットでフィルタ）。
  - run_news_collection により複数ソースの独立処理（1ソース失敗でも継続）と新規保存数の集計。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataSchema.md に基づくスキーマを実装（Raw / Processed / Feature / Execution 層）。
  - テーブル群（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 制約（PRIMARY KEY / CHECK / FOREIGN KEY）とインデックス定義（頻出クエリに対するインデックス）。
  - init_schema(db_path) による初期化 API（親ディレクトリ自動作成、":memory:" サポート）。
  - get_connection(db_path) による既存 DB 接続取得（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新（DB の最終取得日から backfill_days 前を再取得して後出し修正を吸収）をサポート。
  - 市場カレンダーの先読み（lookahead）や最小データ日付（_MIN_DATA_DATE）に基づく初回ロード対応。
  - ETL 実行結果を表す ETLResult データクラス（品質問題・エラーの集約、to_dict）。
  - テーブル存在チェック、最大日付取得ユーティリティ、営業日調整ヘルパー（_adjust_to_trading_day）を実装。
  - run_prices_etl の骨組み（取得→保存→ログ記録）を実装（差分ロジックと backfill の考慮、取得/保存件数を返却）。

Security
- 外部データ取得に関するセキュリティ対策を多数実装:
  - defusedxml による XML パース安全化。
  - SSRF 対策（スキーム検証・ホストのプライベート判定・リダイレクト時検査）。
  - レスポンスサイズ制限と gzip 解凍後サイズ再検査（DoS対策）。
  - .env ロード時の OS 環境変数保護（protected セット）と警告ログ。

Notes
- 本バージョンは基盤実装（API クライアント、ニュース収集、スキーマ、ETL の基礎）に重点を置いた初版です。実運用でのパラメータ調整（タイムアウト、バックフィル日数、RSS ソースの追加など）や、strategy/execution/monitoring の具体実装は今後のバージョンで追加予定です。
- 実行時は必須環境変数（JQUANTS_REFRESH_TOKEN 等）を設定してください。.env.example を参考に .env を作成できます。

Unreleased
- 現時点で未リリースの変更はありません。

--- 

（この CHANGELOG はソースコードの実装から推測して作成しています。実際の変更履歴やリリースノートとして利用する場合は、必要に応じて調整してください。）