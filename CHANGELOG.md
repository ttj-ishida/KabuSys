# CHANGELOG

このファイルは Keep a Changelog の形式に従っています。  
次の変更点は、このリポジトリのコードベースから推測して記載した初回リリースの内容です。

全般的注意:
- パッケージバージョンは `src/kabusys/__init__.py` の `__version__ = "0.1.0"` に合わせています。
- 日付はこの CHANGELOG 作成日です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17
初回リリース — 基本的なデータ取得、ETL、ニュース収集、スキーマ定義、および設定管理を提供。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（`kabusys`、`__version__ = "0.1.0"`、`__all__` 定義）。

- 環境設定管理 (`kabusys.config`)
  - `.env` / `.env.local` 自動読み込み機能を実装（プロジェクトルートは `.git` または `pyproject.toml` から検出）。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数で自動ロードを無効化可能。
  - `.env` のパースはコメント、`export KEY=val`、クォート内のエスケープ、行内コメント等に対応。
  - `Settings` クラスを実装し、J-Quants や kabu API、Slack、DBパスや実行環境フラグ（development/paper_trading/live）、ログレベル等のプロパティを提供。
  - 必須変数未設定時は `_require` で ValueError を送出。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API ベース処理を実装: ベースURL、レート制限、リトライ、トークン管理等。
  - 固定間隔スロットリングによるレート制御 (`_RateLimiter`): デフォルト 120 req/min（最小間隔 0.5s）。
  - リトライ戦略: 最大3回、指数バックオフ、408/429/5xx をリトライ対象に設定。429 の場合は `Retry-After` ヘッダを優先。
  - 401 Unauthorized 受信時は自動でリフレッシュトークンから ID トークンを再取得して1回リトライ（無限再帰防止のため allow_refresh 制御）。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes: 株価日足（OHLCV）取得（pagination_key を用いたページネーション）
    - fetch_financial_statements: 四半期財務データ取得
    - fetch_market_calendar: JPX マーケットカレンダー取得
  - DuckDB への保存関数（冪等設計: ON CONFLICT DO UPDATE）
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 保存時に取得時刻 (fetched_at) を UTC ISO8601 形式で記録し、Look-ahead bias のトレーサビリティに配慮
  - 型変換ユーティリティ:
    - `_to_float`: 空・不正値は None に変換
    - `_to_int`: "1.0" 等の小数表現を扱い、小数部が 0 以外の場合は None を返すなど厳密な変換を実施

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからニュース記事を取得・前処理・DB保存する機能を実装。
  - セキュリティ・堅牢性対策:
    - defusedxml を使った XML パースで XML Bomb 等に対策
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートIP判定（DNS 解決と IP 判定）を実施
    - リダイレクト検査ハンドラ (`_SSRFBlockRedirectHandler`) によるリダイレクト先の検証
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入し、gzip 解凍後もサイズを再検査（Gzip bomb 対策）
    - 受信時の Content-Length チェックと読み取りバイト数で超過判定
  - URL 正規化とトラッキングパラメータ除去 (`_normalize_url`)：
    - utm_ 等の既知トラッキングパラメータを除去、クエリソート、フラグメント除去、スキーム/ホスト小文字化
  - 記事ID は正規化 URL の SHA-256 の先頭32文字で生成（冪等性を担保）
  - テキスト前処理 (`preprocess_text`): URL 除去、空白正規化、トリム
  - RSS 取得関数 (`fetch_rss`) は gz 圧縮対応、XML の fallback 検索（channel/item の有無を考慮）
  - DuckDB 保存:
    - `save_raw_news`: INSERT ... ON CONFLICT DO NOTHING + RETURNING id、チャンク分割挿入、1 トランザクションでコミット
    - `save_news_symbols` / `_save_news_symbols_bulk`: 記事と銘柄の紐付けを INSERT ... RETURNING で正確にカウント、重複除去やチャンク化を行いトランザクションで処理
  - 銘柄コード抽出 (`extract_stock_codes`): 正規表現で 4 桁数字を検出し、known_codes に基づいてフィルタ、重複除去

- DuckDB スキーマ定義 (`kabusys.data.schema`)
  - Data Platform 構造に基づくスキーマ（Raw / Processed / Feature / Execution 層）を作成:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / FOREIGN KEY / CHECK）を定義しデータ整合性を確保
  - 頻出クエリ向けの索引定義を追加（例: code×date インデックス、orders/status 等）
  - `init_schema(db_path)` を提供: DB ファイルの親ディレクトリ自動作成、全DDL とインデックスを実行して接続を返す（冪等）
  - `get_connection(db_path)` を提供: 既存 DB への接続（スキーマ初期化は行わない）

- ETL パイプライン (`kabusys.data.pipeline`)
  - ETL の設計方針と差分更新ロジックを実装。
  - 定数・デフォルト:
    - データ開始日 `_MIN_DATA_DATE = 2017-01-01`
    - カレンダー先読み `_CALENDAR_LOOKAHEAD_DAYS = 90`
    - デフォルトバックフィル `_DEFAULT_BACKFILL_DAYS = 3`
  - ETL 実行結果を保持する `ETLResult` データクラスを実装（品質問題、エラー一覧、プロパティによる状態判定を含む）
  - テーブル存在チェック、最大日付取得ユーティリティ（`_table_exists`, `_get_max_date`）
  - 営業日に調整するヘルパー `_adjust_to_trading_day`
  - 差分更新ヘルパー:
    - `get_last_price_date`, `get_last_financial_date`, `get_last_calendar_date`
  - 株価差分ETLジョブ `run_prices_etl` を実装（date_from の自動算出、backfill 対応、J-Quants から fetch して save）
    - 既に最新の場合は早期リターン
    - id_token 注入可能でテスト容易性を配慮
  - 品質チェックへの統合ポイント（`quality` モジュールとの連携を想定）

### 修正 (Changed)
- N/A（初回リリースのため過去の変更履歴なし）

### 修正 (Fixed)
- N/A

### セキュリティ (Security)
- RSS パースに defusedxml を使用、SSRF 対策、レスポンスサイズ制限、gzip 解凍後の再検査など多層的な防御を実装。

### 既知の制限 / 注意点
- DuckDB に依存するため実行環境に duckdb が必要。
- J-Quants 用のリフレッシュトークン等、必須環境変数が未設定だと例外が発生する（Settings._require）。
- pipeline の完全な品質チェック（quality モジュール）は別実装を必要とする（このコードベース内に quality の詳細実装は含まれていない想定）。
- 一部の機能は外部サービス（J-Quants API、RSS ソース、kabuステーション、Slack）への接続が前提。

---

（今後のリリースでは、各モジュールのユニットテスト追加、quality モジュールの統合、監視/通知機能（Slack連携）の実装、実運用向けのより細かい設定/メトリクス等を追記予定です。）