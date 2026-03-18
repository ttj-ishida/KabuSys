# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
リリース日付はソースコード解析時点（2026-03-18）を用いています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」のコアモジュール群を追加しました。主な追加内容は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート: data, strategy, execution, monitoring を公開（src/kabusys/__init__.py）。

- 環境変数／設定管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート判定は .git または pyproject.toml 基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - .env ファイルの堅牢なパース処理実装（export 形式、クォート文字処理、行内コメント処理等に対応）。
  - Settings クラスを導入し、以下の設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
  - is_live / is_paper / is_dev の便宜プロパティを提供。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 基本機能: 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装。
  - レート制限を尊重する固定間隔スロットリング実装（120 req/min、_RateLimiter）。
  - リトライロジックを実装（最大 3 回、指数バックオフ、HTTP 408/429/5xx を対象）。
  - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライする機能を搭載（無限再帰制御あり）。
  - ページネーション対応（pagination_key の処理）。
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes: raw_prices へ保存（ON CONFLICT DO UPDATE）、fetched_at を UTC ISO 形式で記録。
    - save_financial_statements: raw_financials へ保存（ON CONFLICT DO UPDATE）。
    - save_market_calendar: market_calendar へ保存（ON CONFLICT DO UPDATE）、HolidayDivision の解釈を明記。
  - 型変換ユーティリティ (_to_float / _to_int) を実装し、空値や不正値に対する寛容な処理を行う。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得して raw_news テーブルへ保存する一連の実装。
  - セキュリティ・堅牢性設計:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証、ホストのプライベートアドレス判定（IP直接判定と DNS 解決結果の検査）、リダイレクトハンドラによる検査。
    - 最大受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後のサイズ検査。
    - 許可されないスキームやプライベートアドレスを早期に拒否。
  - 記事 ID 生成: URL を正規化して（トラッキングパラメータ除去、クエリソート、フラグメント削除）SHA-256 の先頭32文字を使用し冪等性を保証。
  - テキスト前処理: URL 除去・空白正規化。
  - DB 保存の実装:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING と RETURNING を使って新規挿入 ID を正確に取得、チャンク分割してトランザクションで保存。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンク単位でトランザクション処理、ON CONFLICT DO NOTHING。
  - 銘柄コード抽出ユーティリティ extract_stock_codes を実装（4桁数字、known_codes に基づくフィルタ、重複除去）。
  - run_news_collection: 複数 RSS ソースを順次処理、ソース単位でエラーハンドリングを行い継続する設計。既定の RSS ソース辞書を提供（DEFAULT_RSS_SOURCES）。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層を含む包括的な DDL を実装。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 型・制約（CHECK、PRIMARY KEY、FOREIGN KEY）と実用的なインデックスを定義。
  - init_schema(db_path): ディレクトリ自動作成、すべての DDL とインデックスを実行して DuckDB 接続を返す（冪等）。
  - get_connection(db_path): 既存 DB への接続（スキーマ初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL の設計指針と差分更新ロジックを実装。
  - 定数:
    - _MIN_DATA_DATE = 2017-01-01（初回ロード基準）
    - _CALENDAR_LOOKAHEAD_DAYS = 90
    - _DEFAULT_BACKFILL_DAYS = 3（デフォルトで直近 N 日を再取得して後出し修正に対応）
  - ETLResult dataclass を導入: ETL 実行結果、品質問題・エラーの集約、has_errors / has_quality_errors / to_dict を実装。
  - DB ヘルパー:
    - _table_exists, _get_max_date を実装してテーブル未作成時の安全な振る舞いを提供。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
  - 市場カレンダーヘルパー _adjust_to_trading_day を実装（非営業日の調整: 最大 30 日遡る）。
  - run_prices_etl を実装（差分取得、backfill に基づく date_from の算出、fetch->save の流れ）。品質チェックモジュール quality との連携を想定。

### Security
- RSS 取得周りで SSRF・XML 注入対策を導入（defusedxml、ホスト判定、リダイレクト検査、スキーム検証、受信サイズ制限）。
- .env 読み込みはプロジェクトルート基準で行い、OS 環境変数を保護する仕組み（protected set）を用意。

### Documentation / Notes
- 各モジュールに docstring と設計方針を記載し、挙動・例外・設計上の注意点（例: id_token の自動リフレッシュは 1 回のみ）を明文化。
- DuckDB の INSERT は可能な限り冪等に設計（ON CONFLICT DO UPDATE / DO NOTHING、RETURNING の利用）。
- パッケージ全体でテスト容易性を考慮（id_token 注入可能、_urlopen をモック差し替え可能など）。

### Removed
- なし

### Changed
- なし

### Fixed
- なし

補足:
- 本 CHANGELOG はソースコードからの機能推測に基づいて作成しています。実際のリリースノートとして使用する場合は、実装者による確認・必要に応じた修正を推奨します。