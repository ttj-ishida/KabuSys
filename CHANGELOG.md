# Changelog

すべての変更点は Keep a Changelog の形式に従って記載しています。  
慣用的に重大度の高い変更（破壊的変更）は Breaking changes セクションに記載します。

## [0.1.0] - 2026-03-17

### Added
- 初回リリース。日本株自動売買システム「KabuSys」の基礎モジュールを追加。
- パッケージ公開情報
  - パッケージ名: kabusys
  - __version__ = "0.1.0"
  - パッケージ公開 API: data, strategy, execution, monitoring（__all__ に定義）

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ローダを実装。プロジェクトルートは .git または pyproject.toml を基準に探索するため CWD に依存しない。
  - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パース機能を強化:
    - "export KEY=val" 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの扱い（クォートあり/なしのケースに対応）
  - 必須環境変数取得ヘルパ (_require) と Settings クラスを提供（J-Quants, kabuステーション, Slack, DB パスなどのプロパティを用意）
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の妥当性チェックを実装

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得機能を実装
  - API レート制限対策: 固定間隔スロットリング（120 req/min に相当）を実装する RateLimiter を導入
  - リトライ戦略: 指数バックオフ、最大 3 回。リトライ対象に 408/429/5xx を含む。429 の場合は Retry-After を優先。
  - 401 Unauthorized 受信時のトークン自動リフレッシュ（1 回のみ）と再試行ロジックを実装。ページネーション間で使うためのモジュールレベルの id_token キャッシュを導入
  - JSON レスポンスの堅牢なデコード（デコード失敗時は明確なエラー）
  - データ取得関数:
    - fetch_daily_quotes（ページネーション対応）
    - fetch_financial_statements（ページネーション対応）
    - fetch_market_calendar
  - DuckDB への保存関数（冪等性を確保）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE による上書きを実装。fetched_at は UTC ISO 形式で保存
    - save_financial_statements: raw_financials テーブルへ冪等保存
    - save_market_calendar: market_calendar テーブルへ冪等保存。HolidayDivision の意味付けを実装
  - 値変換ユーティリティ: _to_float, _to_int（文字列の "1.0" を適切に int に変換する等）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュースを収集し raw_news / news_symbols に保存するエンドツーエンド実装
  - 設計要点:
    - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字（冪等性確保）
    - URL 正規化: スキーム・ホストの小文字化、トラッキングパラメータ除去（utm_, fbclid, gclid, ref_, _ga 等）、フラグメント除去、クエリソート
    - defusedxml を利用した XML パース（XML Bomb 等へ対策）
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベート/ループバック/リンクローカル/マルチキャスト判定、リダイレクト毎の事前検査用 RedirectHandler を導入
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ再チェック（Gzip Bomb 対策）
    - 受信時の User-Agent 指定、Accept-Encoding: gzip 支持
    - テキスト前処理（URL 除去、空白正規化）
  - 公開関数:
    - fetch_rss: RSS を取得して NewsArticle リストを返す（エラーは個別ソースでハンドリング）
    - save_raw_news: INSERT ... RETURNING による新規挿入 ID 取得、チャンク挿入 + 単一トランザクション
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けをチャンク化して保存（ON CONFLICT DO NOTHING + RETURNING で実挿入数を返す）
    - extract_stock_codes: テキストから 4 桁銘柄コードを抽出（known_codes によるフィルタリング、重複除去）
    - run_news_collection: 複数ソースを順次処理し新規保存数を集計。1 ソース失敗しても他のソースは継続

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）および Execution レイヤのテーブル定義を実装
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック・外部キー・PRIMARY KEY を定義してデータ整合性を担保
  - 標準的なクエリパターン向けのインデックスを作成
  - init_schema(db_path): ディレクトリ自動作成、DDL とインデックスを実行（冪等）
  - get_connection(db_path): 既存 DB への接続取得（スキーマ初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - ETL 設計:
    - 差分更新（DB の最終取得日を参照して必要な分だけ取得）
    - backfill_days（デフォルト 3 日）で後出し修正を吸収
    - market calendar の先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）
    - 品質チェックモジュールとの連携（quality モジュール想定）により欠損・スパイク等を検出。品質問題は集約して呼び出し元へ返すが、可能な限り収集は継続する設計
  - ETLResult データクラスを導入し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を表現
  - ヘルパ関数:
    - _table_exists, _get_max_date
    - _adjust_to_trading_day（非営業日の調整、最大 30 日遡り）
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
  - run_prices_etl の骨格を実装（差分算出、fetch -> save の流れ）

### Security
- ニュース収集で SSRF/内部アドレスアクセス対策を強化:
  - URL スキーム検証（http/https のみ）
  - リダイレクト先のスキーム/ホスト検査（_SSRFBlockRedirectHandler）
  - ホスト名は DNS 解決して A/AAAA レコードの IP を検査（解決失敗時は保守的に非プライベート扱い）
  - レスポンスサイズ制限（10MB）と gzip 解凍後の再チェックを導入して DoS/Bomb 攻撃に対処
- defusedxml を使用して XML パースに伴う脆弱性を緩和

### Notes / Implementation details
- J-Quants クライアントは内部で rate limiting と retry を行うため、高頻度呼び出しを安全に行える想定。ただしアプリ側でも呼び出し頻度を考慮すること。
- DuckDB への保存は基本的に冪等（ON CONFLICT）で実装しているため、再実行や部分的リトライに強い。
- News の記事 ID は正規化 URL のハッシュで生成しているため、トラッキングパラメータの有無による重複登録を抑止。
- settings で定義された必須環境変数が未設定の場合は ValueError を投げるため、起動前に環境変数の準備が必要。

### Breaking Changes
- 初回リリースのため該当なし。

### Known issues / TODO
- pipeline.run_prices_etl の戻り値が実装途中（末尾がカンマで切れている等）であり、完全な ETL フロー（品質チェック呼び出し・calendar/backfill の統合・例外ハンドリングの細部）は今後整備予定。
- strategy / execution / monitoring パッケージの公開はあるが、具体的な戦略・発注ロジック・監視機能はこのリリースでは実装のスケルトンまたは未実装の可能性あり。今後のリリースで追加予定。

--- 

今後のリリースでは、ETL の完全実装、quality モジュールとの統合、実行（execution）層の発注連携、監視（monitoring）・通知機能（Slack 連携など）の拡充を予定しています。