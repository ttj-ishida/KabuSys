# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従っています。  
このファイルはリポジトリ内のコードから推測して作成した初期リリースの変更履歴です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-17

初期リリース — KabuSys 日本株自動売買システムの基盤実装を追加。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてバージョン番号 __version__ = "0.1.0" を定義し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定/ロード
  - src/kabusys/config.py を追加。
    - .env ファイルまたは環境変数からの設定読み込み（.env, .env.local の自動ロード、プロジェクトルートの検出は .git または pyproject.toml を基準）。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
    - .env 行パーサーは export プレフィックス・クォート付き値・インラインコメント等に対応。
    - OS 環境変数を保護する protected パラメータを用いた上書き制御。
    - 必須環境変数取得時の例外化（_require）。
    - 環境（development / paper_trading / live）とログレベルのバリデーション。
    - 各種設定プロパティ（J-Quants トークン、kabu API 設定、Slack トークン／チャンネル、DBパス等）を提供する Settings クラスと settings インスタンス。

- J-Quants データクライアント
  - src/kabusys/data/jquants_client.py を追加。
    - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
    - API レート制御（固定間隔スロットリングで 120 req/min を遵守する _RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx）。
    - 401 エラー時の自動トークンリフレッシュ（1 回まで）を実装。
    - ページネーション対応（pagination_key を追跡して重複ページを防止）。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead Bias のトレースを可能に。
    - DuckDB への冪等保存（ON CONFLICT DO UPDATE）を行う save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 型変換ユーティリティ (_to_float / _to_int) を追加し、不正値や空値を安全に扱う。

- ニュース収集
  - src/kabusys/data/news_collector.py を追加。
    - RSS フィードからのニュース収集（DEFAULT_RSS_SOURCES に Yahoo Finance をデフォルトで含む）。
    - defusedxml を用いた安全な XML パース（XML Bomb 対策）。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント除去）と記事ID生成（正規化URL の SHA-256 の先頭32文字）による冪等性確保。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト先に対する事前検証ハンドラ（プライベートアドレス・不正スキームを拒否）。
      - ホスト名の DNS 解決結果および直接 IP のプライベート判定。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - テキスト前処理（URL 除去、空白正規化）。
    - DuckDB へのバルク保存（save_raw_news）:
      - チャンク挿入（_INSERT_CHUNK_SIZE）およびトランザクションでまとめて INSERT ... ON CONFLICT DO NOTHING RETURNING id により、実際に挿入された新規記事ID一覧を取得。
    - 記事と銘柄コードの紐付け機能（extract_stock_codes, save_news_symbols, _save_news_symbols_bulk）:
      - 4桁銘柄コード抽出（正規表現）、既知銘柄セット（known_codes）との照合、重複除去、チャンク挿入で効率化。

- DuckDB スキーマ管理
  - src/kabusys/data/schema.py を追加。
    - Raw / Processed / Feature / Execution の多層データモデルに基づくテーブル定義を実装。
    - 定義済みテーブルの例:
      - Raw: raw_prices, raw_financials, raw_news, raw_executions
      - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature: features, ai_scores
      - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 適切な主キー・チェック制約・外部キー・インデックス（検索パターン想定に基づく）を追加。
    - init_schema(db_path) 関数で DB ディレクトリの自動作成と全DDLの冪等実行を提供。
    - get_connection(db_path) による既存 DB への接続。

- ETL パイプライン
  - src/kabusys/data/pipeline.py を追加（ETL 基盤）。
    - 差分更新を行う設計（DB の最終取得日から差分のみ取得）。
    - backfill_days（デフォルト 3 日）により直近数日を再取得して API の後出し修正を吸収。
    - 市場カレンダーの先読み（日数は _CALENDAR_LOOKAHEAD_DAYS = 90）。
    - 最小データ開始日 (_MIN_DATA_DATE = 2017-01-01) を定義。
    - ETL 実行結果を表す dataclass ETLResult（品質チェックの結果やエラー一覧を保持、has_errors / has_quality_errors プロパティを提供）。
    - DB 存在チェック・最大日付取得ユーティリティ（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - トレード用に非営業日を直近営業日に調整するヘルパー (_adjust_to_trading_day)。
    - run_prices_etl による株価差分 ETL 実装（jq.fetch_daily_quotes / jq.save_daily_quotes を利用）。

### Security
- ニュース収集における複数のセキュリティ対策を導入:
  - defusedxml による安全な XML パース。
  - SSRF 防止（スキーム検証、プライベートIP/ループバック/リンクローカル判定、リダイレクト先検査）。
  - 外部から読み込むレスポンスサイズ上限（10MB）と gzip 解凍後サイズ検査によるメモリ DoS/Gzip bomb 対策。
  - URL のスキームホワイトリスト（http/https）の厳格化。

### Performance / Reliability
- J-Quants API クライアントでのレート制御と再試行ロジックにより、API 仕様（120 req/min）や一時的なネットワーク障害に耐性を持たせた。
- DuckDB へのバルク挿入をチャンク化して SQL 長やパラメータ数を抑制し、トランザクションを用いて整合性・効率化を図った。
- ニュースの ID 生成により同一記事の重複挿入を防止、INSERT ... RETURNING により実際に挿入された行数を正確に把握可能。

### Documentation / Comments
- 各モジュールに詳細な docstring と設計方針コメントを付与。挙動（例: リトライロジック、Look-ahead 防止、品質チェックの扱いなど）を明示。

### Notes
- 本 CHANGELOG はコードベースから推測して作成したものであり、実際のリリースノートや追加機能・バグ修正はリポジトリの履歴やリリース管理に基づき更新してください。