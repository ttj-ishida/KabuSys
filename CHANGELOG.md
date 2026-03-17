# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

※この CHANGELOG はリポジトリのコード内容から推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-17

初回リリース — KabuSys 基本モジュール群を追加。

### 追加 (Added)
- パッケージの初期化
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - __all__ に data, strategy, execution, monitoring を公開（strategy/execution モジュールはプレースホルダとして存在）

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env 読み込み機構:
    - プロジェクトルートを .git または pyproject.toml から検出し、ルート直下の .env と .env.local を読み込む。
    - 読み込み優先順位: OS 環境 > .env.local > .env
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサーは export プレフィックス・クォート・インラインコメント等に対応。
  - 必須環境変数の検証を行う _require を提供。
  - 取得可能な設定例:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
  - 環境区分判定ユーティリティ: is_live / is_paper / is_dev

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得を想定したクライアント実装。
  - 実装の主な特長:
    - レート制限（120 req/min）を守る固定間隔スロットリング実装 (_RateLimiter)。
    - リトライロジック（指数バックオフ、最大3回）。429 の場合は Retry-After を優先。
    - 401 受信時は自動でトークンをリフレッシュして1回リトライ（無限再帰防止）。
    - ページネーション対応（pagination_key を使って全ページ取得）。
    - 取得時刻を UTC の fetched_at として記録（Look-ahead bias 対策）。
    - DuckDB への保存は冪等性を確保（INSERT ... ON CONFLICT DO UPDATE）。
  - 公開 API:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
    - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)
  - データ型変換ユーティリティ: _to_float, _to_int（文字列化された数値の頑健な扱い）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュースを収集して raw_news / news_symbols に保存する一連の機能を実装。
  - 設計上の配慮:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - SSRF 対策: URL スキーム検証、リダイレクト先のスキーム/ホスト検査、プライベート IP 判定。
      - リダイレクト時に検査を行うカスタムハンドラ (_SSRFBlockRedirectHandler) を実装。
    - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）チェック、gzip 解凍後も検査（Gzip bomb 対策）。
    - URL 正規化: トラッキングパラメータ（utm_* 等）の除去、スキーム/ホスト小文字化、フラグメント除去。
    - 記事IDは正規化 URL の SHA-256 ハッシュの先頭32文字で生成し冪等性を担保。
    - テキスト前処理: URL 削除、空白正規化。
    - DB 保存はチャンク/トランザクション化し INSERT ... RETURNING で実際に挿入された ID を返す実装。
    - 銘柄コード抽出: 4桁の候補を正規表現で抽出し、known_codes でフィルタリング。
  - 公開 API:
    - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
    - save_raw_news(conn, articles) -> list[str]（新規挿入された記事IDのリスト）
    - save_news_symbols(conn, news_id, codes) -> int
    - run_news_collection(conn, sources=None, known_codes=None, timeout=30) -> dict[source_name, new_count]
  - テスト向けフック:
    - _urlopen をオーバーライドしてテストで差し替え可能

- DuckDB スキーマ定義 & 初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature / Execution）構造のテーブル群を定義。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY / CHECK / FOREIGN KEY）や頻出クエリ向けのインデックスを定義。
  - init_schema(db_path) でフォルダ作成 → テーブル作成 → インデックス作成までの初期化を行う（冪等）。
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない）

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新を想定した ETL 構成（差分取得、保存、品質チェックを想定）。
  - 実装の主な機能:
    - ETLResult dataclass により ETL 実行結果を構造化（品質問題、エラーなどを集約）。
    - テーブル存在チェック、最大日付取得ユーティリティ (_table_exists, _get_max_date)。
    - 市場カレンダーに基づく取引日の調整ヘルパー (_adjust_to_trading_day)。
    - raw_prices / raw_financials / market_calendar の最終取得日取得関数。
    - run_prices_etl: 差分更新ロジック（最終取得日から backfill_days を考慮して date_from を算出）、jquants_client 経由で取得 → 保存する処理の骨組み。
  - 定数: _MIN_DATA_DATE（デフォルト最古日 2017-01-01）、_CALENDAR_LOOKAHEAD_DAYS、_DEFAULT_BACKFILL_DAYS（デフォルト 3 日）など。

### 修正 (Fixed)
- 初回リリースのため特段の「修正」はなし（新規実装中心）。

### 既知の問題 (Known issues)
- run_prices_etl の戻り値実装に不備が見られます（関数のドキュメントは (fetched_count, saved_count) のタプルを期待しますが、実装の末尾が "return len(records), " のように片方しか返さない/文法ミスの可能性があります）。リリース後に修正が必要です。
- strategy / execution 用のモジュールはプレースホルダのみで、戦略実装や発注ロジックは未実装。

### セキュリティ (Security)
- RSS パースに defusedxml を使用し、XML の脆弱性対策を行っている。
- RSS フェッチ周りで SSRF の予防（スキーム検証、プライベートIP検出、リダイレクト検査）を実装。
- .env 読み込み時のファイル読み取り失敗は警告ログに留める実装。

### マイグレーション / 導入メモ (Migration / Notes)
- 必須の環境変数をセットしてください（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
- デフォルトの DuckDB ファイルパス: data/kabusys.duckdb。init_schema() を使って初期化してください。
- 自動 .env 読み込みが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

今後の予定（コードから推測）
- run_prices_etl の戻り値バグ修正・追加の ETL ジョブ（financials / calendar の完全な run_* ジョブ実装）。
- strategy / execution 層の実装（シグナリング・発注器の統合）。
- モニタリング / Slack 通知機能の実装（設定に Slack トークンがあるため実装予定を推測）。
- テスト追加と CI ワークフロー整備。

以上。