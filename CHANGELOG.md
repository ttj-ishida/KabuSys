CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。
このファイルはパッケージ版 v0.1.0 に基づいて作成されています。

[Unreleased]

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py に __version__="0.1.0"、公開サブパッケージ指定（data, strategy, execution, monitoring）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル・ダブルクォートのエスケープ処理、インラインコメント扱いの挙動を考慮。
    - 上書き制御 (override) と保護キー集合 (protected) による既存 OS 環境変数保護。
  - Settings クラスを実装し、プロパティ経由で設定を取得:
    - J-Quants / kabuステーション / Slack / DB パス (DuckDB/SQLite) / システム環境 (KABUSYS_ENV) / ログレベル等を取得。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）とユーティリティプロパティ（is_live, is_paper, is_dev）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティと高レベルの取得関数を追加:
    - fetch_daily_quotes: 株価日足（OHLCV、ページネーション対応）
    - fetch_financial_statements: 財務データ（四半期 BS/PL、ページネーション対応）
    - fetch_market_calendar: JPX マーケットカレンダー取得
  - 認証ヘルパ: get_id_token（リフレッシュトークンから idToken を取得）
  - レート制御: 固定間隔スロットリングで 120 req/min を保証する _RateLimiter を実装。
  - リトライ戦略: 指数バックオフ、最大 3 回、対象ステータスコード (408, 429, >=500) に対する再試行。429 の場合は Retry-After ヘッダを優先。
  - 401 ハンドリング: 401 受信時は id_token を自動リフレッシュして 1 回リトライ（無限再帰防止のため allow_refresh 制御）。
  - ページネーション間で共有するモジュールレベルのトークンキャッシュを実装。
  - DuckDB への保存関数（冪等性を考慮）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE による冪等保存と、PK 欠損行のスキップログ。
  - データ整形ユーティリティ: _to_float, _to_int（安全な型変換ロジック）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードを安全に取得・解析して raw_news / news_symbols に保存する機能を実装。
  - セキュリティ・堅牢化:
    - defusedxml による XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト時のホスト検査（プライベート/ループバック/リンクローカルを拒否）、_SSRFBlockRedirectHandler を利用した事前検査。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10 MB) によるメモリ DoS 対策、Gzip 圧縮後のサイズ検査（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding ヘッダの設定。
  - URL 正規化と記事 ID 生成:
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）削除、スキーム/ホストの小文字化、フラグメント削除、クエリパラメータのソートを行う _normalize_url。
    - 正規化後 URL の SHA-256 を先頭 32 文字で記事 ID を生成。
  - テキスト前処理:
    - URL 除去と空白正規化を行う preprocess_text。
  - DB 保存:
    - save_raw_news: チャンク化したバルク INSERT + RETURNING id を使い、新規挿入された記事 ID リストを返却。1 トランザクションで実行し、失敗時はロールバック。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンク挿入で行い、実際に挿入された件数を返却。
  - 銘柄コード抽出ユーティリティ: extract_stock_codes（4桁数字パターンを known_codes でフィルタ）。
  - 統合収集ジョブ: run_news_collection（複数 RSS ソースから独立して収集し保存、既知銘柄が指定されていれば紐付けを実施）。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）＋Execution 層のテーブル定義を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに必要な制約（PK, CHECK, FOREIGN KEY）を定義。
  - パフォーマンス向けインデックス群を作成する定義を追加。
  - init_schema(db_path) によりファイルパスの親ディレクトリを自動作成し、DDL を冪等的に実行して接続を返却。
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計に基づく差分更新処理の基礎を実装。
  - ETLResult dataclass を導入し、ETL 実行結果（取得件数、保存件数、品質問題、エラー等）を集約可能に。
  - 差分取得ヘルパ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date により raw_* テーブルの最終日を取得。
    - _adjust_to_trading_day により非営業日は直近営業日に調整（market_calendar を利用。未取得時はフォールバック）。
  - run_prices_etl を実装（差分算出、backfill_days による遡り再取得、jquants_client の fetch/save を利用）。
  - 設計上の方針:
    - デフォルトで backfill_days=3（API の後出し修正を吸収するための再取得）。
    - calendar の先読み用定数 _CALENDAR_LOOKAHEAD_DAYS を定義。
    - 品質チェックは quality モジュールへ委譲（quality.QualityIssue を ETLResult に集約）。

Changed
- 初期リリースにつき変更履歴はなし。

Fixed
- 初期リリースにつき修正履歴はなし。

Security
- RSS / HTTP 周りに関する複数のセキュリティ対策を実装:
  - defusedxml を用いた安全な XML パース。
  - SSRF 対策（スキーム検証、プライベート IP/ホストブロック、リダイレクト時検証）。
  - レスポンスサイズと Gzip 解凍後サイズの上限チェック。
  - 外部 API 呼び出しに対するレート制御とリトライ（429 の Retry-After 尊重、401 の安全なトークンリフレッシュ）。

Notes / 今後の作業候補
- strategy, execution, monitoring サブパッケージはパッケージエクスポートに含まれているものの、本リリースに明示的な実装はないか最小化されています。今後これらの実装を追加予定。
- pipeline.run_prices_etl 等は差分更新の流れを実装していますが、品質チェック（quality モジュール）や全体のジョブスケジューリングとの統合テストを推奨します。
- 単体テスト・統合テストの追加、API 呼び出し・DB 操作のモックを用いたテストカバレッジの拡充を推奨します。

署名
- この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時はリリース担当者による確認・追記をお願いします。