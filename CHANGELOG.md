# CHANGELOG

すべての重要な変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

## Unreleased
- TODO / 既知の注意点
  - data.pipeline.run_prices_etl の実装が途中で終了しているように見えます（戻り値が途中で切れている）。本番利用前に関数の完了処理（tuple の完全な返却値、エラー処理など）を確認・修正してください。
  - パッケージのトップレベルで `monitoring` を __all__ に含めていますが、提供されているコードベース内に monitoring モジュールの実装は含まれていません。今後追加予定。

---

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース: KabuSys (バージョン 0.1.0)
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。
  - パッケージ構成の公開APIとして data, strategy, execution, monitoring を定義（monitoring は未実装）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD 非依存）。
    - 読み込み順: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは以下をサポート:
    - 空行・コメント行、`export KEY=val` 形式、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い（非クォート時は `#` の直前が空白の場合をコメントとみなす）など。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で扱う:
    - J-Quants / kabuAPI / Slack / DB パス（DuckDB / SQLite） / システム設定（KABUSYS_ENV, LOG_LEVEL）等。
    - KABUSYS_ENV と LOG_LEVEL の値検証（ホワイトリスト）。
    - is_live / is_paper / is_dev のヘルパープロパティ。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得用のクライアントを実装。
  - 設計上の特徴:
    - API レート制限（デフォルト 120 req/min）を固定間隔のスロットリングで順守 (_RateLimiter)。
    - リトライロジック（指数バックオフ、最大 3 回）。408/429 および 5xx を対象に再試行。
    - 401 Unauthorized は自動でリフレッシュトークンを用いて 1 回だけ再試行。
    - id_token のモジュールレベルキャッシュを共有してページネーションや複数呼び出しで使い回し。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead バイアスを防止。
    - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で実装。
  - 提供関数:
    - get_id_token: リフレッシュトークンから idToken を取得（POST）。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar: ページネーション対応でデータ取得。
    - save_daily_quotes / save_financial_statements / save_market_calendar: DuckDB へ冪等に保存（ON CONFLICT）。
  - データ変換ユーティリティ:
    - _to_float / _to_int：安全な型変換（空値や不正値は None、float 文字列の整数扱いの注意点など）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news / news_symbols に保存する処理を実装。
  - 設計上の特徴（セキュリティ・堅牢性重視）:
    - defusedxml を利用して XML Bomb 等の脆弱性を軽減。
    - RSS の取得時にリダイレクト先のスキーム検査とプライベートアドレス検査を行うカスタムリダイレクトハンドラ (_SSRFBlockRedirectHandler) により SSRF を防止。
    - 受信サイズ上限を設定（MAX_RESPONSE_BYTES = 10 MB）。Content-Length の事前チェックと実際の読み込みサイズ検査を実行（Gzip 圧縮後も検査）。
    - URL 正規化: スキーム・ホストを小文字化、トラッキング系クエリパラメータ（utm_ 等）を除去、フラグメント除去、クエリをソート。
    - 記事IDは正規化 URL の SHA-256 ハッシュ（先頭32文字）を使用して冪等性を確保（utm 等除去後に正規化）。
    - HTTP/HTTPS 以外のスキームの URL を拒否。
    - DB 保存はチャンク化（_INSERT_CHUNK_SIZE = 1000）してトランザクション内で実行、INSERT ... RETURNING を使い新規挿入 ID / 件数を正確に取得。
  - 提供関数:
    - fetch_rss: RSS を取得して NewsArticle リストを返す（XML パース失敗時は警告ログと空リスト）。
    - save_raw_news: raw_news に記事を保存し、挿入された記事IDのリストを返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを保存（ON CONFLICT DO NOTHING、RETURNING により挿入数を正確に返す）。
    - extract_stock_codes: テキスト中の4桁数字を抽出し、known_codes に含まれるもののみを返す。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋ Execution レイヤのテーブル定義を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック: 各カラムに CHECK 制約や PRIMARY KEY、外部キーを定義。
  - インデックス: 頻出クエリに合わせたインデックスを作成（例: idx_prices_daily_code_date 等）。
  - init_schema(db_path): ディレクトリ自動作成（必要時）、DDL とインデックスを作成して DuckDB 接続を返す（冪等）。
  - get_connection(db_path): 既存DBへ接続（スキーマ初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計方針に基づく差分更新処理の基礎を実装。
  - 定数:
    - データ最小開始日: 2017-01-01（_MIN_DATA_DATE）
    - カレンダー先読み: 90 日（_CALENDAR_LOOKAHEAD_DAYS）
    - デフォルトバックフィル日数: 3 日（_DEFAULT_BACKFILL_DAYS）
  - ETLResult dataclass を導入して ETL 実行結果（取得数、保存数、品質問題、エラー等）を表現。品質問題は quality モジュールの構造をそのまま保持し、to_dict で辞書化可能。
  - DB ヘルパー:
    - _table_exists / _get_max_date: テーブル存在チェック・最大日付取得。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date.
  - 市場カレンダー補助:
    - _adjust_to_trading_day: 非営業日の場合は過去方向で直近の営業日に調整（最大 30 日遡る）。
  - run_prices_etl: 株価日足の差分 ETL を実装（差分算出、backfill を考慮、J-Quants からの取得と保存）。
    - テスト容易性のため id_token を注入可能。
    - 品質チェック（quality モジュール）との統合ポイントを想定。
    - 注意: ファイル末尾の実装が途中で切れているため、戻り値の完全な返却等を確認する必要あり。

### Security
- RSS / XML 処理に関する安全対策を導入:
  - defusedxml を使用して XML パースの安全性を向上。
  - リダイレクト時・最終 URL に対するスキーム検査およびプライベートアドレス検査により SSRF を防止。
  - レスポンスサイズ上限（10MB）および Gzip 解凍後の再検査でメモリ DoS / Gzip bomb を軽減。

### Internal / Developer convenience
- テストしやすさを考慮した設計:
  - jquants_client の HTTP 呼び出しで id_token を注入可能。
  - news_collector の _urlopen をテストでモック差し替え可能（SSRF ハンドラを含む）。
  - .env 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を利用可能。

### Dependencies / 要注意
- 主要外部依存: duckdb, defusedxml（XML セキュリティ用）。
- ネットワーク呼び出しは urllib を使用。J-Quants API のレート制限や HTTP エラーハンドリングの挙動を念頭に置いてください。
- Slack や kabu API 関連の設定は Settings から取得するため、必要な環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定する必要があります。

---

参照:
- 各モジュールはコード内 docstring に設計方針・処理フロー・使用例を記載しています。実運用前に設定・シークエンス（schema の初期化、ETL 実行順、監視・エラーハンドリング）を整えてください。