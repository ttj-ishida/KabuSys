# Changelog

すべての変更は Keep a Changelog の形式に従います。  
現在のバージョンは 0.1.0（初回リリース）です。

さらに小さな修正や既知の問題は「注記 / 既知の問題」欄に記載します。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース: KabuSys (バージョン 0.1.0)
  - パッケージ公開 API: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring を __all__ でエクスポート。

- 環境設定管理モジュール (kabusys.config)
  - .env / .env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パース実装: コメント・export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理を考慮。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - OS 環境変数を保護する protected ロジック（.env.local が OS 環境変数を上書きしない）。
  - Settings クラスを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須検証。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等のデフォルト値。
    - KABUSYS_ENV / LOG_LEVEL の値検証 (許容値チェック) と便利プロパティ is_live/is_paper/is_dev。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティ _request 実装: JSON デコード、タイムアウト、例外ハンドリング、ログ出力。
  - レート制御: 固定間隔スロットリングによる 120 req/min 制御（_RateLimiter）。
  - 再試行ロジック: 指数バックオフ、最大 3 回、HTTP 408/429/5xx を再試行対象に。
  - 認証トークン管理: get_id_token (refresh token → idToken)、モジュールレベルのトークンキャッシュ、401 発生時のトークン自動リフレッシュ（1 回のみ）。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes（OHLCV 日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 各保存は INSERT ... ON CONFLICT DO UPDATE を用いて重複を排除・更新
  - データ変換ユーティリティ: _to_float, _to_int（頑健な型変換と空値処理）
  - 取得時の fetched_at は UTC タイムスタンプで記録（Look-ahead bias 対策に配慮）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得と記事保存ワークフローを実装:
    - fetch_rss: RSS 取得 → XML パース → 前処理 → 記事リスト返却
    - save_raw_news: DuckDB へチャンク化して INSERT ... RETURNING を用いたトランザクション保存
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING）および実挿入数の返却
    - extract_stock_codes: 4桁数字パターンから既知銘柄のみ抽出（重複除去）
    - run_news_collection: 複数 RSS ソースを横断して収集・保存・銘柄紐付けを実行、各ソースを独立してエラーハンドリング
  - セキュリティ・堅牢性:
    - defusedxml を利用して XML 攻撃（XML bomb 等）に対策
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - ホストがプライベート/ループバック/リンクローカルでないことをチェック（DNS で A/AAAA を解決して確認）
      - リダイレクト時もスキーム/ホスト検証を行うカスタムハンドラ（_SSRFBlockRedirectHandler）
    - レスポンスサイズ上限の導入（MAX_RESPONSE_BYTES = 10MB）と Gzip 解凍後の検査（Gzip bomb 対策）
    - 受信ヘッダ Content-Length の事前チェック
  - 付加機能:
    - URL 正規化（クエリ中のトラッキングパラメータを削除、ソート、フラグメント削除）
    - 記事 ID は正規化 URL の SHA-256 の先頭32文字で生成（冪等性確保）
    - テキスト前処理（URL 除去、空白の正規化）

- DuckDB スキーマ定義 / 初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の 3 層＋実行層に対応したテーブル定義を実装:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な型・制約（PRIMARY KEY、CHECK 制約、外部キー）を設定
  - 頻出クエリ用インデックスを定義
  - init_schema(db_path) によりディレクトリ自動作成＋DDL 実行でスキーマ初期化（冪等）
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新を行う ETL 設計:
    - 最終取得日を判定し新規分のみ取得（差分更新）
    - backfill_days により最終取得日の数日前から再取得して API の後出し修正を吸収（デフォルト 3 日）
    - 市場カレンダーは先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）
  - ETLResult dataclass を追加（対象日、取得/保存件数、品質問題、エラーメッセージなど）
  - 品質チェック（quality モジュール）と連携する設計（品質問題は集約して呼び出し元が判断）
  - ヘルパー関数:
    - _table_exists, _get_max_date, _adjust_to_trading_day, get_last_price_date, get_last_financial_date, get_last_calendar_date
  - run_prices_etl 実装（差分取得→保存のワークフロー、date_from 自動計算、ログ出力）

### Security
- XML パースに defusedxml を採用（XML-related の脆弱性対策）。
- RSS 取得での SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト時検査）。
- 外部から読み込む .env ファイルで OS 環境変数を安全に保護する挙動を採用。

### Documentation / Examples
- 各モジュールに docstring と設計方針のコメントを追加（使用例や設計意図を明示）。

### Notes / 既知の問題
- 一部モジュールはパッケージ名で placeholder（空の __init__.py）があり、strategy / execution の実装は今後拡張予定。
- run_prices_etl の末尾（返り値）に不完全な形跡が見られます（コードが途中で切れているため、戻り値のタプル（取得数, 保存数）を完全に返す意図があるようです）。実運用前に該当箇所の確認とテストを推奨します。
- quality モジュールの詳細な実装は本差分に含まれていないため、品質チェック周りの挙動は統合テストで確認が必要です。
- RSS ソースのデフォルトは Yahoo Finance のビジネスカテゴリのみ設定（DEFAULT_RSS_SOURCES）。運用時は収集対象ソースを適宜追加してください。
- DuckDB 回りは ON CONFLICT / RETURNING を使用しているが、環境によっては動作差（DuckDB バージョン依存）が生じる可能性があるため、使用する DuckDB バージョンでの互換性確認を推奨。

---

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートは変更履歴管理・Git のタグ付けに基づいて更新してください。）