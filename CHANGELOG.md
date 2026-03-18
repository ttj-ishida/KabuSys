# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、本リリースはパッケージバージョン 0.1.0（src/kabusys/__init__.py の __version__）に対応します。

## [Unreleased]

## [0.1.0] - 2026-03-18
最初の公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。モジュール分割は data, strategy, execution, monitoring を想定（src/kabusys/__init__.py）。
  - バージョン: 0.1.0 を設定。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出: __file__ 起点で親ディレクトリを探索し .git または pyproject.toml を根拠に検出。
  - 自動 .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用）。
  - .env パーサを実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理（クォートあり/なしのルール差異）。
  - 必須 env 取得時に未設定だと ValueError を送出する _require を提供。
  - Settings に J-Quants / kabu / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等のプロパティを実装。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API ベース実装を追加。取得対象:
    - 株価日足（OHLCV）
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter を実装。
  - 再試行ロジック:
    - 指数バックオフ、最大 3 回のリトライ（対象ステータス 408, 429, 5xx）。
    - 429 時は Retry-After ヘッダを優先。
    - ネットワークエラー（URLError/OSError）に対する再試行。
  - 認証トークン処理:
    - refresh token から id_token を取得する get_id_token。
    - 401 受信時に自動で id_token を1回リフレッシュして再試行（無限再帰防止）。
    - モジュールレベルの id_token キャッシュを持ち、ページネーション間で共有。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - pagination_key によるページ取得ループ、重複検出を実装。
  - DuckDB への冪等な保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes: raw_prices への保存。fetched_at は UTC ISO8601（Z）で記録。
    - save_financial_statements: raw_financials への保存。
    - save_market_calendar: market_calendar への保存。HolidayDivision の意味を反映してフラグを設定。
  - JSON デコード失敗時のエラー処理、ログ出力。
  - ユーティリティ: _to_float / _to_int（空値や不正値の扱い、"1.0" などの float 文字列処理を含む）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news / news_symbols に保存する一連処理を実装。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加（DEFAULT_RSS_SOURCES）。
  - セキュリティ・堅牢性:
    - defusedxml を利用した XML パース（XML Bomb 等の防御）。
    - SSRF 防止: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカルかを判定して拒否。
    - リダイレクト時にスキームとリダイレクト先のホストを事前検査する _SSRFBlockRedirectHandler。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）によるメモリ DoS 対策。gzip 圧縮レスポンスの解凍後再チェック。
    - URL 正規化でトラッキングパラメータ（utm_* 等）を除去。
  - 記事 ID の生成:
    - 正規化済み URL の SHA-256 ハッシュ先頭32文字を記事 ID として使用し冪等性を担保。
  - テキスト前処理関数 preprocess_text（URL 除去・空白正規化）。
  - fetch_rss: XML の <channel>/<item> にフォールバックしつつ記事を抽出。content:encoded を優先。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING を使い、実際に挿入された記事 ID のリストを返す。チャンク分割と単一トランザクションで実行、失敗時はロールバック。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けをチャンク化して INSERT ... RETURNING により挿入件数を算出。重複排除を行う。
  - 銘柄コード抽出:
    - 4桁数字パターンから既知の銘柄コードセットに基づいて抽出する extract_stock_codes を実装。
  - 統合収集ジョブ run_news_collection を実装。各ソースは独立してエラーハンドリングし、既存記事の重複はスキップ。既知コードが与えられれば新規挿入記事に対して銘柄紐付けを行う。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく多層スキーマを実装（Raw / Processed / Feature / Execution 層）。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）を付与。
  - インデックス定義（頻出クエリを想定したインデックス群）。
  - init_schema(db_path) を実装:
    - 指定パスの親ディレクトリ自動作成（:memory: を除く）。
    - 全テーブルとインデックスを冪等に作成。
    - 初回は init_schema を使い、以降は get_connection で接続を得ることを想定。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計方針と差分更新ロジックを実装（DataPlatform.md に準拠）。
  - ETLResult データクラスを追加（取得数・保存数・品質問題・エラー一覧を保持、辞書化メソッド付き）。
  - 差分更新ヘルパー:
    - _table_exists, _get_max_date による最終取得日の判定。
    - get_last_price_date, get_last_financial_date, get_last_calendar_date を提供。
  - 市場カレンダー補助: 非営業日の場合に直近営業日に調整する _adjust_to_trading_day を実装（最大30日遡り）。
  - run_prices_etl を実装（差分取得、backfill_days による後出し修正吸収、jq.fetch + jq.save を使用）。注: デフォルトバックフィルは 3 日。
  - 定数:
    - データ開始日 (_MIN_DATA_DATE = 2017-01-01)
    - カレンダー先読み日数、バックフィル日数等を定義。

### Security
- ニュース収集での SSRF 対策と XML パースの安全化（_SSRFBlockRedirectHandler, _is_private_host, defusedxml）。
- ネットワーク関連の堅牢な再試行・バックオフ（J-Quants クライアント）により一時的な障害に耐性を強化。
- .env 読み込み時に OS 環境変数を保護する protected 引数の実装（.env.local が OS 環境を上書きしないよう配慮）。

### Notes / Migration
- DuckDB スキーマは init_schema() で初期化する必要がある（get_connection() はスキーマ初期化を行わない）。
- .env の自動読み込みはデフォルトで有効。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants の認証に JQUANTS_REFRESH_TOKEN 環境変数が必須。
- Slack 通知等を使う場合、SLACK_BOT_TOKEN / SLACK_CHANNEL_ID が必須。
- save_* 系関数は冪等（ON CONFLICT）設計で、重複挿入を更新で吸収します。

### Fixed
- 初回リリースのため該当なし。

### Changed / Removed / Deprecated
- 初回リリースのため該当なし。

---

（補足）この CHANGELOG は現行コードベースから推測して作成しています。実際のリリースノートへ転記する際は、実行時の挙動やドキュメントに合わせて日付・細部を調整してください。