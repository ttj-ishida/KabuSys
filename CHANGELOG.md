# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-17
初期リリース — 日本株自動売買支援ライブラリ「KabuSys」の基本コンポーネントを追加。

### 追加
- パッケージ基盤
  - src/kabusys/__init__.py にてパッケージ定義とバージョン (0.1.0) を追加。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機構:
    - プロジェクトルートを .git または pyproject.toml から探索して .env と .env.local を自動読み込み。
    - OS 環境変数を保護する protected 機構を実装。
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサの強化:
    - export KEY=val 形式、シングル／ダブルクォート内のエスケープ処理、インラインコメント処理に対応。
  - 必須変数取得用の _require()、環境値検証（KABUSYS_ENV, LOG_LEVEL）と便利プロパティ（is_live / is_paper / is_dev）を提供。
  - 標準的な設定項目をプロパティとして提供（J-Quants トークン、kabu API、Slack トークン・チャンネル、DB パスなど）。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得 API クライアント実装。
  - レート制限対応（固定間隔スロットリング、120 req/min）。
  - リトライ機構（指数バックオフ、最大 3 回）、HTTP 429 の Retry-After ヘッダ優先処理、ネットワークエラー再試行。
  - 401 レスポンス時に自動でリフレッシュトークンから id_token を再取得して 1 回リトライする仕組み。
  - ページネーション対応（pagination_key を用いた連続取得）。
  - DuckDB への冪等保存関数を提供:
    - save_daily_quotes / save_financial_statements / save_market_calendar は ON CONFLICT ... DO UPDATE を用いた更新を行う。
  - 取得時刻 (fetched_at) を UTC で記録し、Look-ahead bias のトレースを可能にする。
  - 型変換ユーティリティ (_to_float, _to_int) を実装（不正値や空値は None で扱う）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news, news_symbols へ保存する一連の処理を実装。
  - セキュリティおよび堅牢性の考慮:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策: リダイレクトごとのスキーム/ホスト検査（_SSRFBlockRedirectHandler）、ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否。
    - URL スキームは http/https のみ許可。
    - レスポンス受信上限 (MAX_RESPONSE_BYTES=10MB) を設定し、gzip 解凍後のサイズ検査も実施（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去 (_normalize_url, _TRACKING_PARAM_PREFIXES)。
  - 記事 ID を正規化 URL の SHA-256 の先頭32文字で生成し冪等性を保証。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を使い、実際に挿入された記事 ID を返す。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への一括保存。チャンク処理とトランザクション管理を実装。
  - 銘柄コード抽出機能 (extract_stock_codes): 4桁数字パターンを抽出し、known_codes に基づきフィルタリング。
  - run_news_collection により複数ソースの収集をまとめて実行（ソース単位でエラーハンドリングし、1 ソース失敗でも他は継続）。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層を意識したスキーマを定義。
  - 生データ用テーブル: raw_prices, raw_financials, raw_news, raw_executions。
  - 整形済み・特徴量・実行用テーブル: prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等を定義。
  - 各種 CHECK 制約・PRIMARY KEY・FOREIGN KEY を設定。
  - 検索用インデックスを複数定義（頻出クエリの高速化を想定）。
  - init_schema(db_path) でディレクトリ作成・テーブル作成を行い、get_connection() を経由して接続を返す。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新を行う ETL ロジックの基本を実装（run_prices_etl の抜粋実装を含む）。
  - データ最小開始日の定義 (_MIN_DATA_DATE)、カレンダー先読み日数、バックフィル日数等の定数を提供。
  - ETL 実行結果を格納する ETLResult dataclass を追加（品質チェック、エラー集約、to_dict）。
  - テーブル有無チェック、最大日付取得ヘルパー、営業日調整ロジックを実装（_adjust_to_trading_day）。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
  - run_prices_etl: 差分取得ロジック（最終取得日 - backfill_days から再取得）、jq.fetch_daily_quotes / jq.save_daily_quotes を呼び出してフェッチ・保存を行う（処理結果をログ出力）。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 非推奨
- （初回リリースのため該当なし）

### セキュリティ
- news_collector に SSRF 対策、defusedxml 使用、レスポンスサイズ制限を実装して外部データ取り込みの安全性を確保。

### 既知の制限 / 備考
- 現時点では pipeline.run_prices_etl の戻り値組み立てが途中（ソースコードの末尾で tuple の最後にコンマがあり未完の可能性が見られます）。実装を継続して完全な ETL ワークフロー（品質チェック呼び出し、他リソースの ETL 等）を整備する必要があります。
- 外部依存: duckdb, defusedxml が必要。
- J-Quants API のレート制限や認証ロジックは実装済みだが、運用時は settings に正しいトークン・設定を用意すること。
- DB スキーマは多くの制約を含むため、既存 DB との互換性が必要な場合は注意が必要。

---

参考:
- 環境変数自動ロードはテストや CI で KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで無効化可能です。