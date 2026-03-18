CHANGELOG
=========

すべての変更は「Keep a Changelog」ガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

Unreleased
----------

- （なし）

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初回リリース。KabuSys: 日本株自動売買システムの基本コンポーネント群を追加。
- 環境設定管理（kabusys.config.Settings）
  - .env / .env.local をプロジェクトルートから自動読み込み（OS 環境変数が優先）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープシーケンス等に対応。
  - 必須環境変数取得ヘルパ（_require）と各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）を実装。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価（日足）、財務データ（四半期 BS/PL）、マーケットカレンダー取得 API を実装（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - レート制限対応（120 req/min、固定間隔スロットリング _RateLimiter 実装）。
  - 再試行ロジック（指数バックオフ、最大 3 回）。HTTP 408/429/5xx をリトライ対象に含める。
  - 401 Unauthorized 受信時はリフレッシュトークンで自動的に id_token を更新して 1 回リトライ（無限再帰防止）。
  - ページネーション対応（pagination_key を追跡して重複防止）。
  - DuckDB へ冪等保存する save_* 関数を実装（ON CONFLICT DO UPDATE を利用）：save_daily_quotes / save_financial_statements / save_market_calendar。
  - 取得時刻を fetched_at に UTC で記録し、look-ahead bias を考慮。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード収集（fetch_rss）と記事保存（save_raw_news）、銘柄紐付け（save_news_symbols / _save_news_symbols_bulk）を実装。
  - セキュリティ対策:
    - defusedxml を使用して XML 攻撃を防御。
    - SSRF 対策: URL スキーム検証、ホストのプライベートアドレス検査、リダイレクト時の事前検証用ハンドラ（_SSRFBlockRedirectHandler）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - http/https 以外のスキーム拒否。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url）。記事IDは正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
  - content:encoded を優先するパース、pubDate の RFC2822 パース（UTC 正規化）、本文の前処理（URL 除去・空白正規化）。
  - DB 保存はチャンク単位のバルク INSERT とトランザクションで実行し、INSERT ... RETURNING を用いて実際に挿入された件数/ID を正確に返す。
  - 銘柄コード抽出ユーティリティ（4桁数値、known_codes によるフィルタリング）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の各レイヤーに対応したテーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 適切な型チェック制約・PRIMARY KEY・FOREIGN KEY を定義。
  - よく使うクエリ向けのインデックス定義を追加（例: idx_prices_daily_code_date 等）。
  - init_schema(db_path) でディレクトリ作成、DDL 実行、接続返却（冪等）。get_connection で既存 DB へ接続。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETLResult データクラス（品質チェック結果・エラー情報含む）を実装。
  - 差分取得のためのヘルパ（テーブル存在チェック、最大日付取得、営業日調整）を実装。
  - run_prices_etl の差分更新ロジック（最終取得日から backfill_days を考慮して再取得）と J-Quants からの取得→保存のフローを実装（部分実装を含む）。
  - 設計上、品質チェックは Fail-Fast せずに問題検出は報告に留める方針。

- 共通ユーティリティ
  - 値変換ヘルパ（_to_float / _to_int）、URL/テキスト正規化、RSS pubDate パース、SSH/SSRF 検査など、データ処理に必要なユーティリティを多数追加。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- RSS パーサで defusedxml を採用、SSRF の多層対策、レスポンスサイズ制限などセキュリティ考慮を明記。

Notes / Migration
- 初期リリースのため既存互換性破壊はなし。ただし DB スキーマは init_schema() で作成されるため、既存データを利用するには移行手順を別途用意してください。
- J-Quants / Slack / kabu API 用の各種環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）は必須です。.env.example を参照して .env を作成してください。

Acknowledgements
- 本リリースはデータ取得・保存・セキュリティ・ETL の基盤を提供します。戦略実装や実際の発注ロジックは今後のリリースで拡張予定です。