# Changelog

すべての注目すべき変更点をここに記録します。これは Keep a Changelog の形式に準拠しています。

フォーマット: [version] - YYYY-MM-DD

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17
初期公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは `0.1.0`。
  - パッケージ公開用のトップレベル __all__ と簡単なパッケージ説明を実装。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local からの自動環境変数読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して検出）。
  - 読み込み優先順位: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ等に対応）。
  - 環境変数取得ヘルパ `_require` と Settings クラスを提供。J-Quants、kabuステーション、Slack、DB パス、実行環境（development/paper_trading/live）やログレベル検証等のプロパティを用意。
  - DB パスは Path 型で扱う（expanduser 対応）。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - API レート制限制御（固定間隔スロットリング）を実装（120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）を実装。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時にリフレッシュトークンから id_token を自動リフレッシュして再試行（無限再帰防止の仕組みあり）。
  - ページネーション対応（pagination_key を利用して全ページ取得）。
  - データ取得関数を提供:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB へ冪等保存する save_* 関数を実装（INSERT ... ON CONFLICT DO UPDATE を利用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 取得時刻（fetched_at）を UTC で記録して look-ahead bias のトレーサビリティを確保。
  - 型変換ユーティリティ `_to_float`, `_to_int` を実装（安全な変換・不正データは None）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を取得し raw_news / news_symbols に保存するエンドツーエンドの処理を実装。
  - 記事 ID は URL 正規化後の SHA-256 の先頭 32 文字で生成し、トラッキングパラメータを除去して冪等性を保証。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
  - RSS 取得時の安全対策:
    - defusedxml による安全な XML パース（XML Bomb 等の防御）。
    - SSRF 対策: リダイレクト先のスキーム検査とプライベートアドレス検出（DNS 解決して A/AAAA をチェック）。初期 URL も事前検査。
    - レスポンスサイズ上限（10 MB）での事前検査と読み取り超過検出、gzip 解凍後の再検査（Gzip bomb 対策）。
    - HTTP ヘッダによる Content-Length の事前検査（不正値は無視）。
    - 非 http/https スキームや不正な link 要素はスキップ。
  - テキスト前処理（URL 除去・空白正規化）と pubDate の安全なパース（RFC2822 → UTC naive に変換、失敗時は現在時刻で代替）。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING を用いたチャンク挿入（トランザクション、重複は ON CONFLICT DO NOTHING、実際に挿入された ID を返す）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク単位で安全に保存（重複除去、RETURNING による実挿入数算出）。
  - 銘柄コード抽出ユーティリティ extract_stock_codes（本文中の 4 桁数列を既知銘柄セットでフィルタ、重複除去）。
  - run_news_collection: 複数 RSS ソースの収集を統合するジョブ（各ソースは独立してエラー処理、known_codes があれば銘柄紐付け一括実行）。

- DuckDB スキーマ定義 / 初期化 (kabusys.data.schema)
  - DataPlatform 構成に基づくスキーマ定義を実装（Raw / Processed / Feature / Execution 層）。
  - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など。
  - 適切な制約、チェック制約、主キー、外部キーを定義。
  - 頻出クエリに対応したインデックスを定義。
  - init_schema(db_path) でディレクトリ作成 → 全 DDL とインデックスを実行して接続を返す（冪等）。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult データクラスを導入（取得数、保存数、品質チェック結果、エラー一覧 等を格納、辞書出力可）。
  - 差分取得用ユーティリティ:
    - テーブル存在検査 `_table_exists`
    - 日付最大値取得 `_get_max_date`
    - 市場日調整 `_adjust_to_trading_day`（非営業日の場合は過去方向で最近の営業日に調整）
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - run_prices_etl の基礎を実装（差分更新ロジック、backfill_days による再取得、J-Quants から取得して保存）。（価格 ETL の主要フローを提供）

### Security
- news_collector における SSRF 対策を実装（リダイレクト時の検査、事前ホスト検査、非 http/https スキーム排除、プライベートアドレス判定）。
- RSS パースに defusedxml を使用して XML 関連の攻撃を緩和。
- レスポンスサイズ上限および gzip 解凍後検査により、メモリ DoS / Gzip bomb を軽減。

### Notes / Implementation details
- 多くの DB 操作は DuckDB のプレースホルダとトランザクションを用いて実装（チャンク処理、INSERT ... RETURNING による正確な挿入数取得）。
- jquants_client はモジュールレベルの id_token キャッシュを保持し、ページネーション間で使い回し・必要時リフレッシュを行う。
- .env パーサはクォート内部のバックスラッシュエスケープやインラインコメントの扱い等、実用的なケースに対応。
- strategy / execution パッケージの __init__ はプレースホルダとして存在（今後の実装対象）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。