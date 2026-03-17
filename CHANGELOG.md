CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の慣例に従います。
リリース日付はコードベースから推定した初期リリース日時を使用しています。

[Unreleased]
-------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-17
-------------------

Added
- 初期リリース。パッケージ名: kabusys、バージョン: 0.1.0。
- パッケージ構成（主要モジュール）を追加:
  - kabusys.config: 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - kabusys.data: データ取得・保存関連（J-Quants クライアント、ニュース収集、DuckDB スキーマ、ETL パイプライン）
  - kabusys.strategy: 戦略用パッケージ（初期 __init__ を用意）
  - kabusys.execution: 発注/実行関連パッケージ（初期 __init__ を用意）
  - kabusys.monitoring を __all__ に含める（将来の監視モジュール予備）

- 環境設定機能（kabusys.config）:
  - .env/.env.local ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
  - .env 解析ロジックを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応など）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD をセットすることで自動読み込みを無効化可能。
  - Settings クラスを提供し、以下の設定をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
  - 環境変数未設定時は明確な ValueError を送出する実装。

- J-Quants API クライアント（kabusys.data.jquants_client）:
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
  - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter を実装。
  - リトライ戦略を実装（指数バックオフ、最大 3 回、HTTP 408/429 および 5xx を対象）。
  - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動更新して 1 回だけリトライ。
  - ページネーション対応（pagination_key を用いた継続取得）。
  - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE）を実装:
    - save_daily_quotes → raw_prices
    - save_financial_statements → raw_financials
    - save_market_calendar → market_calendar
  - 取得時刻（fetched_at）を UTC で記録して look-ahead bias を検討可能にする。
  - 値変換ユーティリティ（_to_float, _to_int）を用意し、型変換ルールを明示。

- ニュース収集モジュール（kabusys.data.news_collector）:
  - RSS フィード取得と raw_news への保存処理を実装（デフォルトソース: Yahoo Finance ビジネスカテゴリ）。
  - セキュリティ対策:
    - defusedxml を使用して XML Bomb 等に対処。
    - SSRF 対策: URL スキーム検証（http/https のみ）・リダイレクト先の検査・プライベートIP拒否（DNS 解決および IP 直接判定）。
    - レスポンス読み込みの最大バイト数制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検証（Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）と SHA-256 による記事 ID 生成（先頭32文字）で冪等性を確保。
  - 前処理: URL 除去、空白正規化、title/content の統一処理。
  - RSS の pubDate をパースして UTC naive datetime に変換（失敗時は現在時刻で代替）。
  - DB 保存:
    - save_raw_news はチャンク挿入＋INSERT ... RETURNING id で新規挿入 ID リストを返す（トランザクションでまとめてコミット）。
    - save_news_symbols / _save_news_symbols_bulk は記事と銘柄コードの紐付けを重複排除して挿入（RETURNING を利用して挿入数を返す）。
  - extract_stock_codes: 4桁数字の抽出と known_codes によるフィルタリングで銘柄コード抽出。
  - run_news_collection: 複数ソースを順次処理し、ソースごとにエラーハンドリングして継続可能な収集ジョブを実装。新規記事のみ銘柄紐付けを行う。

- DuckDB スキーマ定義 / 初期化（kabusys.data.schema）:
  - DataPlatform.md に基づく 3 層 + Execution 層スキーマを実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY、CHECK、FOREIGN KEY）を定義。
  - 頻出クエリ用のインデックス群を定義（code×date / status / foreign keys 等）。
  - init_schema(db_path) でディレクトリ自動作成・DDL 実行して初期化するユーティリティを提供。get_connection は既存 DB への接続取得を提供。

- ETL パイプライン（kabusys.data.pipeline）:
  - ETLResult データクラスを導入して ETL 実行結果・品質問題・エラー一覧を保持。
  - 差分更新ヘルパー（テーブル存在チェック、最大日付取得、営業日の調整）を実装。
  - run_prices_etl の骨組みを追加（差分算出、backfill_days の取扱い、fetch → save の流れを実装）。
  - 市場カレンダーの先読み日数・バックフィル方針など ETL 設計方針を反映した定数を定義。

Changed
- 初回リリースのため履歴上の「変更」はありません（初期機能の追加に相当）。

Fixed
- 初回リリースのため履歴上の「修正」はありません。

Security
- ニュース収集に関する SSRF 対策、defusedxml の採用、受信バイト数制限などセキュリティ考慮を含めて実装。

Notes / Breaking changes / Migration
- 環境変数必須項目:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - （必要に応じて）KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH
- .env 自動読み込みはデフォルトで有効。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。
- DuckDB の初期化は init_schema() を必ず呼び出してください。既存テーブルがあれば DDL はスキップされます（冪等）。
- J-Quants API のレート制限・リトライ・トークン自動リフレッシュの実装により、運用時の API 呼び出しは比較的安全に行えますが、運用負荷に応じた監視・ログ設定を推奨します。
- news_collector の既知制約:
  - 現在デフォルト RSS ソースは Yahoo Finance のみ。sources 引数で任意ソースを指定可能。
  - extract_stock_codes は単純な 4 桁数字マッチ（正規表現）を使うため誤検出・見落としの可能性あり。known_codes を与えてフィルタリングすることを想定。

Acknowledgements
- 本リリースはセキュリティ（SSRF・XML Bomb・Gzip Bomb）とデータ品質（fetched_at 記録、冪等性）に配慮した設計を先行して実装しています。今後は監視・アラート、戦略ロジック、発注実行の具体実装を追加予定です。