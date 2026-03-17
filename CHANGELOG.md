# Changelog

すべての注記は Keep a Changelog の形式に従い、セマンティックバージョニングに基づいています。  

読み方の便宜上、コードベースから推測できる変更点・設計意図を記載しています（実装コメントや定数、関数名・挙動に基づく）。

※ 初期リリース（v0.1.0）はリポジトリに含まれる主要機能の初回実装を示します。

## [Unreleased]
- （現在なし）

## [0.1.0] - 2026-03-17
初期リリース。日本株自動売買プラットフォームの基礎ライブラリを実装。

### Added
- パッケージ基礎
  - パッケージメタ情報: kabusys.__version__ = 0.1.0、および公開モジュール一覧を定義。
- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - .env と .env.local の優先順位制御（.env.local が上書き）、KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロード無効化。
  - .env パーサーでシングル／ダブルクォート、エスケープ、インラインコメント、export プレフィックス等に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等の取得とバリデーションを実装。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - ベース実装: token の取得（get_id_token）、株価日足・財務データ・市場カレンダーの取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - レート制御: 固定間隔の RateLimiter を実装し、デフォルトで 120 req/min を順守（最小間隔を自動待機）。
  - リトライロジック: ネットワークエラーや 408/429/5xx を対象に指数バックオフで最大3回リトライ。
  - 401 Unauthorized 受信時にリフレッシュトークンで id_token を自動更新して最大1回再試行（無限再帰回避）。
  - ページネーション対応（pagination_key による続き取得）とモジュール単位のトークンキャッシュ。
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。fetched_at を UTC ISO 時刻で記録、ON CONFLICT DO UPDATE による重複排除。
  - 型変換ユーティリティ（_to_float / _to_int）で不正データを安全に扱う。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集の実装（fetch_rss）と記事保存（save_raw_news）、記事と銘柄の紐付け（save_news_symbols / _save_news_symbols_bulk）。
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 対策）。
    - URL スキーム検証（http/https のみ許可）とプライベートアドレス判定による SSRF 防止。リダイレクト時も検証を行うカスタムハンドラを実装。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - 受信時の User-Agent 指定と Content-Length の事前チェック。
  - 冪等性・同一性:
    - 記事ID を URL 正規化後の SHA-256（先頭32文字）で生成し追跡可能に。
    - URL 正規化でトラッキングパラメータ（utm_* 等）を除去、クエリをソート、フラグメント削除。
  - 前処理:
    - テキストから URL を除去し空白正規化を行う preprocess_text。
    - RSS pubDate のパース（タイムゾーン調整）とフォールバック。
  - DB 保存はチャンク化して一つのトランザクションで実行し、INSERT ... RETURNING により実際に挿入された件数を返す。
  - 銘柄抽出: 正規表現で4桁銘柄コードを抽出し既知コードセットでフィルタ（extract_stock_codes）。
  - 統合ジョブ run_news_collection を提供し、複数ソースの個別エラーハンドリング・新規保存件数の集計・銘柄紐付けの一括保存を行う。
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の各レイヤーに対応するテーブル定義（DDL）を実装。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores など Feature テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等 Execution テーブル。
  - 適切な制約（PRIMARY KEY / CHECK / FOREIGN KEY）と頻出クエリ向けのインデックスを定義。
  - init_schema(db_path) でディレクトリ自動作成後に DDL とインデックスを順次実行して初期化するユーティリティを提供。
  - get_connection(db_path) で既存 DB 接続を返す。
- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラスを導入し、取得数・保存数・品質問題リスト・エラー一覧等を集約。
  - 差分更新ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）とテーブル存在チェック。
  - 市場カレンダーを考慮した営業日調整ヘルパー（_adjust_to_trading_day）。
  - run_prices_etl の初期実装: 差分取得ロジック（最終取得日から backfill_days を遡る）、J-Quants クライアント呼び出し、保存およびログ出力のフローを実装。
  - 初期データ開始日（_MIN_DATA_DATE = 2017-01-01）とデフォルトバックフィル日（3日）、カレンダー先読み日数定義。

### Changed
- （初回実装のため該当なし）

### Fixed
- （初回実装のため該当なし）

### Security
- RSS パーサーに defusedxml、SSRF 対策（スキーム検証・プライベートアドレス拒否・リダイレクト検査）を導入。
- HTTP レスポンスサイズの上限と gzip 解凍後の上限チェックを実装（メモリ DoS / Gzip bomb 対策）。
- .env 読み込みで OS 環境変数保護機能（protected set）を導入し、意図しない上書きを防止。

### Notes / Implementation details
- J-Quants API クライアントはページネーション対応だが、API 側の pagination_key を使用する実装であるため、ページネーション仕様の変更があると影響を受ける可能性がある。
- DuckDB への保存は SQL の ON CONFLICT（UPSERT）に依存しているため、スキーマの主キーや一貫性が重要。
- ETL の品質チェックは quality モジュールに依存する設計（quality.QualityIssue を扱う）だが、quality モジュールは別途実装される想定。
- run_news_collection はソース単位で失敗を許容し他ソースの処理を継続する堅牢な設計。

### Breaking Changes
- 初版のためなし。

---
今後の予定（想定）
- quality モジュールの実装と ETL 内統合（データ品質チェックを収集し ETLResult に反映）。
- execution（発注）レイヤーの外部 API 統合（kabuステーションやブローカ API）およびモニタリング機能の実装。
- ユニットテストの充実化（ネットワーク I/O のモック、DuckDB のインメモリテスト等）。
- ドキュメント（DataPlatform.md、API 仕様、運用ガイド）の追加。

ご了承ください：上記変更履歴は提示されたコードの内容から推測して作成しています。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。