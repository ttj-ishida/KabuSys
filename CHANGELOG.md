CHANGELOG
=========
このファイルは「Keep a Changelog」準拠で作成されています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- 進行中 / 要対応
  - run_prices_etl 関数が返す値のタプルが未完（コード末尾で第一要素のみを返しているように見える）。ETL の戻り値 (取得数, 保存数) を正しく返すよう修正が必要。
  - strategy/ および execution/ パッケージが未実装のまま初期化モジュールのみ存在するため、戦略実装および発注実装が未完。
  - 単体テスト・統合テストの整備（モックしてネットワークや DB 操作を置き換える設計になっている箇所があるためテスト作成が可能）。
  - ドキュメント（DataPlatform.md / DataSchema.md 参照の記述はある）が整備されるとさらに使いやすくなる。

0.1.0 - 2026-03-17
------------------
Added
- パッケージの初版リリース (kabusys v0.1.0)
  - パッケージ識別子: src/kabusys/__init__.py にて __version__="0.1.0" を設定。

- 環境設定 / ロード機能 (kabusys.config)
  - .env ファイルと環境変数の統合読み込みを実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（CWD に非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ実装:
    - export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントを考慮した堅牢な行パース。
  - Settings クラスで強い型付きプロパティを提供（必須環境変数は明示的にチェックして ValueError を送出）。
    - J-Quants: JQUANTS_REFRESH_TOKEN
    - kabuステーション: KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト値あり)
    - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス: DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH
    - システム環境: KABUSYS_ENV (development/paper_trading/live の検証)、LOG_LEVEL（DEBUG/INFO/... の検証）
    - convenience: is_live / is_paper / is_dev プロパティ

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティ _request を実装。
    - レート制限: 固定間隔スロットリングで 120 req/min を遵守（_RateLimiter クラス）。
    - 再試行ロジック: 指数バックオフ、最大 3 回、408/429/5xx に対するリトライ。
    - 429 の場合は Retry-After ヘッダを優先。
    - 401 受信時はリフレッシュトークンで自動的に id_token を再取得して 1 回だけリトライ（無限再帰回避あり）。
    - JSON デコード失敗時の明確なエラー。
  - 認証ヘルパ: get_id_token(refresh_token=None)（POST /token/auth_refresh）
  - データ取得関数:
    - fetch_daily_quotes (ページネーション対応)
    - fetch_financial_statements (ページネーション対応)
    - fetch_market_calendar
    - 取得時に fetched_at を UTC で記録する設計方針（Look-ahead Bias のトレーサビリティ）
  - DuckDB への保存関数（冪等性を考慮: ON CONFLICT DO UPDATE）
    - save_daily_quotes → raw_prices テーブルに保存
    - save_financial_statements → raw_financials テーブルに保存
    - save_market_calendar → market_calendar テーブルに保存
  - データ変換ユーティリティ: _to_float / _to_int（不正値耐性）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集と DuckDB 保存の実装。
  - セキュリティおよび堅牢性対策:
    - defusedxml を使用して XML Bomb 等を防御。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないことを検証（直接 IP と DNS 解決の両方で判定）
      - リダイレクト時もスキーム・ホストを検査するカスタムリダイレクトハンドラ (_SSRFBlockRedirectHandler)
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と読み込み上限チェック（Gzip 展開後も検査）
    - gzip 解凍失敗時の安全なフォールバック
  - URL 正規化と記事 ID 生成:
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）の除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート処理を行う _normalize_url
    - 正規化 URL の SHA-256（先頭32文字）を記事 ID にする _make_article_id（冪等性確保）
  - テキスト前処理: URL 除去、空白正規化 (preprocess_text)
  - RSS パース: fetch_rss → NewsArticle リストを返す（content:encoded を優先）
  - DuckDB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事IDのみを返す。チャンク分割と単一トランザクション。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付け保存（重複除去、チャンク、RETURNING による挿入数精査）
  - 銘柄コード抽出: 4桁数字パターンから既知のコード集合に含まれるものだけを抽出する extract_stock_codes
  - run_news_collection: 複数 RSS ソースを順次処理し、新規記事保存数を返す（各ソースは独立してエラーハンドリング）

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataSchema.md に基づき 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を実装。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・型チェックを多用（CHECK、PRIMARY KEY、FOREIGN KEY による整合性）
  - パフォーマンスのためのインデックス群を定義（例: idx_prices_daily_code_date 等）
  - init_schema(db_path) でディレクトリ自動作成→スキーマ作成（冪等）
  - get_connection(db_path) で既存 DB への接続を取得

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計に基づく差分取得/保存の実装方針（差分更新、backfill による後出し修正吸収、品質チェック連携）
  - ETLResult データクラスを追加（監査ログ・品質問題・エラーの集約）
  - 差分取得ヘルパ:
    - _table_exists, _get_max_date
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
    - _adjust_to_trading_day: 非営業日調整（market_calendar に基づく）
  - run_prices_etl 実装（差分算出・jq.fetch_daily_quotes -> jq.save_daily_quotes 呼び出し）
    - 初回は _MIN_DATA_DATE（2017-01-01）からロード
    - デフォルト backfill_days=3 をサポート
    - 取得・保存のログ出力

Security
- セキュリティに関する実装・注意点を多数導入（ニュース収集の SSRF 対策、XML の defusedxml 使用、レスポンスサイズ制限、J-Quants API のトークン管理と自動リフレッシュ）

Notes / Known issues
- run_prices_etl の戻り値が不完全に見える（現状コードは len(records), を返している箇所があり、タプルが未完）。ETLResult の返却や (fetched, saved) の完全な返却に修正が必要。
- strategy と execution の実装は未着手（パッケージ初期化のみ存在）。
- 実運用前に以下の点を確認推奨:
  - DB マイグレーション方針（スキーマ変更時の互換性）
  - 実行環境での環境変数設定（必須項目のドキュメント化）
  - 大量データ取得時のスループット調整（レート制限・チャンクサイズ）
  - J-Quants と kabu API の接続・認証フローの実運用確認

Contributors
- 初期実装者: （コードベースからの推測に基づく単一作者）

----
（注）上記は提供されたコード内容から機能・設計意図を推測してまとめた CHANGELOG です。実際の変更履歴やリリース日、貢献者情報はプロジェクトの VCS のコミット履歴やリリースノートに基づいて適宜更新してください。