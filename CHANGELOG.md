# Changelog

すべての変更は Keep a Changelog の形式に従って記録しています。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 初回リリース

初期機能実装。日本株自動売買システムのコアとなる設定管理、データ取得・保存、ニュース収集、DuckDBスキーマ、ETLパイプラインの基本実装を含みます。

### Added
- パッケージ初期化
  - kabusys パッケージの基本 __init__（バージョン 0.1.0、主要サブパッケージ公開: data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準に探索）。
  - .env/.env.local の自動読み込み機能を追加（OS 環境変数を保護しつつ .env.local で上書き可能）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env の行パーサーを実装（export プレフィックス、クォート、エスケープ、インラインコメント対応）。
  - 必須環境変数取得ヘルパー _require と Settings クラスを実装（各種必須トークン、DB パス、ログレベル・環境のバリデーション等を提供）。
  - 環境値のバリデーション（KABUSYS_ENV、LOG_LEVEL 等）を実装。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装。
  - レートリミッタ実装（固定間隔スロットリング、120 req/min に準拠）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）を実装。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回のみ）を実装。
  - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）。
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止。
  - DuckDB へ冪等に保存する save_* 関数を実装（INSERT ... ON CONFLICT DO UPDATE を利用）。
  - 型変換ユーティリティ（_to_float/_to_int）で不正値を安全に扱う。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集する fetch_rss を実装（デフォルトソースに Yahoo Finance を追加）。
  - セキュリティ対策:
    - defusedxml を利用した XML パース（XML Bomb 等対策）。
    - SSRF 対策：URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルでないことを検査、リダイレクト時にも検証。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリDoS対策、gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリソート）と記事ID生成（正規化 URL の SHA-256 先頭32文字）で冪等性を保証。
  - テキスト前処理（URL 除去、空白正規化）。
  - DuckDB への保存処理を実装:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事IDを返す（1 トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols の一括保存（重複除去、チャンク挿入、INSERT ... RETURNING を利用して実挿入数を取得）。
  - 銘柄コード抽出ロジック（4桁の数字を候補とし、known_codes でフィルタリング）を実装。
  - run_news_collection により複数ソースを順次処理し、失敗したソースはスキップして他ソースは継続する堅牢な集約ジョブを提供。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の各レイヤーに対応するテーブル DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions、processed 層（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）、feature 層（features, ai_scores）、execution 層（signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）を作成。
  - インデックス（検索パターンに基づく）を作成する DDL を含む。
  - init_schema(db_path) でディレクトリ作成からテーブル作成まで行い、冪等的に初期化できる実装。
  - get_connection(db_path) で既存 DB へ接続するユーティリティを提供。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の基本方針に基づく処理フローと設計方針を実装。
  - ETLResult dataclass を実装し、品質チェックの結果やエラー一覧を保持・辞書化できるようにした。
  - スキーマ存在確認・最大日付取得用ユーティリティを実装（_table_exists, _get_max_date）。
  - market_calendar を用いた営業日調整ヘルパー（_adjust_to_trading_day）を実装。
  - 差分更新用ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）を実装。
  - run_prices_etl を実装（最終取得日からの差分取得、自動バックフィル、jquants_client を使った取得と保存、保存件数返却の骨組み）。
    - デフォルトのバックフィル日数は 3 日。
    - 初回ロード時の最小日付は 2017-01-01。
    - 市場カレンダーの先読みデフォルトは 90 日。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Security
- ニュース収集での SSRF / XML インジェクション / Gzip Bomb / 大容量レスポンス対策を実装。
- .env の扱いで OS 環境変数の上書きを保護する仕組みを導入（protected set を利用）。

---

著者: KabuSys 開発チーム  
初回リリース: 0.1.0（このリリースがパッケージのベースラインです）