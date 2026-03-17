CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。本ファイルは「Keep a Changelog」形式に準拠しています。

0.1.0 - 2026-03-17
-----------------

Added
- パッケージ初期リリース (kabusys)
  - パッケージバージョン: 0.1.0

- 基本パッケージ構成
  - モジュール群: data, strategy, execution, monitoring を公開。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを追加。
    - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - プロジェクトルート判定ロジック: .git または pyproject.toml を基準に探索。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - コメント処理（quoted / unquoted の違いを考慮）。
  - Settings クラスを提供（プロパティ経由で必須/任意設定を取得）。
    - J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル の取得。
    - env / log_level の妥当性検証 (有効な値セットを定義)。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装:
    - ベースURL、レート制限 (120 req/min) を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）。対象ステータス: 408, 429, 5xx。
    - 401 時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止のため allow_refresh フラグ）。
    - ページネーション対応（pagination_key の追跡）。
    - JSON デコード失敗時の明示的なエラー化。
  - 認証ヘルパー:
    - get_id_token(refresh_token: Optional) を実装（POST /token/auth_refresh）。
    - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有可能、force_refresh オプション）。
  - データ取得 API:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供（ページネーション対応）。
    - 各取得関数は取得件数ログ出力を行う。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - 冪等性を保証するため ON CONFLICT DO UPDATE を使用。
    - fetched_at を UTC ISO8601 形式で記録し、Look-ahead バイアスのトレースを可能に。
    - PK 欠損レコードのスキップと警告ログ出力。
  - 型変換ユーティリティ:
    - _to_float / _to_int を実装（安全な変換、空値/不正値は None）。
    - _to_int は "1.0" のような文字列を float 経由で処理し、小数部がある場合は None を返すことで意図しない切り捨てを防止。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集機能を実装:
    - fetch_rss により RSS を取得し NewsArticle 型リストを返す。
    - defusedxml を用いた XML パース（XML Bomb 等の攻撃対策）。
    - gzip 圧縮対応と解凍後サイズチェック（Gzip bomb 対策）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入しメモリDoS対策。
    - HTTP/HTTPS のみ許可し、それ以外のスキームを拒否（SSRF 対策）。
    - リダイレクト時にスキームとホストを事前検証するカスタムハンドラを実装（_SSRFBlockRedirectHandler）。
    - ホストがプライベートアドレスか検査するロジックを実装（_is_private_host）。DNS 解決を行い A/AAAA を確認。
    - URL 正規化処理（クエリのトラッキングパラメータ除去、ソート、フラグメント削除、小文字化）。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - テキスト前処理：URL 除去、空白正規化。
    - RSS pubDate の安全なパース（タイムゾーンを考慮し UTC に正規化、パース失敗時は現在時刻で代替）。
  - DuckDB への保存:
    - save_raw_news: チャンク分割して一括 INSERT（_INSERT_CHUNK_SIZE）、トランザクションでまとめる。
      - INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、新規挿入された記事IDリストを返す。
      - トランザクション失敗時はロールバックして例外を再送出。
    - save_news_symbols / _save_news_symbols_bulk:
      - (news_id, code) ペアの紐付けをチャンク単位で一括保存。ON CONFLICT で重複を排除し、実際に挿入された件数を RETURNING で正確に取得。
      - 複数記事分を扱う内部関数は重複除去して順序を保つ実装。
  - 銘柄コード抽出:
    - extract_stock_codes(text, known_codes) を提供。4桁数字パターンを候補として抽出後、known_codes にあるものだけを返す（重複排除）。

- DuckDB スキーマ定義 / 初期化 (kabusys.data.schema)
  - DataSchema.md に準拠したスキーマを実装（3 層 + 実行層の構造を想定）。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - テーブル定義には制約（PRIMARY KEY / CHECK / FOREIGN KEY）を適切に設定。
  - 頻出クエリを想定したインデックス群を追加。
  - init_schema(db_path) を提供:
    - DuckDB ファイルの親ディレクトリ自動作成、全テーブル・インデックスの作成 (冪等)。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL 用ユーティリティとジョブを実装（差分更新・バックフィル対応）。
    - ETLResult dataclass を追加（対象日/取得件数/保存件数/品質問題/エラーの集約、シリアライズ用 to_dict を提供）。
    - 差分取得のヘルパー: get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - 市場カレンダー参照の補正ヘルパー: _adjust_to_trading_day（非営業日を直近の営業日に調整）。
    - run_prices_etl を実装（差分取得、backfill_days による再取得、J-Quants クライアント経由で取得・保存）。
    - ETL の設計方針として、品質チェックは全件収集し呼び出し元で対応を決定する（Fail-Fast しない）。
  - デフォルト設定:
    - J-Quants データ最古日: 2017-01-01
    - カレンダー先読み: 90 日
    - デフォルトバックフィル: 3 日

Security
- SSRF 対策を強化:
  - news_collector の RSS フェッチでスキーマ検証、リダイレクト先のスキーム/ホスト検査、プライベートアドレス判定を導入。
  - defusedxml を利用して XML 関連の脆弱性を軽減。
- .env 読み込みでも OS 環境変数を保護する仕組み（protected set）を導入。

Performance
- J-Quants API クライアントに固定間隔レートリミッタを導入して レート制限 (120 req/min) を守る。
- news_collector の DB 保存はチャンク挿入・トランザクションでまとめ、INSERT RETURNING を活用してオーバーヘッドを低減。

Notes / Implementation details
- DuckDB を利用（依存: duckdb）。
- RSS の既定ソースに Yahoo Finance のカテゴリ RSS を設定。
- 一部 I/O やネットワーク処理はテスト時にモック可能な設計（例: _urlopen の差し替え）。
- ロギングを随所に追加し、実行状況・警告・失敗の原因を出力する。
- いくつかの関数は外部仕様（DB テーブル名、カラム名、環境変数名）に依存するため、導入時は .env を準備し settings で必須値を設定すること。

Deprecated
- なし。

Removed
- なし。

Fixed
- なし。

以上。必要であれば各機能の利用例や .env.example の想定内容、テーブルスキーマの抜粋などを追記できます。どの部分の細かい説明が必要か教えてください。