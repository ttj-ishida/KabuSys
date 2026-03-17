CHANGELOG
=========
すべての変更は Keep a Changelog の形式に準拠しています。  
初期リリース (v0.1.0) を含む、コードベースから推測される機能追加・設計上の注記・既知の問題を日本語でまとめています。

フォーマットの注記
-----------------
- 各エントリはコードベース（src/kabusys 以下の実装）から推測して記載しています。
- 日付は本ファイル生成時点（2026-03-17）を使用しています。

Unreleased
----------
- なし

0.1.0 - 2026-03-17
------------------
Added
- パッケージ初期化
  - kabusys パッケージの公開バージョンを 0.1.0 として追加。
  - __all__ に data, strategy, execution, monitoring を定義。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト向け）。
  - .env 行パーサを実装（export プレフィックス対応、クォート内エスケープ、インラインコメント処理）。
  - 必須環境変数取得ヘルパー _require を提供。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level, is_live 等）を環境変数から取得・検証。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装（_request）。
    - 固定間隔の RateLimiter によるレート制御（120 req/min）。
    - 冪等なページネーション対応。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx などを再試行）。
    - 401 受信時はトークン自動リフレッシュを 1 回行って再試行。
    - JSON デコード失敗時の明示的エラー報告。
  - get_id_token: リフレッシュトークンから idToken を取得（POST）。呼び出し時の無限再帰を防止。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等設計: ON CONFLICT DO UPDATE）
    - save_daily_quotes（raw_prices に保存）
    - save_financial_statements（raw_financials に保存）
    - save_market_calendar（market_calendar に保存）
  - 型変換ユーティリティ (_to_float/_to_int) を実装（空値や不正値に対する安全な扱い）。
  - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集と前処理の実装。
  - セキュリティ・堅牢性対策:
    - defusedxml による XML パース（XML Bomb 対策）。
    - HTTP リダイレクト時の SSRF 検査（スキーム検証 + プライベートホスト拒否）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）および Gzip 解凍後のサイズチェック。
    - URL スキーム検証（http/https のみ許可）。
    - トラッキングパラメータ（utm_* 等）を除去する URL 正規化。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
  - フィード処理:
    - fetch_rss: RSS 取得 → XML パース → 記事抽出（content:encoded 優先、description 代替）。
    - preprocess_text: URL 除去・空白正規化。
    - _parse_rss_datetime: pubDate を UTC naive datetime に正規化。
  - DuckDB への保存:
    - save_raw_news: INSERT ... RETURNING を用いて新規挿入記事 ID のリストを返す（チャンク & 単一トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等に保存（ON CONFLICT DO NOTHING、挿入数を正確に返す）。
  - 銘柄コード抽出:
    - extract_stock_codes: テキストから 4 桁銘柄コードを抽出し、既知のコードセットでフィルタリング。

- DuckDB スキーマ・初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層に対応するテーブル DDL を定義。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックスを想定した CREATE INDEX 文を定義（クエリパターンに基づく）。
  - init_schema(db_path) によりディレクトリ作成（必要時）→ 全テーブル・インデックス作成（冪等）。
  - get_connection(db_path) で既存 DB への接続を提供（スキーマ初期化は行わない旨の注記）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass により ETL 実行結果を構造化（品質問題やエラーの一覧を保持）。
  - スキーマ存在チェックや最大日付取得のユーティリティ（_table_exists, _get_max_date）。
  - 市場カレンダーを考慮した営業日調整ヘルパー (_adjust_to_trading_day)。
  - 差分更新サポート: DB の最終取得日からの差分再取得ロジックを採用（backfill_days により後出し修正を吸収）。
  - run_prices_etl: 株価日足の差分 ETL 実装（fetch → save の流れ）。デフォルトバックフィル 3 日、最小取得開始日は 2017-01-01。
  - 品質チェック（quality モジュール）との連携を想定（結果に quality_issues を含む設計）。

Security
- SSRF 対策、defusedxml の採用、URL スキーム制限、プライベート IP チェック、レスポンスサイズ制限など、外部入力の扱いに関するセキュリティ強化が多数導入されています。

Performance / Reliability
- API レート制御（_RateLimiter）によりレート制限を厳守。
- リトライ & 指数バックオフ、Retry-After ヘッダ尊重（429 時）により堅牢性を向上。
- トークンキャッシュ / ページネーションの共有トークンで効率化。
- DuckDB 側はバルク挿入（チャンク処理）・トランザクション利用・ON CONFLICT戦略により冪等性と性能を確保。

Notes / Usage
- 必須環境変数の例:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB 初期化: kabusys.data.schema.init_schema("data/kabusys.duckdb")
- 自動 .env 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

Known issues / TODO
- run_prices_etl の戻り値に不整合の可能性:
  - 現在の実装末尾に "return len(records), " のようにカンマで終わる行が存在しており、意図した (fetched_count, saved_count) のタプルが返らない可能性があります。呼び出し側での利用に注意が必要です（修正: saved 変数を含めた正しいタプルを返す必要あり）。
- 一部のモジュール（strategy, execution, monitoring）の __init__ は空であり、実装がこれから想定される点に留意してください。
- quality モジュールは参照されているが、このコードベースには含まれていないため、品質チェックの具体的実装は別途追加が必要です。

Breaking Changes
- 初期リリースのため該当なし。

Deprecated
- なし。

Removed
- なし。

Acknowledgements / References
- 設計意図として Keep a Changelog と DataPlatform.md / DataSchema.md のセクション参照をコメントに残した形跡があるため、ドキュメントに基づいた実装であることが分かります。

（以上）