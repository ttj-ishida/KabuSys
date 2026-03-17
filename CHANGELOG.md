# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルはパッケージの初期リリースに基づく推測による変更履歴です。

全般的な注意:
- バージョンはパッケージ内の __version__ に準拠しています（0.1.0）。
- 日付はこの CHANGELOG 作成時点（2026-03-17）を使用しています。

## [0.1.0] - 2026-03-17

### Added
- 初期リリース。以下の主要コンポーネントを追加。
  - パッケージ初期化
    - src/kabusys/__init__.py
      - パッケージ名 KabuSys、バージョン 0.1.0。
      - __all__ に data, strategy, execution, monitoring を公開。

  - 設定管理
    - src/kabusys/config.py
      - .env ファイルおよび環境変数から設定を自動読み込みする機能を追加。
      - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を読み込む（配布後の実行でも動作するよう設計）。
      - 読み込み優先度: OS環境変数 > .env.local > .env。
      - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
      - .env のパースは export プレフィックス、クォート、エスケープ、行内コメント等に対応。
      - Settings クラスで主要な設定をプロパティとして提供:
        - JQUANTS_REFRESH_TOKEN（必須）
        - KABU_API_PASSWORD（必須）
        - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
        - SLACK_BOT_TOKEN（必須）
        - SLACK_CHANNEL_ID（必須）
        - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
        - SQLITE_PATH（デフォルト: data/monitoring.db）
        - KABUSYS_ENV（検証: development/paper_trading/live）
        - LOG_LEVEL（検証: DEBUG/INFO/WARNING/ERROR/CRITICAL）
        - is_live / is_paper / is_dev ヘルパープロパティ

  - J-Quants API クライアント（データ取得・保存）
    - src/kabusys/data/jquants_client.py
      - 基本設計: レート制限順守、リトライ（指数バックオフ）、トークン自動リフレッシュ、取得時刻(fetched_at)の記録、DuckDB への冪等保存（ON CONFLICT DO UPDATE）。
      - レート制限: 120 req/min 固定間隔スロットリング実装 (_RateLimiter)。
      - HTTP リクエストラッパー _request:
        - 最大 3 回のリトライ、408/429/5xx に対応。
        - 401 受信時はリフレッシュして 1 回のみリトライ。
        - 429 の場合は Retry-After ヘッダを尊重（存在すれば待機時間として利用）。
      - モジュールレベルの ID トークンキャッシュと get_id_token(refresh_token)。
      - ページネーション対応の取得関数:
        - fetch_daily_quotes（株価日足）
        - fetch_financial_statements（財務データ）
        - fetch_market_calendar（JPX マーケットカレンダー）
      - DuckDB への保存関数（冪等化）:
        - save_daily_quotes -> raw_prices（ON CONFLICT (date, code) DO UPDATE）
        - save_financial_statements -> raw_financials（ON CONFLICT (code, report_date, period_type) DO UPDATE）
        - save_market_calendar -> market_calendar（ON CONFLICT (date) DO UPDATE）
      - 値変換ユーティリティ: _to_float, _to_int（入力の堅牢な変換ロジック）

  - ニュース収集モジュール
    - src/kabusys/data/news_collector.py
      - RSS フィードからニュースを収集し raw_news / news_symbols へ保存する機能を提供。
      - セキュリティ:
        - defusedxml を用いた XML パース（XML Bomb などへの対策）。
        - SSRF 対策: URL スキーム検証、プライベート/ループバック/IP 判定（_is_private_host）、リダイレクト前検査用ハンドラ (_SSRFBlockRedirectHandler)。
        - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzipped コンテンツの解凍後サイズ検査（Gzip bomb 対策）。
      - URL 正規化: トラッキングパラメータ（utm_ 等）除去、スキーム/ホスト小文字化、フラグメント削除、クエリキーソート。
      - 記事ID: 正規化 URL の SHA-256 の先頭 32 文字を使用して冪等性を確保。
      - テキスト前処理: URL 除去、空白正規化。
      - RSS 取得関数 fetch_rss（gzip 対応、XML パースエラーハンドリング、記事抽出）。
      - DB 保存:
        - save_raw_news: チャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDを返す。1 トランザクション内で処理。
        - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク・トランザクションで挿入し、実際に挿入された件数を返す。
      - 銘柄コード抽出: extract_stock_codes（4桁数字候補を known_codes と照合して抽出）。
      - run_news_collection: 複数 RSS ソースを順次処理し、各ソースで個別にエラーハンドリング（1 ソース失敗でも他を継続）。デフォルトソースに Yahoo Finance を設定。

  - DuckDB スキーマ定義と初期化
    - src/kabusys/data/schema.py
      - DataSchema.md に基づく 3 層（Raw / Processed / Feature）と実行レイヤーのテーブル定義を追加。
      - Raw テーブル: raw_prices, raw_financials, raw_news, raw_executions
      - Processed テーブル: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature テーブル: features, ai_scores
      - Execution テーブル: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
      - インデックス定義（頻出クエリ向け）。
      - init_schema(db_path) 関数でディレクトリ作成 → 全 DDL を実行して初期化（冪等）。
      - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わないことを明示）。

  - ETL パイプライン基礎
    - src/kabusys/data/pipeline.py
      - ETLResult データクラス（ETL 実行結果、品質問題リスト、エラーメッセージ等を保持）。
      - 差分更新ヘルパー: テーブルの最終取得日取得（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
      - 市場カレンダー補正: _adjust_to_trading_day（非営業日は直近営業日に調整）。
      - run_prices_etl: 株価差分 ETL の骨子（差分計算、backfill を考慮した再取得、jquants_client を用いた取得・保存）。設計上:
        - _MIN_DATA_DATE = 2017-01-01（初回ロード時の下限）
        - _CALENDAR_LOOKAHEAD_DAYS = 90（カレンダー先読み）
        - backfill_days デフォルト 3（日次で後出し修正を吸収）
        - 品質チェックは外部 quality モジュールを参照し、致命的な問題があっても ETL は継続する（呼び出し元で対応判断）
      - テスト容易性のため、id_token 注入可能などの設計。

### Security
- セキュリティ対策の明示的実装:
  - RSS/XML: defusedxml を使用して XML 攻撃を緩和。
  - SSRF 対策: スキーム検証、プライベート IP 判定、リダイレクト前検査、受信サイズ制限。
  - HTTP リクエスト時のタイムアウト設定や Retry-After 処理で DoS 等のリスク軽減を考慮。

### Notes / Usage
- .env 自動読み込みはプロジェクトルートの検出に依存（.git または pyproject.toml）。配布環境で root が見つからない場合は自動ロードをスキップ。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化可能。
- DuckDB スキーマ初期化は init_schema() を一度呼ぶことを推奨。既存テーブルは CREATE IF NOT EXISTS により破壊されない。
- news_collector._urlopen はテスト時にモックして差し替え可能（ネットワーキングの依存を排除）。
- jquants_client のレート制御はモジュールレベルで行われるため、複数スレッド/プロセスで同一インスタンスを共有する場合は注意が必要（現在は単一プロセス単一インスタンス想定）。

### Breaking Changes
- 初回リリースにつき該当なし。

### Fixed / Changed / Removed / Deprecated
- 初回リリースにつき該当なし。