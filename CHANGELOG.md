# CHANGELOG

すべての重要な変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。  

なお、このリポジトリの初期バージョンとしてリリースされた内容を v0.1.0 にまとめています。

## [Unreleased]

（現在のところ未リリースの変更はありません）

## [0.1.0] - 2026-03-17

### Added
- 初回リリース（KabuSys 0.1.0）。
- パッケージ基盤
  - パッケージメタ情報: kabusys.__version__ = 0.1.0、公開モジュール一覧を __all__ に定義。
  - 空のサブパッケージプレースホルダ: execution, strategy, monitoring（将来的な実装用）。
- 設定/環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装。
    - 読み込み順序: OS環境 > .env.local > .env
    - プロジェクトルートは .git または pyproject.toml を基準に自動検出（CWD 非依存）。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサの堅牢化:
    - export プレフィックス対応、クォート/エスケープ対応、インラインコメント処理。
    - 無効行・空行・コメント行のスキップ。
  - Settings クラスで各種必須設定をプロパティとして提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - 環境値のバリデーション:
    - KABUSYS_ENV は development / paper_trading / live のみ許可。
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許可。
  - デフォルト DB パス設定（DuckDB/SQLite）を提供。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装:
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）。対象ステータス: 408, 429, 5xx。429 は Retry-After ヘッダ優先。
    - 401 受信時は refresh token で自動的に id_token を再取得して 1 回だけリトライ。
    - JSON デコードエラー時に詳細メッセージを含めて例外化。
    - モジュールレベルの id_token キャッシュを導入（ページネーション間で共有）。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務四半期データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
    - 各 fetch 関数で取得件数のログ出力。
  - DuckDB への保存関数（冪等性を重視）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE による保存。
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE。
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE。
    - 保存前に fetched_at を UTC ISO8601 で記録。PK 欠損行はスキップし警告ログを出力。
  - ユーティリティ関数: _to_float / _to_int（安全な型変換、空値/不正値は None）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得と記事保存処理の実装。
  - セキュリティ・堅牢化:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルかを検査し拒否。
    - リダイレクト時にもスキーム/ホスト検査を実施するカスタム RedirectHandler を導入。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、受信時と gzip 解凍後のサイズチェックを実施（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding ヘッダを送信。
  - URL 正規化 & 記事ID生成:
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）を除去しクエリをソートして正規化。
    - 正規化 URL から SHA-256 の先頭 32 文字を記事IDとして生成（冪等性確保）。
  - テキスト前処理（URL 除去・空白正規化）。
  - RSS パーシングのフォールバック（channel/item がない場合にも探索）。
  - DuckDB への保存（効率化と冪等性）:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDを返す。チャンク分割・1 トランザクションでまとめて処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク挿入・INSERT RETURNING で正確に挿入数を取得。トランザクションとエラーハンドリングを実装。
  - 銘柄コード抽出: テキストから 4 桁数字の候補を抽出し、known_codes に含まれるものだけを返す。
  - 統合ジョブ run_news_collection を実装:
    - 複数ソースを独立して処理し、個別ソースの失敗は他ソースに影響を与えない。
    - 新規記事のみ銘柄紐付けを行う。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataSchema.md に基づく多層（Raw / Processed / Feature / Execution）テーブル定義を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型制約・CHECK・PRIMARY KEY・FOREIGN KEY を定義。
  - 検索パフォーマンス向けのインデックスを複数定義。
  - init_schema(db_path) によりディレクトリの自動作成を含めたスキーマ初期化を実装（冪等）。
  - get_connection(db_path) で既存 DB への接続を提供（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラスを導入し、ETL 実行結果（取得件数・保存件数・品質問題・エラー）を集約。
  - ユーティリティ:
    - _table_exists、_get_max_date（テーブルの存在チェック・最終日取得）
    - _adjust_to_trading_day（非営業日の調整）
    - get_last_price_date / get_last_financial_date / get_last_calendar_date（差分更新用の最終日取得）
  - run_prices_etl（株価差分 ETL）を実装（差分取得ロジック、backfill_days による再取得）。J-Quants クライアントの fetch/save を利用。
  - ETL の設計方針として「差分更新」「backfill による後出し修正吸収」「テスト容易性（id_token 注入）」を採用。
  - 品質チェック（quality モジュール）との連携を想定（品質問題は収集しつつ ETL は継続する方針）。

### Documentation
- 各モジュールに docstring と設計意図・注意点を記載（例: Look-ahead bias 対策、冪等性、セキュリティ対策など）。

### Security
- defusedxml の使用、SSRF 対策、レスポンスサイズ制限、URL スキーム制限などを導入し外部入力に対する防御を追加。
- 環境変数で機密情報（トークンやパスワード）を取得する設計を採用（直接コードに埋め込まない）。

### Compatibility / Requirements
- DuckDB を DB backend として利用（duckdb パッケージが必要）。
- defusedxml を RSS パースに利用。
- ネットワークアクセス時に urllib を利用しており、J-Quants API と RSS 配信元に接続します。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings にて未設定時は ValueError）

### Known limitations / Notes
- strategy、execution、monitoring サブパッケージは現状プレースホルダ（実装予定）。
- pipeline.run_prices_etl 等はいくつかの連携（quality モジュールや追加 ETL ジョブ）を前提としており、拡張が予定されている。
- 実運用では J-Quants のレート制限や Slack / kabuapi との連携を考慮した追加の運用制御が必要。

---

参照:
- パッケージルート: src/kabusys/
- 主なモジュール: config.py, data/jquants_client.py, data/news_collector.py, data/schema.py, data/pipeline.py

（詳細な設計や使用例は各モジュールの docstring を参照してください）