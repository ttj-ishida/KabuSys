Keep a Changelog に準拠した CHANGELOG.md

すべての目立つ変更を記載します。このリリースは、提供されたコードベースから推測して作成した初回リリースの要約です。

Unreleased
---------
- なし（このスナップショットは初回リリース v0.1.0 に対応）

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期化
  - kabusys パッケージ初期版を追加。__version__ = "0.1.0" を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ に定義。

- 設定 / 環境変数管理 (kabusys.config)
  - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env と .env.local の読み込み順序を実装（OS 環境変数を保護する protected 機能あり）。
  - .env 行パーサを実装（export 形式、クォートやエスケープ、インラインコメントの扱いに対応）。
  - 環境変数取得のユーティリティ Settings クラスを実装。J-Quants、kabuAPI、Slack、DB パス、ログレベル、環境種別（development / paper_trading / live）等のプロパティを提供。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - バリデーション（KABUSYS_ENV, LOG_LEVEL）と必須変数チェック（_require）を実装。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 基本クライアントを実装（_BASE_URL, rate limiting, retry/backoff, JSON デコードエラーハンドリング）。
  - レート制限 (120 req/min) を固定間隔スロットリングで実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回、HTTP 408/429/5xx を対象）。429 の場合は Retry-After を優先。
  - 401 受信時の自動トークンリフレッシュ（1 回）を実装。ID トークンのモジュールレベルキャッシュを導入しページネーション間で共有。
  - get_id_token (リフレッシュトークン→IDトークン) を実装。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes（OHLCV）
    - fetch_financial_statements（四半期 BS/PL）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 型安全な数値変換ユーティリティ (_to_float, _to_int) を実装。
  - データ取得時に fetched_at を UTC で記録し、Look-ahead Bias 対策を意識した設計。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集と前処理を実装（defusedxml を利用して XML 攻撃防止）。
  - セキュリティ対策:
    - URL スキーム検証（http/https のみ許可）
    - SSRF 対策としてリダイレクト先のスキーム／ホストの事前検証（プライベートアドレス拒否）
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）
    - 受信サイズバイト数チェックと早期中止
  - URL 正規化とトラッキングパラメータ除去（_normalize_url, _make_article_id）。記事ID は正規化 URL の SHA-256 の先頭32文字。
  - テキスト前処理（URL除去、空白正規化）を実装（preprocess_text）。
  - RSS 解析（fetch_rss）で content:encoded 優先、pubDate のパースと UTC 正規化を行う。
  - DuckDB への保存ユーティリティ:
    - save_raw_news: トランザクション内でチャンクINSERT、ON CONFLICT DO NOTHING、INSERT ... RETURNING により新規挿入IDを返却。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンクで保存、RETURNING で実際の挿入数を返却。
  - 銘柄コード抽出ユーティリティ（4桁数字パターンに基づく extract_stock_codes）。
  - run_news_collection により複数 RSS ソースを順次収集し、エラーが発生しても他ソースは継続する設計。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataPlatform に基づく多層スキーマを定義（Raw / Processed / Feature / Execution）。
  - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等のテーブル DDL を実装。
  - 頻出クエリ用にインデックスを作成するDDLを用意。
  - init_schema(db_path) によりディレクトリ自動作成後、全DDLとインデックスを実行して DB を初期化する関数を提供。get_connection(db_path) により既存 DB へ接続可能。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETL の処理フローと設計方針に沿った実装を開始。
  - ETLResult dataclass を実装し、取得件数・保存件数・品質問題・エラー一覧などを保持。to_dict により品質問題を整形して出力可能。
  - 差分更新ユーティリティ:
    - _table_exists, _get_max_date を実装。
    - get_last_price_date, get_last_financial_date, get_last_calendar_date を公開。
    - _adjust_to_trading_day: 非営業日は直近の営業日に調整するヘルパーを実装。
  - run_prices_etl の雛形を実装（差分計算、backfill_days による再取得、fetch→save のフロー）。（注: 実装は本スナップショットで途中まで）

Changed
- 該当なし（初回リリース）

Fixed
- 該当なし（初回リリース）

Deprecated
- 該当なし

Removed
- 該当なし

Security
- RSS 処理と外部URLアクセスに関する複数の防御（defusedxml、SSRF 対策、応答サイズ制限、スキーム検証）を導入。

Notes / Known issues
- パッケージ構成に関する注意
  - __all__ に "monitoring" を含めているが、本スナップショットには monitoring サブパッケージの実装ファイルが含まれていません。実装が別途必要です。
  - strategy/execution パッケージはパッケージディレクトリが用意されていますが、現時点では具体的実装（モジュール）が含まれていません（プレースホルダ）。
- 依存ファイル/モジュール
  - pipeline モジュールは quality モジュール（kabusys.data.quality）を参照しているが、本スナップショット内に quality モジュールの実装が見当たりません。品質チェック機能を利用するには quality モジュールの追加実装が必要です。
- 実装未完 / 破壊的な不備の可能性
  - kabusys.data.pipeline.run_prices_etl は本スナップショットで末尾が途中となっており、戻り値のタプルなどが未完の状態に見えます。実行前に実装を完成させる必要があります。
- テストと例
  - ネットワーク操作・DB 操作が多数含まれるため、ユニットテスト時は環境変数（KABUSYS_DISABLE_AUTO_ENV_LOAD など）の設定や外部 API のモック化（_urlopen, jq.get_id_token 等）を推奨します。

参考
- バージョンはパッケージ定義の __version__ を使用: 0.1.0

-- End of CHANGELOG.md --