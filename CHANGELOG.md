# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載します。  
このファイルは、与えられたコードベースの内容から機能・設計を推測して作成した初期のリリース履歴です。

全般的な表記ルール:
- バージョン番号は src/kabusys/__init__.py の __version__ を基準にしています。
- 日付は本 CHANGELOG 作成日時（2026-03-18）を使用しています（実際のリリース日と異なる場合があります）。

## [Unreleased]
- （現時点のリポジトリは初回リリースと推定されるため、Unreleased は空です）

## [0.1.0] - 2026-03-18

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys（src/kabusys）
  - __version__ = "0.1.0" を定義。

- 環境変数 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に実施。プロジェクトルートが見つからない場合は自動ロードをスキップ。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パースロジック:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを扱う。
    - インラインコメントルール（クォート無しの値で '#' の直前に空白がある場合はコメントと認識）を実装。
    - ファイル読み込み失敗時は警告を出す。
  - protected set を用いた .env 上書き制御（OS 環境変数を保護）。
  - Settings クラスによりアプリ設定をプロパティとして提供（必須設定は _require にて ValueError を送出）。
    - 必須環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値あり: KABU_API_BASE_URL（http://localhost:18080/kabusapi）、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）
    - KABUSYS_ENV の許容値: development / paper_trading / live（不正値で例外）
    - LOG_LEVEL の許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL（不正値で例外）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API ベース URL: https://api.jquants.com/v1 を想定。
  - レート制御: 固定間隔スロットリングで 120 req/min を守る（_RateLimiter, 最小間隔 60/120 秒）。
  - リトライ/バックオフ:
    - 最大 3 回までリトライ。
    - 指数バックオフ（base 2 秒）。
    - 408 / 429 / 5xx 系に対するリトライロジック。
    - 429 の場合は Retry-After ヘッダを優先。
  - 認証:
    - refresh token から id token を取得する get_id_token（POST /token/auth_refresh）。
    - モジュールレベルで id_token キャッシュを保持し、ページネーション間で共有。
    - 401 を受信した場合は id_token を自動リフレッシュして 1 回だけリトライ（無限再帰回避に allow_refresh フラグ）。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes（OHLCV）
    - fetch_financial_statements（四半期 BS/PL）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等実装）:
    - save_daily_quotes: raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials テーブルへ INSERT ... ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar テーブルへ INSERT ... ON CONFLICT DO UPDATE
  - ロギングで取得件数・保存件数を出力。
  - データ変換ユーティリティ (_to_float / _to_int) により安全な型変換を実現。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を取得して raw_news テーブルへ保存する処理を実装。
  - セキュリティ/堅牢性対策:
    - defusedxml を使用して XML Bomb 等を防止。
    - SSRF 対策: リダイレクト先のスキーム/ホストを検査するカスタムハンドラ（_SSRFBlockRedirectHandler）。
    - URL スキーム検証（http/https のみ許可）。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合は拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES＝10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - 受信時に Content-Length を事前チェック（不正値は無視）。
  - 記事ID: 正規化した URL の SHA-256 ハッシュ（先頭32文字）を使用して冪等性を確保。トラッキングパラメータ（utm_*, fbclid 等）を除去して正規化。
  - テキスト前処理: URL 除去、空白正規化。
  - DB 保存:
    - save_raw_news はチャンク化してトランザクション単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事IDのみを返却。
    - save_news_symbols / _save_news_symbols_bulk により (news_id, code) の紐付けをチャンク挿入（ON CONFLICT DO NOTHING）で保存し、挿入数を正確に返す。
  - 銘柄コード抽出: 正規表現 \b(\d{4})\b による 4 桁数字を候補として抽出し、既知銘柄セット known_codes と照合して重複除去して返す。
  - デフォルト RSS ソース: Yahoo Finance のビジネスカテゴリを設定（news.yahoo.co.jp）。

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層（＋実行層）スキーマを定義。
  - 主なテーブル（例）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 主キー・チェック制約・外部キーを含む DDL を提供。
  - 頻出クエリ向けのインデックス定義を用意。
  - init_schema(db_path) でディレクトリ自動作成（親ディレクトリがなければ作成）してテーブル作成を行う（冪等）。
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新を想定した ETL 実装（差分取得、保存、品質チェックの統合フロー）。
  - 設計パラメータ:
    - _MIN_DATA_DATE = 2017-01-01（J-Quants 提供データの開始日想定）
    - 市場カレンダー先読み: _CALENDAR_LOOKAHEAD_DAYS = 90
    - デフォルトバックフィル: _DEFAULT_BACKFILL_DAYS = 3（最終取得日の数日前から再取得して後出し修正を吸収）
  - ETLResult dataclass を導入し、ETL 実行結果（取得/保存件数、品質問題、エラー一覧）を保持・辞書化する API を提供。
  - テーブル存在チェック・最大日付取得ユーティリティ (_table_exists, _get_max_date) を提供。
  - 非営業日調整ヘルパー (_adjust_to_trading_day) を実装（market_calendar に基づき最寄り過去営業日に調整）。
  - 個別ジョブ例:
    - run_prices_etl: 差分 ETL（date_from の自動計算、backfill の適用、jq.fetch_daily_quotes / jq.save_daily_quotes の呼び出し）
  - 品質チェック連携（quality モジュールを想定）: 品質問題を収集し ETLResult に格納。重大度に応じた判定ロジックあり（has_quality_errors）。

### Changed
- 初回リリースのため該当なし（新規実装の集合）。

### Fixed
- 初回リリースのため該当なし。

### Security
- RSS パーサーで defusedxml を利用し XML 関連攻撃を軽減。
- SSRF 対策（リダイレクト先検査 / ホストがプライベートIPかどうかの判定）を実装。
- ネットワークから受信するコンテンツサイズに上限を設け、Gzip 解凍後もチェックして Gzip Bomb を防止。

### Notes / Implementation details
- jquants_client の _request は JSON デコード失敗時に詳細を含む RuntimeError を送出。
- id_token の自動リフレッシュは 1 回のみ行う設計（401 を受けたら 1 回再取得して再試行、再度 401 の場合は即失敗）。
- 各種保存関数は冪等性を重視し、raw 層は ON CONFLICT DO UPDATE、news 系は ON CONFLICT DO NOTHING（挿入件数を RETURNING で把握）。
- news_collector の fetch_rss はリダイレクト後の最終 URL も再検証する二重防御を行う。
- pipeline モジュールは品質チェックでエラーが検出されても ETL を継続する方針（呼び出し元が対処を決定する）。

---

この CHANGELOG はコード内容から機能・設計を推測して作成しています。実際の変更履歴やリリースノートと差異がある可能性があります。必要であれば、実際のコミット履歴やリリース日を基に日付や内容を調整します。