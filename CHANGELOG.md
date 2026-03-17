# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]

### Added
- ETLパイプラインの基盤（kabusys.data.pipeline）を導入。ETL結果を表す ETLResult dataclass、差分取得・日付調整・テーブル存在チェックなどのユーティリティ関数を追加。
- テストや実行環境で自動 .env 読み込みを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（kabusys.config）。
- モジュールレベルでのログ出力や詳細な例外情報の充実（各モジュールで logger 使用）。

### Fixed / To do
- run_prices_etl の戻り値が不完全（len(records), のみでタプルが期待される箇所が中途になっている）ため、戻り値の整備が必要。現状は開発中／要修正。

---

## [0.1.0] - 2026-03-17

初回リリース。パッケージのコア機能を実装しました。

### Added
- パッケージ初期化
  - `kabusys.__init__` を追加し、主要サブパッケージ（data, strategy, execution, monitoring）をエクスポート。

- 設定管理（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）を基に自動で .env/.env.local を読み込む機能を実装。
  - .env ファイルパーサを独自実装（export プレフィックス、クォート処理、インラインコメント対応、保護された OS 環境変数の考慮）。
  - 必須環境変数の取得 (`_require`) と、J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供する `Settings` クラス。
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（有効な値のチェック）。

- J-Quants クライアント（kabusys.data.jquants_client）
  - API ベース URL とトークン取得（get_id_token）実装。
  - レート制御（120 req/min の固定間隔スロットリング）を行う `_RateLimiter` を実装。
  - 再試行（指数バックオフ、最大3回）と 401 受信時の自動トークンリフレッシュ処理を実装。
  - ページネーション対応のデータ取得関数を追加：
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB へ冪等に保存する save_* 関数を追加（ON CONFLICT DO UPDATE を利用）：
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 型変換ユーティリティ `_to_float`, `_to_int` を実装し、空値や不正値を安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事取得（fetch_rss）と前処理（preprocess_text）機能を追加。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url, _make_article_id）により冪等性を確保（記事IDは正規化後の SHA-256 の先頭32文字）。
  - SSRF 対策を含む堅牢な HTTP 処理：
    - リダイレクト時にスキーム/ホストを検証するカスタムハンドラ（_SSRFBlockRedirectHandler）。
    - ホストがプライベートアドレスかを判定する `_is_private_host`、およびスキーム検証 `_validate_url_scheme`。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）チェックと gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - defusedxml による XML パース（XML Bomb 等の防止）。
  - DuckDB への保存処理をトランザクション・チャンク単位で実装：
    - save_raw_news（INSERT ... RETURNING を使用して実際に挿入された記事IDを返す）、チャンクサイズ制御。
    - save_news_symbols / _save_news_symbols_bulk（記事と銘柄コードの紐付けを一括挿入、ON CONFLICT で重複スキップ）。
  - テキストから銘柄コード（4桁）を抽出する extract_stock_codes を実装。
  - 複数ソースの統合収集ジョブ run_news_collection を実装（各ソースは独立してエラー処理、既存記事はスキップ）。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataLayer（Raw / Processed / Feature / Execution）に対応するテーブル群の DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores の Feature テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
  - よく使われるクエリ向けのインデックスを複数定義。
  - init_schema(db_path) でディレクトリ作成 → テーブル作成を冪等に実行する機能を提供。
  - get_connection(db_path) で既存 DB に接続するヘルパを提供。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック（最終取得日から未取得分のみを再取得、バックフィル日数で後出し修正を吸収）を実装するための各種ユーティリティ（_get_max_date 等）。
  - run_prices_etl 実装（差分取得 → jq.fetch_daily_quotes → jq.save_daily_quotes の流れ）。backfill_days による再取得制御、最小データ開始日の扱いを実装。

### Changed
- なし（初回リリースのため変更はなし）。

### Security
- RSS パーサに defusedxml を採用し、XML 関連の脆弱性（XML Bomb など）に対処。
- RSS 取得時の SSRF 対策を実装（URL スキーム検証、プライベートホスト判定、リダイレクト検査）。
- HTTP レスポンスの読み取り上限を設け、メモリ DoS・Gzip bomb 対策を実施。
- J-Quants クライアントは認証トークンを明示的に取り扱い、401 受信時には自動でトークンをリフレッシュ（ただし無限再帰回避あり）。

### Performance / Reliability
- API 呼び出しのレート制御（固定スロットリング）と再試行（指数バックオフ）を実装し、外部 API との安定した通信を目指す。
- DB 書き込みはトランザクションおよびチャンク処理で行い、INSERT ... RETURNING による正確な挿入判定を行うことでオーバーヘッドと不整合を低減。
- jquants_client のページネーションで ID トークンをモジュールキャッシュで共有し、ページ間でのトークン再取得を最小化。

### Known Issues
- run_prices_etl の戻り値がファイル末尾の実装で不完全になっている（現状は取得数のみを返す形になっており、保存数など期待される戻り値の構造が満たされていない）。修正が必要。
- モジュールレベルのトークンキャッシュ（_ID_TOKEN_CACHE）はスレッドセーフではないため、マルチスレッド環境での使用時には注意が必要。

### Removed
- なし（初回リリース）。

---

今後の予定（例）
- pipeline の追加 ETL ジョブ（financials, market_calendar の自動差分ETL）を実装。
- テストカバレッジの拡充（特にネットワーク周りと DB トランザクション部分）。
- run_prices_etl の戻り値/エラーハンドリングの改善とドキュメント整備。

（以上）