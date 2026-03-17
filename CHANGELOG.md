# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-03-17

### Added
- 基本パッケージの初期実装を追加
  - パッケージ名: kabusys（__version__ = 0.1.0）
  - パッケージ公開モジュール: data, strategy, execution, monitoring

- 環境設定管理（kabusys.config）
  - .env / .env.local および OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に __file__ から上位を検索してプロジェクトルートを特定（CWD に依存しない）。
  - .env パーサ実装:
    - export KEY=val 形式に対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの値でのインラインコメント処理（'#' 前の空白でコメント判定）
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - ロード順序: OS 環境変数 > .env.local（override）> .env（未設定時にのみセット）
  - Settings クラスを提供し、主要設定のプロパティを型安全に取得:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティ
    - 値検証（env 値の許容値チェック、LOG_LEVEL の検証等）
    - helper メソッド: is_live / is_paper / is_dev

- J-Quants クライアント（kabusys.data.jquants_client）
  - API 呼び出しのユーティリティを実装（_request）
    - レート制限（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx の再試行）
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ
    - ページネーション対応（pagination_key を利用）
    - JSON デコードエラーハンドリング
  - 認証ヘルパ: get_id_token（リフレッシュトークン -> idToken）
  - データ取得関数:
    - fetch_daily_quotes（OHLCV 日足、ページネーション対応）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等性を保証する ON CONFLICT を使用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 値変換ユーティリティ: _to_float, _to_int（文字列/NULL の安全な変換処理）
  - モジュールレベルで ID トークンをキャッシュしてページネーション間で共有

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからのニュース収集機能を実装
    - デフォルト RSS ソース（例: Yahoo Finance の business RSS）
    - fetch_rss: RSS 取得 → XML パース → 記事抽出（title, description/content:encoded, link, pubDate）
    - preprocess_text: URL 除去、空白正規化
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保（utm_* 等のトラッキングパラメータを除去して正規化）
    - RSS の XML パースに defusedxml を利用（XML Bomb 等の防御）
    - HTTP リダイレクト検査と SSRF 対策:
      - リダイレクト先のスキーム検証（http/https のみ許可）
      - リダイレクト先がプライベートアドレス（ループバック/リンクローカル/プライベート）でないか検査
      - 初期 URL のホストに対する事前プライベート判定
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）によるメモリDoS 対策、gzip 解凍後のサイズチェック
    - fetch_rss はエラーを局所化し、ソース単位で失敗を扱える設計
  - DuckDB への保存機能:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を使い、実際に挿入された ID リストを返す。チャンク分割と単一トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT でスキップ）し、挿入件数を正確に返す。
  - 銘柄コード抽出:
    - extract_stock_codes: テキスト中の4桁数字候補を検出し、known_codes に含まれるもののみ返す（重複除去）
  - 統合収集ジョブ:
    - run_news_collection: 複数ソースを巡回し fetch → 保存 → 銘柄紐付け を実行。各ソースは個別にエラーハンドリング。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）+ Execution 層のテーブル群を実装
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・制約・PRIMARY KEY・外部キー・CHECK 制約を定義
  - 頻出クエリを考慮したインデックスを作成
  - init_schema(db_path) でディレクトリ作成・DDL 実行して初期化（冪等）、get_connection() で接続取得

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETLResult dataclass による実行結果・品質チェック結果の集約
  - 差分更新のためのヘルパ関数:
    - _table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date
    - _adjust_to_trading_day: 非営業日の場合に直近の営業日に調整（market_calendar に依存、未取得時はフォールバック）
  - run_prices_etl: 株価差分ETL（最終取得日から backfill_days を考慮して差分取得 → 保存）
    - デフォルト backfill_days = 3、最小取得開始日 _MIN_DATA_DATE = 2017-01-01
    - id_token を注入可能にしてテスト容易性を確保

### Security
- RSS/HTTP 関連のセキュリティ対策を多数導入
  - defusedxml による XML パース（XML Bomb の防御）
  - URL スキーム検証（http/https のみ）
  - リダイレクト先のプライベートアドレス判定（SSRF 対策）
  - 受信サイズ上限と gzip 解凍後のサイズチェック（メモリ DoS 対策）

### Reliability / Testing
- ネットワーク・API 呼び出しでリトライ・バックオフ実装（ネットワーク瞬断や 429 対応）
- レート制限をモジュールで管理し、J-Quants のレート制限 (120 req/min) を順守
- _urlopen や id_token の注入によりテスト時にモックしやすい設計
- DuckDB への保存処理はトランザクションでまとめ、INSERT ... RETURNING / ON CONFLICT を活用して冪等性を確保

### Notes / Known issues
- run_prices_etl の戻り値注記:
  - run_prices_etl は (取得レコード数, 保存レコード数) を返す設計だが、現状の実装末尾で "return len(records)," のように単一要素のタプルしか返していない個所が確認できます（型アノテーションと実際の戻り値が不整合）。この点は今後修正が必要です。
- data.strategy, data.execution, monitoring 等のモジュールはパッケージに含まれるが、このリリースでは各 __init__ のみで詳細実装は今後の追加を想定。

### Migration
- 既存データベースを利用する場合は init_schema() を用いてスキーマが作成されることを想定。既存の DuckDB ファイルを使用する際はスキーマの互換性に注意してください。

---

貢献: 初期実装（主要コンポーネントの骨格と重要な処理/セキュリティ対策を実装）