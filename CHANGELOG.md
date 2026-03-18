# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-18

Added
- パッケージ初期リリースとして kabusys コードベースを追加。
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml 基準）。  
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは export プレフィックス、クォート文字列、インラインコメント、エスケープシーケンス等に対応。
  - 必須変数取得時は _require() で明示的にエラーを発生させる（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN）。
  - 環境変数値の検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、四半期財務データ、マーケットカレンダーの取得機能を実装（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - 再試行ロジック: 指数バックオフ、最大 3 回、対象ステータス (408, 429, 5xx)。
  - 401 Unauthorized を検出した場合はリフレッシュ（get_id_token を使ったトークン再取得）して 1 回だけリトライする仕組みを導入。
  - ページネーション対応（pagination_key を利用）およびモジュールレベルの ID トークンキャッシュを実装。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等（ON CONFLICT DO UPDATE）で fetched_at を UTC で記録。
  - 型変換ユーティリティ (_to_float / _to_int) を追加し不正値を安全に扱う。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS から記事を収集し raw_news に保存する完全なパイプラインを実装。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url / _make_article_id）。記事IDは正規化URLの SHA-256 の先頭32文字。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の対策）。
    - SSRF 対策: スキーム検証（http/https のみ）、ホストがプライベート/ループバックでないことを確認する関数 _is_private_host、リダイレクト時の検査を行うカスタム HTTPRedirectHandler。
    - レスポンス最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ再検査。
  - テキスト前処理 (preprocess_text): URL 除去、空白正規化。
  - DuckDB への保存はトランザクションでまとめ、INSERT ... RETURNING を用いて実際に挿入された ID を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 銘柄コード抽出 (extract_stock_codes): 4桁数字を既知銘柄セットでフィルタして抽出。
  - run_news_collection: 複数 RSS ソースの収集をオーケストレーションし、各ソースは独立してエラーハンドリング。
  - テスト容易性: _urlopen を差し替え可能（モック対応）。
- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution レイヤーのテーブル DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等を含む。
  - インデックスを作成して一般的なクエリパターンのパフォーマンスを改善。
  - init_schema(db_path) によりディレクトリ作成 → 接続 → テーブルとインデックス作成を行う（冪等）。
  - get_connection(db_path) で既存 DB へ接続可能（初期化は行わない）。
- ETL パイプライン骨格 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass により ETL の集計結果と品質問題・エラーを構造化して返す設計。
  - 差分更新ヘルパー: テーブル存在確認、最大日付取得、営業日調整ロジック(_adjust_to_trading_day) を実装。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date を公開。
  - run_prices_etl: 差分更新とバックフィル（デフォルト backfill_days=3）を実装。J-Quants から差分取得して保存する流れを実装。

Security
- RSS パーサーに defusedxml を利用して XML 攻撃を軽減。
- URL/リダイレクトのスキーム・ホスト検証により SSRF を防止。
- HTTP レスポンスサイズの上限設定と gzip 解凍後のチェックでメモリ DoS（Gzip bomb）への対策を実装。
- J-Quants クライアントは認証トークンの自動リフレッシュ機能を安全に実装（無限再帰対策あり）。

Notes / Developer Tips
- 自動 .env ロードはパッケージ内からプロジェクトルートを探索して実行するため、配布後でも CWD に依存しない動作を意図しています。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化してください。
- J-Quants のページネーション／複数 API 呼び出しで同一 ID トークンを共有するためのモジュールレベルキャッシュ (_ID_TOKEN_CACHE) を用意しています。テストでは get_id_token をモックするか、_get_cached_token(force_refresh=True) を利用してください。
- news_collector._urlopen はテスト時に簡単に差し替え可能（SSRF チェックを通した上でのモックが推奨）。

Known Issues
- run_prices_etl の戻り値が関数シグネチャ（tuple[int, int]）と一致していません。実装末尾にある "return len(records)," のように単一要素のタプルしか返しておらず（おそらく saved 値を返すべき）、呼び出し元での扱いに注意が必要です（修正が必要）。
- その他エッジケースは十分な実稼働テストを推奨（例: 非標準フォーマットの RSS、特殊な HTTP ヘッダや Retry-After の異常値等）。

Migration / Upgrade Notes
- 初回は必ず init_schema(settings.duckdb_path) を実行してデータベースとテーブルを初期化してください（":memory:" 指定でインメモリ DB を作成可能）。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - （必要に応じて）KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_DISABLE_AUTO_ENV_LOAD
- DB スキーマを手動で変更する場合は、外部キーやインデックスの依存関係に注意してください。

Unreleased / TODO
- run_prices_etl の戻り値修正（saved 値を含めて正しいタプルを返す）。
- 単体テストおよび統合テストの追加（特にネットワークエラー・リダイレクト・大型レスポンス・XML の異常系）。
- ETL の品質チェックモジュール (quality) の実装完了および ETL からの利用強化。
- 実行層（execution）・戦略層（strategy）の具体的実装拡充（現状はパッケージ構造のみ）。

-- end --