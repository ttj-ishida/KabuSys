# Changelog

すべての変更は Keep a Changelog の規約に従って記載しています。  
このプロジェクトはセマンティックバージョニングに従います。  

現在のバージョン: 0.1.0 - 初期リリース

## [0.1.0] - 2026-03-18
初回リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージルートを定義（kabusys/__init__.py）。バージョン情報 __version__ = 0.1.0 を追加。
  - モジュール公開: data, strategy, execution, monitoring を __all__ に登録。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を探索）。
  - .env / .env.local の自動ロード機能を実装（OS 環境変数優先、.env.local は上書き）。自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは export プレフィックス、シングル／ダブルクォート、インラインコメントをサポート。
  - 必須環境変数チェック用の _require() を提供。
  - 設定プロパティ（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV、LOG_LEVEL）を用意。KABUSYS_ENV/LOG_LEVEL の値検証あり。
  - settings = Settings() を公開。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants API からのデータ取得機能を実装：
    - get_id_token(refresh_token=None)：リフレッシュトークンから id_token を取得（POST）。
    - fetch_daily_quotes(...)=株価日足のページネーション取得対応。
    - fetch_financial_statements(...)=財務データのページネーション取得対応。
    - fetch_market_calendar(...)=マーケットカレンダー取得。
  - レート制御（120 req/min 固定間隔スロットリング）を実装（内部 _RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回）。HTTP 408/429 および 5xx をリトライ対象に設定。429 の場合は Retry-After を優先。
  - 401 受信時の自動トークンリフレッシュ（1回のみ）と再試行を実装。モジュールレベルで id_token キャッシュを保持（ページネーション間で共有）。
  - DuckDB へ保存する冪等的な保存関数を実装：
    - save_daily_quotes(conn, records)：raw_prices テーブルに ON CONFLICT DO UPDATE を用いて保存。
    - save_financial_statements(conn, records)：raw_financials テーブルに冪等保存。
    - save_market_calendar(conn, records)：market_calendar テーブルに冪等保存。
  - データ型変換ユーティリティ (_to_float / _to_int) を実装し、妥当でない値を None に変換するロジックを含む。
  - 取得時刻（fetched_at）を UTC ISO8601 形式で記録し、Look-ahead Bias を防止する方針を採用。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからのニュース収集パイプラインを実装：
    - fetch_rss(url, source, timeout)：RSS の XML 取得・パース・記事整形（title, content, pubDate の正規化）を行う。
    - save_raw_news(conn, articles)：raw_news テーブルへ一括（チャンク）挿入、INSERT ... RETURNING を使用し新規挿入IDを返却。
    - save_news_symbols(conn, news_id, codes)：news_symbols テーブルへ記事と銘柄コードの紐付けを保存（RETURNING を使用）。
    - _save_news_symbols_bulk(conn, pairs)：複数記事の紐付けをチャンクで一括保存。
    - extract_stock_codes(text, known_codes)：記事本文から4桁の銘柄コードを抽出（重複除去、known_codes フィルタ）。
    - run_news_collection(conn, sources=None, known_codes=None, timeout=30)：既定の RSS ソース群から収集し DB に保存、各ソースを独立してエラーハンドリング。
  - セキュリティ／堅牢性設計:
    - defusedxml を利用して XML Bomb 等の攻撃を軽減。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否、リダイレクト時にも検証するカスタム RedirectHandler を実装。
    - 最大受信バイト数（DEFAULT: 10MB）でレスポンスを制限しメモリ DoS を軽減。gzip の解凍後もサイズチェックを行う。
    - 記事IDは URL 正規化（トラッキングパラメータ除去など）後の SHA-256（先頭32文字）で生成し、冪等性を保証。
    - トラッキングパラメータ（utm_* 等）を除去する正規化ロジックを実装。

- DuckDB スキーマ (kabusys.data.schema)
  - DataSchema.md に基づく多層スキーマを実装し、初期化関数を提供：
    - init_schema(db_path) : DuckDB を初期化して全テーブル・インデックスを作成（冪等）。
    - get_connection(db_path) : 既存 DB へ接続（スキーマ初期化は行わない）。
  - 作成される主なテーブル（抜粋）:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 主なインデックス（コード×日付検索やステータス検索向け）を作成。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL のためのユーティリティとジョブを実装：
    - ETLResult データクラス：ETL 実行結果、品質問題、エラーの集約と to_dict() を提供。
    - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists, _get_max_date）。
    - 市場カレンダーに基づいて営業日調整を行うヘルパー（_adjust_to_trading_day）。
    - 差分更新用の最終取得日取得関数（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - run_prices_etl(conn, target_date, id_token=None, date_from=None, backfill_days=3)：差分 ETL（J-Quants から差分取得し save_daily_quotes で保存）をサポート。最終取得日からの backfill による後出し修正吸収ロジックを実装。
  - 設計方針として、品質チェックは重大な問題が見つかっても ETL を継続させ、呼び出し元が対応方針を決定できるようにしている。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- RSS パーサで defusedxml を利用し、XML 関連の脆弱性（XML Bomb 等）を軽減。
- RSS 取得で SSRF を防止するため、スキーム検証、プライベートアドレス検出、リダイレクト検査を強化。
- .env パーサはクォート内エスケープやインラインコメント処理を正しく扱うようになっており、誤った環境変数注入のリスクを低減。

### パフォーマンス (Performance)
- J-Quants クライアントはレートリミッタを導入し API レート制限を守る。
- DB へのバルク挿入はチャンク処理および INSERT ... RETURNING を利用してオーバーヘッドを低減。
- DuckDB のインデックスを作成して頻出クエリのパフォーマンスを向上。

### 互換性 / 要求環境 (Compatibility / Requirements)
- 本コードは Python の型注釈に | を使用しており、Python 3.10 以降を想定しています。
- DuckDB と defusedxml が必須ランタイム依存になります。
- デフォルトの DuckDB ファイルパスは data/kabusys.duckdb（settings.duckdb_path）。
- 自動環境読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

### マイグレーション / 注意事項 (Migration / Notes)
- 初回起動時は必ず init_schema(settings.duckdb_path) を呼び出してスキーマを作成してください（":memory:" もサポート）。
- 環境変数に JQUANTS_REFRESH_TOKEN / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID / KABU_API_PASSWORD 等が必須です（Settings プロパティが未設定時に ValueError を送出します）。
- run_news_collection() を実行する際に銘柄コード抽出を有効にするには known_codes パラメータに有効な銘柄コード集合を渡してください。
- J-Quants の API 制限（120 req/min）およびリトライ方針により、大量の一括リクエストはスロットリングされます。

---

今後のリリースでは、strategy（戦略ロジック）、execution（発注実装）、monitoring（監視・アラート）周りの実装追加、ETL の品質チェックモジュール（quality）およびテスト・例外ケースの追加・改善を予定しています。