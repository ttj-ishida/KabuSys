CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。  

[Unreleased]
------------

- ―

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - kabusys.__version__ を "0.1.0" として公開。

- 環境設定管理 (kabusys.config)
  - .env/.env.local ファイルおよび環境変数から設定値をロードする自動ローダを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD に依存しない挙動）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env と .env.local の読み込み順序: OS 環境変数 > .env.local > .env(.local は override=True)。
    - OS 環境変数を保護する protected セットを用いた上書き制御。
  - .env 行パーサを実装:
    - コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - Settings クラスを提供（settings インスタンスを公開）。
    - 必須環境変数取得時に未設定なら ValueError を送出（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - デフォルト値を持つ設定（KABUSYS_ENV のデフォルトは "development"、LOG_LEVEL のデフォルトは "INFO"、Kabu / DB パスのデフォルト等）。
    - KABUSYS_ENV と LOG_LEVEL の入力値検証（許可値セットを定義）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
    - デフォルト DB パス: duckdb -> data/kabusys.duckdb、sqlite -> data/monitoring.db（expanduser 対応）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装。
    - レート制限 (120 req/min) を守る固定間隔スロットリング (_RateLimiter)。
    - 再試行ロジック (指数バックオフ、最大 3 回)。対象ステータス: 408, 429, 5xx。
    - 401 受信時はリフレッシュトークンで id_token を自動リフレッシュして 1 回だけ再試行（無限再帰回避のため allow_refresh フラグを使用）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements）。
    - JPX マーケットカレンダー取得 fetch_market_calendar。
    - モジュールレベルの ID トークンキャッシュを導入（ページネーション間でトークン共有）。
  - DuckDB への保存関数を実装（冪等性を重視）。
    - save_daily_quotes, save_financial_statements, save_market_calendar は INSERT ... ON CONFLICT DO UPDATE を用いて重複を排除・更新。
    - 型変換ユーティリティ (_to_float, _to_int) を提供（空値・不正値を None にするなどの堅牢性）。
    - 保存時に fetched_at を UTC ISO フォーマットで記録し、データの「いつ取得されたか」をトレース可能に。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news / news_symbols に保存する機能を実装。
    - defusedxml を使った XML パース（XML Bomb 等に対する防御）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないか検査（直接 IP と DNS 解決の両方をチェック）。
      - リダイレクト時にスキームとホストを検査するカスタム RedirectHandler を利用。
    - レスポンスサイズ制限（最大 10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - 記事ID は URL 正規化後の SHA-256 の先頭32文字を使用し冪等性を担保（utm_* 等トラッキングパラメータ除去、クエリソート、フラグメント除去等の正規化）。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id をチャンク単位で実行し、実際に挿入された記事IDリストを返す。トランザクション制御（begin/commit/rollback）あり。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けをチャンク・トランザクションで保存し、実際に挿入された件数を返す。
    - 銘柄コード抽出ロジック (extract_stock_codes):
      - 4桁数字パターンを抽出し、known_codes に含まれるもののみを返す（重複排除）。
    - run_news_collection: 複数 RSS ソースから独立して収集を行い、各ソースの新規保存件数を返却。known_codes を与えると銘柄紐付けも実施。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の各レイヤー向けテーブル DDL を定義。
    - raw_prices, raw_financials, raw_news, raw_executions 等（Raw Layer）。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等（Processed Layer）。
    - features, ai_scores（Feature Layer）。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等（Execution Layer）。
  - 各テーブルに対する適切なチェック制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を定義。
  - 頻出クエリ向けのインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) でディレクトリ自動作成を行い、全テーブル・インデックスを作成する初期化関数を提供（冪等）。get_connection(db_path) で既存 DB へ接続可能。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass による ETL 実行結果の集約（品質チェック結果・エラー一覧を含む）。
  - 差分更新を行うためのヘルパー関数:
    - _table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date。
    - _adjust_to_trading_day: 非営業日を直近の過去営業日に調整する補助。
  - run_prices_etl: 株価日足の差分 ETL を実装。
    - date_from が未指定の場合は DB の最終取得日から backfill_days（デフォルト 3 日）分さかのぼって再取得（後出し修正の吸収）。
    - データ取得は jquants_client の fetch_daily_quotes を用い、保存は jq.save_daily_quotes を使用。
  - ETL 設計方針:
    - デフォルトの差分単位は営業日1日分。
    - backfill により後出し修正への耐性を確保。
    - 品質チェックは重大度を持たせ、致命的な問題が検出されても ETL 自体は続行して呼び出し元が対応を決定できるように設計。

Security
- ニュース収集における SSRF・XML Bomb・メモリ DoS に対する多層防御を実装（URL スキーム検査、プライベートアドレス検査、リダイレクト検査、defusedxml、レスポンスサイズ上限、gzip 解凍後チェック）。
- J-Quants API の認証・再試行ロジックにより、401（トークン期限切れ）や一時的なネットワーク障害に対して安全にリトライを行う。

Migration / Usage notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
  - KABU_API_PASSWORD: kabu ステーション API パスワード
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- 自動 .env ロードはデフォルトで有効。テストや特別な環境で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB スキーマ初期化:
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)
- NewsCollector の銘柄紐付けを行うには known_codes に利用可能な銘柄コードのセットを渡すこと（extract_stock_codes は known_codes を参照してフィルタリングする）。
- API レート上限は 120 req/min。内部でスロットリングを行いますが、外部からの連続的な大量呼び出しには注意してください。

Notes / Known limitations
- 現在の実装は主要機能の初期版です。運用時には設定値（タイムアウト・バックフィル日数・RSS ソース等）を適宜調整してください。
- ETL の品質チェックモジュール (kabusys.data.quality) の詳細は本リリースのコードベースに依存します（quality.QualityIssue 型を参照）。

--- 

（以後のリリースでは機能追加・バグ修正・破壊的変更等をここに記載します）