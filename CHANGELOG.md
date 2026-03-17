# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトの初期リリースを記録しています。

全般: バージョンは src/kabusys/__init__.py の __version__ に合わせて 0.1.0 としています。

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの骨格を実装。
  - パッケージ公開用の基本モジュール構成を追加（kabusys, data, strategy, execution, monitoring）。
- 環境設定管理（kabusys.config）
  - .env/.env.local または OS 環境変数から設定を自動読み込みする仕組みを実装。
  - 自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .git または pyproject.toml を基準にプロジェクトルートを特定し、CWD に依存しない読み込みを実現。
  - .env 行パーサを実装（export プレフィックス、クォート文字列、インラインコメント対応）。
  - 必須環境変数取得ヘルパー（_require）と Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境・ログレベル検証含む）。
  - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティおよび JSON レスポンス処理を実装。
  - レート制限（120 req/min）を固定間隔スロットリングで強制する RateLimiter を実装。
  - 冪等性を考慮した保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。DuckDB へ ON CONFLICT DO UPDATE を利用して重複を排除。
  - ページネーション対応の取得関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。
  - リトライロジック（指数バックオフ、最大 3 回。408/429/5xx のリトライ、429 では Retry-After 優先）を導入。
  - 401 受信時はリフレッシュトークンで自動的に id_token を再取得して 1 回リトライ（無限再帰防止の allow_refresh フラグ）。
  - id_token のモジュールレベルキャッシュを追加し、ページネーション間でトークンを共有。
  - 取得時に fetched_at を UTC ISO8601（Z）で記録し、Look-ahead Bias 対策を考慮。
  - 型変換ユーティリティ（_to_float, _to_int）を実装（安全な変換と空値処理）。
- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからのニュース収集と前処理パイプラインを実装。
  - トラッキングパラメータ除去・URL 正規化（_normalize_url）と、正規化 URL に基づく記事 ID（SHA-256 先頭32文字）生成を実装。
  - defusedxml を用いた安全な XML パース（XML Bomb 等に対する防御）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - プライベート/ループバック/リンクローカル/マルチキャストアドレスの検出とブロック（DNS 解決含む）。
    - リダイレクト時にスキーム・ホストを検査するカスタムリダイレクトハンドラを実装。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）チェック、gzip 解凍時のサイズ再チェック（Gzip bomb 対策）。
  - RSS 解析時のフォールバックロジック（channel/item がない場合の探索）。
  - 前処理（URL 除去・空白正規化）ユーティリティ（preprocess_text）。
  - DuckDB への保存:
    - save_raw_news: チャンク分割・トランザクション・INSERT ... ON CONFLICT DO NOTHING RETURNING を使って実際に挿入された記事IDリストを返す。
    - save_news_symbols / _save_news_symbols_bulk: (news_id, code) の紐付けをチャンク & トランザクションで保存し、実際に挿入された件数を返す。
  - 銘柄コード抽出（四桁数字）と run_news_collection による複数ソースの一括収集ジョブを実装。
  - デフォルト RSS ソースに Yahoo Finance のカテゴリフィードを追加（DEFAULT_RSS_SOURCES）。
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層（＋実行層）に対応したテーブル DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw Layer。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed Layer。
  - features, ai_scores を Feature Layer に定義。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution Layer を定義。
  - 頻出クエリ向けのインデックスも作成。
  - init_schema(db_path) により、親ディレクトリの自動作成と DDL の冪等実行を提供。get_connection() で既存 DB へ接続できる。
- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass を実装（ETL 実行結果の集約、品質問題の構造化、has_errors, has_quality_errors, to_dict を提供）。
  - 差分更新ヘルパー:
    - テーブル存在チェック、最大日付取得ヘルパー（_table_exists, _get_max_date）。
    - raw_prices / raw_financials / market_calendar の最終取得日取得関数。
    - 市場カレンダーを参照した営業日調整ロジック（_adjust_to_trading_day）。
  - run_prices_etl の差分更新ロジック実装（最終取得日からの backfill をサポート、API 取得→保存のフロー）。
  - ETL の設計方針:
    - 差分のみ取得、backfill_days による後出し修正吸収、品質チェックは収集を継続しつつ報告する方式。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- RSS XML パースに defusedxml を利用し XML 関連攻撃への耐性を確保。
- RSS フェッチでの SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト時の検査）。
- HTTP レスポンスサイズと gzip 解凍後サイズの検査によりメモリ DoS / zip bomb を軽減。

### Notes / Implementation details
- J-Quants の rate-limit は固定間隔スロットリングで実装しており、厳密な分散環境下での総合制御は別途考慮が必要です。
- save_* 系関数は DuckDB の ON CONFLICT を利用して冪等にデータ更新します。fetched_at は UTC で記録されます。
- news_collector の ID 生成は URL 正規化後の SHA-256（先頭 32 文字）を使用しており、utm_* 等のトラッキングパラメータは除去されます。
- pipeline の品質チェックモジュール（kabusys.data.quality）は参照されていますが、本変更履歴では実装の詳細は含まれていません（コードベース参照）。
- run_prices_etl 等の ETL ジョブは引数で id_token を注入可能にし、テスト容易性を考慮しています。
- SQLite 用のパス設定（SQLITE_PATH）や Slack 関連設定は Settings で必須値として扱います。未設定時は ValueError を送出します。

今後の改善候補（非網羅）
- 分散実行環境やマルチプロセスでのレート制御強化（中央化トークンバケット等）。
- API レスポンススキーマの厳密バリデーション（pydantic 等の導入）。
- ニュース記事の言語処理（形態素解析やエンティティ抽出）を追加して銘柄紐付け精度を向上。
- ETL のジョブスケジューリング・監視機能の実装（monitoring モジュールの拡充）。

参考: ソースコードは src/kabusys 以下に実装されています。