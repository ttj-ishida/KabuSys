# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このリポジトリの初期リリースをコードベースから推測してまとめています。

## [0.1.0] - 2026-03-18

### Added
- パッケージ初期化
  - pakage 名称: KabuSys。トップレベルの __version__ を "0.1.0" として定義。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出するため、CWD に依存しない自動読み込みを行う。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーは export KEY=val 形式、クォート内のバックスラッシュエスケープ、インラインコメント処理に対応。
  - Settings クラスでアプリケーション設定を提供:
    - 必須設定の取得と未設定時の ValueError (例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID)。
    - データベースパスのデフォルト (DuckDB: data/kabusys.duckdb, SQLite: data/monitoring.db) を Path オブジェクトで返却。
    - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) の検証（許容値を厳格化）。
    - 環境判定のユーティリティプロパティ (is_live / is_paper / is_dev)。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - ベース機能:
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
    - get_id_token による ID トークン取得。
  - 信頼性向上のための設計:
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装する RateLimiter。
    - リトライロジック（最大 3 回、指数バックオフ）を実装。対象ステータスコード: 408, 429, および 5xx 系。
    - 401 受信時はトークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止）。
    - ページネーション間で共有するモジュールレベルの ID トークンキャッシュ。
    - JSON デコードエラーやネットワークエラーに対する適切な例外ハンドリング。
  - DuckDB への保存関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 冪等性を保つために INSERT ... ON CONFLICT DO UPDATE を使用。
    - fetched_at を UTC（ISO 8601 Z 表記相当）で記録し、データ取得時刻のトレーサビリティを確保。
  - データ型変換ユーティリティ (_to_float / _to_int) を含む（空値・不正値に対する安全な取り扱い）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し、前処理して raw_news テーブルへ保存する機能を実装。
  - 設計上の要点:
    - デフォルト RSS ソースを定義（例: Yahoo Finance のビジネス RSS）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の検査によるメモリ DoS 対策。
    - defusedxml を使った XML パースで XML Bomb 等への防御。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_ 等）の除去、フラグメント削除、クエリをキーでソート。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を保証。
    - SSRF 対策: リダイレクトごとにスキームとホストの検査を行うカスタム HTTPRedirectHandler、及びプライベート/ループバック/リンクローカルアドレスの検出。
    - HTTP/HTTPS 以外のスキームを拒否。
    - raw_news テーブルへの保存はチャンク化してトランザクションでまとめ、INSERT ... RETURNING で実際に挿入された記事 ID を返す。
    - 銘柄紐付け用に extract_stock_codes（4桁数字パターン + known_codes フィルタ）を実装。
    - news_symbols への紐付けを一括（重複除去・チャンク化）で保存する内部 API を提供。

- DuckDB スキーマと初期化（kabusys.data.schema）
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）＋ Execution レイヤのテーブル定義を実装。
  - テーブル例:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）や推奨インデックスを定義。
  - init_schema(db_path) で DB ファイル親ディレクトリの自動生成とテーブル・インデックスの作成を行う（冪等）。
  - get_connection(db_path) で既存 DB への接続を提供（初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計・実装（差分更新、保存、品質チェックの統合）。
  - ETLResult dataclass により各 ETL ランの集計結果（取得件数・保存件数・品質問題・エラーなど）を構造化して返す。
  - 差分更新を支援するユーティリティ:
    - テーブル存在チェック、最大日付取得、営業日調整（market_calendar に基づく調整）を実装。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
  - run_prices_etl の実装:
    - 最終取得日からの backfill_days（デフォルト 3 日）を使った再取得ロジック。
    - jquants_client.fetch_daily_quotes → save_daily_quotes を呼び出して差分 ETL を実行。
    - 取得・保存結果を返却する設計。

### Changed
- 初期リリースのため該当なし（新規追加のみ推定）。

### Fixed
- 初期リリースのため該当なし（新規追加のみ推定）。

### Security
- ニュース収集で以下のセキュリティ対策を導入:
  - defusedxml による安全な XML パース。
  - SSRF を防ぐためのリダイレクト時の検査とプライベート IP 検出。
  - HTTP/HTTPS 以外のスキーム拒否。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES）と gzip 解凍後のサイズ検査でメモリ消費の攻撃を緩和。
- J-Quants クライアントは認証トークンを安全に扱い、401 の際に自動リフレッシュし無限ループにならない設計。

### Notes / Known issues（コードから推測）
- run_prices_etl の末尾戻り値の記述がこのコード断片では途中で切れているように見える（ファイル末尾で切断）。実装上は (fetched_count, saved_count) を返す意図があるが、実コードの最終行を確認することを推奨します。
- schema の DDL や SQL 文は DuckDB 向けに記述されているため、運用時には DuckDB のバージョン互換性や SQL 構文の差異に注意してください。
- news_collector は外部ネットワークに依存するため、プロキシ設定やタイムアウト、リトライ戦略を運用ポリシーに合わせて調整することを推奨します。
- get_id_token は settings.jquants_refresh_token に依存するため、セキュアな環境変数管理が必要です。

---

この CHANGELOG は、提供されたコードスニペットの内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合は、そちらを優先してください。