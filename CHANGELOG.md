CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
このリポジトリの初期バージョンは 0.1.0 です。

Unreleased
----------

（未リリースの変更はここに記載してください）

0.1.0 - 2026-03-18
-----------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。
  - サブパッケージを公開: data, strategy, execution, monitoring。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。  
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（export 付き行、クォートやエスケープ、インラインコメントの取り扱いに対応）。
  - 必須設定読み取り用の _require() を実装（未設定時は ValueError を送出）。
  - 設定項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）をプロパティとして公開。
  - KABUSYS_ENV / LOG_LEVEL の値検証ロジックを追加（許可値外は ValueError）。
  - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）の展開ロジックを追加。

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティ _request を実装。
    - レート制限（120 req/min）を _RateLimiter により厳守。
    - 再試行（指数バックオフ、最大 3 回）。HTTP 408/429/5xx でリトライ。
    - 429 の場合は Retry-After を優先して待機。
    - 401 発生時は id_token を自動リフレッシュして 1 回だけ再試行（無限再帰防止）。
    - JSON デコードエラー・ネットワークエラーのハンドリング。
  - ID トークンの取得とモジュールレベルキャッシュ（get_id_token, _get_cached_token）。
  - データ取得関数を実装:
    - fetch_daily_quotes: 日足（ページネーション対応）
    - fetch_financial_statements: 財務データ（ページネーション対応）
    - fetch_market_calendar: JPX マーケットカレンダー
    - 取得時にページネーション用の pagination_key を扱う実装
  - DuckDB への保存関数（冪等に保存する upsert 実装）:
    - save_daily_quotes: raw_prices への INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials への INSERT ... ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar への INSERT ... ON CONFLICT DO UPDATE
  - データ型変換ユーティリティ _to_float / _to_int（安全な変換と空値処理）。
  - fetched_at を UTC で記録し、Look-ahead Bias のトレースを可能に。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news に保存する一連の処理を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - HTTP リダイレクト時にスキーム/ホストを検査するカスタムハンドラ（SSRF 防止）。
    - URL スキーム検証（http/https のみ許可）。
    - プライベート IP / ループバック / リンクローカル / マルチキャストの拒否（DNS 解決後にチェック）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後サイズチェック。
    - user-agent と gzip Accept-Encoding の指定。
  - テキスト前処理（URL 除去、空白正規化）。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url、utm_* 等の除去）。
  - 記事 ID を SHA-256（正規化 URL）先頭32文字で生成し冪等性を担保。
  - save_raw_news: チャンク分割で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い新規挿入IDのリストを返す。トランザクションでまとめてコミット/ロールバック。
  - save_news_symbols / _save_news_symbols_bulk: news_symbols（記事-銘柄紐付け）をチャンク挿入で保存し、INSERT RETURNING で挿入数を正確に把握。
  - extract_stock_codes: テキストから 4 桁銘柄コード抽出（既知コードセットでフィルタ、重複排除）。
  - run_news_collection: 複数 RSS ソースの収集を統合。ソース単位で堅牢にエラーハンドリングし、既存記事はスキップして新規のみ紐付けを作成。

- スキーマ / DB 初期化（src/kabusys/data/schema.py）
  - DuckDB 用のDDL を集約してスキーマを定義（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions など Raw Layer テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed Layer。
  - features, ai_scores など Feature Layer。
  - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution Layer。
  - インデックスの定義（頻出クエリ向け）。
  - init_schema(db_path): 親ディレクトリ自動作成、全テーブルとインデックスを作成する初期化関数を実装（冪等）。
  - get_connection(db_path): 既存 DB への接続を返す（初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult データクラスを実装（ETL 実行結果、品質問題・エラーの集約、辞書化メソッド）。
  - 差分更新のためのユーティリティ:
    - _table_exists, _get_max_date により最終取得日を判定。
    - _adjust_to_trading_day: 非営業日を直近営業日に調整（market_calendar を利用、最長 30 日遡り）。
    - get_last_price_date, get_last_financial_date, get_last_calendar_date を実装。
  - run_prices_etl の骨組みを実装（差分更新ロジック、backfill_days の扱い、取得→保存フロー）。  
    - 最終取得日から backfill_days 分再取得することで API の後出し修正を吸収する設計。
    - J-Quants クライアントの fetch / save を組み合わせて処理。
  - 品質チェック（quality モジュール）との連携を想定する設計（品質問題は収集を続行し呼び出し元で扱う方針）。

Changed
- N/A（初期リリース）

Fixed
- N/A（初期リリース）

Security
- defusedxml の採用、SSRF 対策、レスポンスサイズ制限、トラッキングパラメータ削除など、外部入力（RSS/API）関連の安全性を重視して実装。

Notes / Migration
- 自動 .env ロードはプロジェクトルートの検出に依存するため、パッケージ配布後に動作させる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って明示的に環境変数管理を行うことを推奨します。
- 必須環境変数が未設定の場合、Settings プロパティが ValueError を投げます（起動前に .env を整備してください）。
- DuckDB スキーマは init_schema() で初期化してください（get_connection() は既存 DB 接続用）。

Known issues / TODO
- run_prices_etl の戻り値や処理フローは実装済みだが、ETL 全体のジョブ（財務・カレンダーのフルフロー、品質チェックの適用など）は継続実装が想定されています。
- strategy / execution / monitoring パッケージの実装は本バージョンでは空の __init__.py のみ配置されており、各レイヤーの詳細実装は今後追加予定。

ライセンス
- ソースにライセンス記載がない場合はリポジトリの LICENSE を参照してください。