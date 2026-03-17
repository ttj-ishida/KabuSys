# CHANGELOG

すべての重要な変更点を記録します。項目は Keep a Changelog の慣例に従っています（リンク等は省略）。  
バージョン番号はパッケージの __version__ に合わせています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買プラットフォームのコア機能（設定管理、外部データ取得・保存、ETL、スキーマ定義、ニュース収集等）を実装しました。

### Added
- パッケージ基礎
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。公開モジュール: data, strategy, execution, monitoring。バージョンは 0.1.0 に設定。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート判定機能を追加（.git または pyproject.toml を探索）。
  - 自動 .env ロード機能（読み込み順: OS 環境 > .env.local > .env）。テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env のパース実装:
    - export KEY=val 形式、クォート（シングル/ダブル）中のエスケープ、インラインコメントの扱い、クォート無しのコメント判定などに対応。
    - 読み込み失敗時は警告を出力して継続。
    - OS 環境変数を保護する protected 機能（上書き防止）。
  - 必須項目チェック（_require）：未設定時は ValueError を送出。
  - 設定項目（プロパティ）:
    - J-Quants / kabuステーション / Slack の各トークン・ID、データベースパス（DuckDB/SQLite デフォルトパス）、環境（development/paper_trading/live）とログレベルの検証、is_live/is_paper/is_dev 判定。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API から株価日足、財務データ（四半期 BS/PL）、市場カレンダーを取得するクライアントを実装。
  - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter を導入。
  - HTTP リクエストでの堅牢性:
    - 再試行ロジック（指数バックオフ、最大 3 回）を実装。対象ステータス: 408, 429, 5xx。
    - 401 受信時はリフレッシュトークンで id_token を自動更新して1回リトライ（無限再帰防止）。
    - ページネーション対応（pagination_key を利用）。
  - id_token キャッシュをモジュールレベルで保持してページネーション間で共有。
  - データ取得関数:
    - fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()（いずれもページネーション対応）。
  - DuckDB への保存関数（冪等性を確保）:
    - save_daily_quotes(), save_financial_statements(), save_market_calendar()。ON CONFLICT DO UPDATE により上書きして重複排除。
    - fetched_at は UTC ISO 形式で記録し、Look-ahead Bias を防ぐために「いつデータを取得したか」を追跡可能に。
  - 型変換ユーティリティ _to_float(), _to_int()（安全な変換と不正値の扱い）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news / news_symbols に保存する機能を実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の対策）。
    - SSRF 対策: リダイレクトハンドラでスキームとホスト（プライベートIP）を検査。DNS 解決した全 A/AAAA レコードをチェックしてプライベート/ループバック/リンクローカル/マルチキャストを拒否。
    - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - URL 正規化:
    - トラッキングパラメータ（utm_*, fbclid 等）を除去し、スキーム・ホストを小文字化、クエリをソート、フラグメントを削除。
    - 記事ID は正規化 URL の SHA-256 の先頭32文字を使用し冪等性を保証。
  - テキスト前処理（URL除去・空白正規化）。
  - RSS 取得関数 fetch_rss(): XML パース失敗時は warning を出し空リストを返す。HTTP エラーは上位に伝播。
  - DuckDB への保存:
    - save_raw_news(): INSERT ... RETURNING id を用い、チャンク単位でトランザクションにまとめて挿入。実際に挿入された記事IDを返す。
    - save_news_symbols(), _save_news_symbols_bulk(): news_symbols の一括保存（重複除去とチャンク挿入、INSERT ... RETURNING により実挿入件数を返却）。
  - 銘柄コード抽出:
    - 4桁数字パターンを抽出し、known_codes セットでフィルタ（重複除去）。extract_stock_codes() を提供。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを登録（DEFAULT_RSS_SOURCES）。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - DataPlatform 設計に基づく3層（Raw / Processed / Feature）＋Execution 層のテーブル定義を追加。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）を定義。
  - 頻出クエリ向けのインデックス群を定義。
  - init_schema(db_path): ディレクトリ自動作成（必要な場合）後、全 DDL を実行して冪等に初期化する関数を提供。
  - get_connection(db_path): 既存 DB への接続を返す関数を提供（スキーマ初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新に基づく ETL ワークフローを実装するためのユーティリティ群とジョブを追加。
  - ETLResult データクラスを導入（取得件数、保存件数、品質問題、エラー等を集約）。品質問題は quality.QualityIssue を想定して取り扱う（to_dict() でシリアライズ可能）。
  - テーブル存在チェック、最大日付取得のヘルパー関数（_table_exists, _get_max_date）。
  - 市場カレンダーに基づいた営業日調整ヘルパー（_adjust_to_trading_day）。
  - 差分更新用ヘルパー関数:
    - get_last_price_date(), get_last_financial_date(), get_last_calendar_date()
  - run_prices_etl():
    - 差分取得ロジックを実装。date_from 未指定時は DB の最終取得日から backfill_days （デフォルト 3 日）前から再取得して API の後出し修正を吸収。
    - J-Quants クライアント（jquants_client）を使って fetch/save を行い、取得数と保存数を返す。
  - ETL の設計方針: 品質チェック（quality モジュール）を呼び出し、重大エラーでも全件収集を継続する（Fail-Fast ではない）。id_token を注入可能でテストしやすい設計。

- その他
  - data パッケージのモジュール構成（__init__.py あり）。
  - strategy と execution パッケージのプレースホルダ（__init__.py）を追加（今後の拡張余地）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集における SSRF 対策、defusedxml による XML パース、レスポンス・サイズ制限、gzip 解凍後の再チェック等を導入し外部入力の安全性を強化。
- .env 読み込み時に OS 環境変数を保護（protected set）する機能を実装して意図しない上書きを防止。

### Notes / Known limitations
- strategy/ execution/ monitoring の本格実装は未着手で、将来のリリースで追加予定。
- quality モジュール（データ品質チェック）は呼び出しを想定しているが、実際のチェック実装やルールは別モジュールで提供されることを想定。
- J-Quants API のエンドポイントやレスポンスの詳細に依存するため、API 仕様の変更時は jquants_client の修正が必要。
- RSS 解析は標準的なフィードを対象としているが、フィードの多様性（特殊な名前空間や非標準フォーマット）への対応は一部フォールバック実装に頼るため、個別ソースでの調整が必要になる可能性あり。

---

（今後のリリースでは戦略ロジック、発注実行連携、モニタリング・アラート、品質チェックルール群の追加を予定しています。）