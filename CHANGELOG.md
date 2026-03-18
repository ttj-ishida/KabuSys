CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。
リリース日はコードベースの現時点（この CHANGELOG 作成日）を使用しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-18
--------------------

Added
- 初回公開: KabuSys 日本株自動売買システムの基礎実装を追加。
- パッケージ構成:
  - kabusys パッケージのエントリポイントを追加（__version__ = 0.1.0）。
  - サブパッケージ: data, strategy, execution, monitoring（骨格を用意）。
- 環境設定:
  - kabusys.config.Settings クラスを追加。環境変数から設定を安全に取得する API を提供。
  - .env ファイルの自動読み込み（プロジェクトルートの .git または pyproject.toml を基準）を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - 必須環境変数チェック用ヘルパ（_require）を追加。
  - サポートする主な環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトあり）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
- J-Quants クライアント:
  - kabusys.data.jquants_client モジュールを実装。
  - 機能:
    - 株価日足（fetch_daily_quotes / save_daily_quotes）
    - 財務データ（fetch_financial_statements / save_financial_statements）
    - マーケットカレンダー（fetch_market_calendar / save_market_calendar）
    - 認証トークン取得（get_id_token）とモジュールレベルのトークンキャッシュ
  - API 呼び出しの堅牢化:
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - 再試行（最大3回、指数バックオフ）と 408/429/5xx のリトライ処理。
    - 401 応答時はトークン自動リフレッシュを 1 回試行。
    - レスポンスの JSON デコード失敗時に分かりやすい例外を投げる。
  - DuckDB への保存は冪等性を考慮（INSERT ... ON CONFLICT DO UPDATE）して上書き/更新を行う。
  - データ取得時に fetched_at を UTC で付与し、Look-ahead Bias 防止のための取得時点を記録。
- ニュース収集:
  - kabusys.data.news_collector を追加。
  - 機能:
    - RSS フィードからのニュース収集（fetch_rss）と raw_news への保存（save_raw_news）。
    - 記事IDは正規化 URL を SHA-256（先頭32文字）で生成して冪等性を担保。
    - 前処理（URL 除去・空白正規化）や pubDate のパース、title/content の優先扱い（content:encoded を優先）。
    - 銘柄コード抽出（extract_stock_codes）と news_symbols への紐付け保存（_save_news_symbols_bulk, save_news_symbols）。
  - セキュリティ・堅牢化:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクト先のスキームおよびプライベート IP 検査（_SSRFBlockRedirectHandler, _is_private_host）。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）を超える場合はスキップ。gzip 解凍後も検査。
    - トラッキングパラメータ（utm_* 等）を除去して URL 正規化。
    - INSERT ... RETURNING などで実際に挿入された件数を正確に返す実装。
- データスキーマ（DuckDB）:
  - kabusys.data.schema に DuckDB のスキーマ定義と初期化ロジックを追加。
  - レイヤ構成（Raw / Processed / Feature / Execution）に従い多数のテーブル定義を導入（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）とインデックスを定義。
  - init_schema(db_path) でディレクトリ自動作成およびテーブル作成を行う（冪等）。
  - get_connection(db_path) を用意（スキーマ初期化は行わない）。
- ETL パイプライン:
  - kabusys.data.pipeline モジュールを追加（ETL の骨組み）。
  - 機能・方針:
    - 差分更新ロジック（DB の最終取得日から不足分のみ取得）。
    - backfill による遡り取得（デフォルト backfill_days=3）で API の後出し修正に対応。
    - 市場カレンダー先読み（_CALENDAR_LOOKAHEAD_DAYS=90）。
    - 品質チェックモジュールへのフック（quality モジュールを参照する設計）。
    - ETL 結果をまとめる ETLResult dataclass（品質問題・エラーの集約、シリアライズ用 to_dict）。
    - 汎用ユーティリティ: テーブル存在チェック、最大日付取得、営業日調整など。
  - run_prices_etl 実装（差分取得 -> 保存 -> 結果返却の流れ、date_from の自動算出）。
- テスト容易性:
  - news_collector._urlopen を差し替え可能にする等、テストでモックしやすい設計を意識。

Changed
- 該当なし（初回リリース）

Fixed
- 該当なし（初回リリース）

Security
- XML パースは defusedxml を使用し、RSS ベースの XML 攻撃に対する防御を実装。
- RSS フェッチ時の SSRF 対策を複数レイヤで導入（事前ホスト検査、リダイレクト時検査、プライベート IP 判定）。
- .env 読み込みで既存 OS 環境変数を保護する仕組みを導入（protected set）。

Deprecated
- 該当なし

Removed
- 該当なし

Notes / Known issues
- run_prices_etl の末尾が断片的に見える箇所があり（提供コードの末尾が途中で終わっているため）、
  実際の戻り値とログ処理の最終整形については本稿作成時点で不完全に見えます。リポジトリの完全版ではこの関数が (fetched_count, saved_count) を正しく返すことを期待します。
- Quality チェック本体（kabusys.data.quality）は presentational に参照されていますが、このスニペットには含まれていません。品質チェックのルール・重大度定義は別途実装済み／実装予定です。
- strategy, execution, monitoring サブパッケージは骨格のみ（__init__.py が空）で、各種戦略や発注ロジックは別実装が必要です。

作者注
- 本 CHANGELOG はコードの現状（提供されたソース）から推測して作成しました。実際のコミット履歴・リリースノートが存在する場合はそちらを優先してください。