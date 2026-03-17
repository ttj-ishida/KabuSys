# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このプロジェクトの初期リリースおよび実装内容は、提供されたソースコードから推測して作成されています。

※ バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に基づきます。

## [Unreleased]

## [0.1.0] - 2026-03-17

初期リリース。本リリースでは、日本株自動売買システム（KabuSys）のコアとなる設定管理、データ取得・保存、RSSニュース収集、DuckDBスキーマ、ETLパイプラインの基礎実装を含みます。

### Added
- パッケージメタ
  - パッケージのバージョンを 0.1.0 として公開（src/kabusys/__init__.py）。

- 設定管理（src/kabusys/config.py）
  - .env / .env.local や環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により CWD に依存しない読み込みを実現。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）。
    - .env のパースは export 形式、クォート文字列、インラインコメントなどに配慮した堅牢な実装。
    - OS 環境変数を保護するため `protected` キーを用いた上書き制御を採用。
  - Settings クラスを提供し、以下の主要設定をプロパティ経由で取得：
    - J-Quants / kabu API / Slack トークン・チャネル、DB パス（DuckDB/SQLite）、環境（development/paper_trading/live）、ログレベルなど。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（不正値は ValueError）。

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API から株価日足、財務データ、マーケットカレンダーを取得するクライアントを実装。
  - 設計特徴:
    - API レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）を導入。408/429/5xx などの再試行対象に対応。
    - 401 受信時にはリフレッシュトークンから id_token を自動更新して1回再試行（無限再帰防止措置あり）。
    - ページネーション対応（pagination_key）で全件取得。
    - データ取得時に fetched_at を UTC で付与し、取得時点のトレースを可能にする（Look-ahead Bias 対策）。
    - DuckDB へ保存する際、INSERT ... ON CONFLICT DO UPDATE により冪等性を保証する save_* 関数を提供：
      - save_daily_quotes, save_financial_statements, save_market_calendar
    - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正値・空値を安全に取り扱う。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからニュース記事を取得・前処理・DB保存する仕組みを実装。
  - 設計特徴（セキュリティ・堅牢性重視）:
    - defusedxml による XML パースで XML Bomb などの攻撃を軽減。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームとホスト/IP の事前チェックを行う専用ハンドラ（_SSRFBlockRedirectHandler）。
      - ホスト名の DNS 解決後にプライベート/ループバック/リンクローカル/マルチキャストを拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を設け、大きすぎるレスポンスはスキップ。
    - gzip 圧縮レスポンスの解凍時にもサイズチェックを行い Gzip Bomb を防止。
    - URL 正規化（_normalize_url）で utm_* などのトラッキングパラメータを削除、SHA-256（先頭32文字）で記事IDを生成（冪等性確保）。
    - テキスト前処理（URL除去、空白正規化）。
  - DB 保存:
    - save_raw_news はチャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事IDのみを返す。
    - save_news_symbols / _save_news_symbols_bulk により記事と銘柄コードの紐付けをトランザクションでまとめて挿入（重複除去、RETURNING で正確な挿入件数を取得）。
  - 銘柄抽出ロジック（extract_stock_codes）:
    - 正規表現で4桁数字を抽出し、known_codes に基づいて有効銘柄コードのみを返す（重複除去）。

- DuckDB スキーマ（src/kabusys/data/schema.py）
  - DataPlatform.md に基づく3層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を提供。
  - 主要テーブル（例）:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各カラムに対する CHECK 制約、PRIMARY KEY、外部キー制約を定義。
  - クエリパターンを想定したインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) によりディレクトリ自動作成と DDL 実行で初期化（冪等）。get_connection を提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新・バックフィル・品質チェックを想定した ETL パイプライン基礎を実装。
  - 主要要点:
    - ETLResult データクラスにより ETL の集計結果（取得数、保存数、品質問題リスト、エラーリスト等）を格納・辞書化可能。
    - 差分計算用ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）を提供。
    - 市場カレンダーを用いた非営業日の調整ロジック（_adjust_to_trading_day）。
    - run_prices_etl による差分取得処理（最終取得日からの backfill をサポート、デフォルト backfill_days=3）および jq.fetch_daily_quotes / jq.save_daily_quotes の呼び出し。
    - ETL は Fail-Fast を避け、品質チェックでの問題も収集して呼び出し元で判断可能な設計。

### Security
- defusedxml を使用した XML パースによる安全化（news_collector）。
- SSRF 対策（スキーム検証、プライベートIP拒否、リダイレクト検査）。
- レスポンスサイズ制限および Gzip 解凍後サイズチェックで DoS 対策。
- .env ローダーは OS 環境変数を保護する仕組みを提供。

### Notes / Implementation details
- HTTP クライアントは標準ライブラリ urllib を使用。タイムアウトや例外処理、ヘッダ処理を実装。
- J-Quants の id_token はモジュールレベルでキャッシュし、ページネーション間で共有。
- DuckDB の SQL 実行は executemany / トランザクションを活用して効率的に保存。
- 多くの関数で入力値検証・欠損行スキップ（PK 欠損の警告ログ出力）を行い、堅牢性を高めている。

### Fixed
- （初期リリースのため該当なし）

### Changed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

---

開発・運用にあたっての推奨事項（今後の変更・改善候補）
- 単体テスト・統合テストの追加（HTTP クライアントや RSS 取得、DB 操作のモックを含む）。
- jquants_client における並列取得時のトークン共有やレート制御の強化（現行はモジュール単位の単純キャッシュと固定間隔スロットリング）。
- pipeline.run_prices_etl 等の戻り値や例外ハンドリングの整備（ETLResult を返す統一インタフェースの全面適用）。
- ロギングフォーマット・監視（Sentry / Prometheus 等）との連携強化。

（以上）