CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠します。  
リリース日はソースコードの現在バージョン（src/kabusys/__init__.py の __version__）に基づいて記載しています。

Unreleased
----------

- なし

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初期リリース:
  - パッケージ名: kabusys
  - バージョン 0.1.0

- 基本構成 / コア:
  - src/kabusys/__init__.py によるパッケージ公開（data, strategy, execution, monitoring）。
  - strategy, execution, monitoring パッケージ（初期プレースホルダ）。

- 設定・環境変数管理 (src/kabusys/config.py):
  - .env / .env.local からの自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env ローダーは OS 環境変数を保護（既存キーを protected として扱う）し、.env.local が優先される。
  - .env のパースは export KEY=val, シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
  - Settings クラスで主要設定をプロパティ化:
    - J-Quants / kabu API / Slack / DB パス（duckdb / sqlite）等の必須設定を取得する _require()。
    - KABUSYS_ENV の検証（development, paper_trading, live）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev ヘルパー。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py):
  - API ベース URL、トークン取得（get_id_token）と利用。
  - レート制限制御: 固定間隔スロットリング (120 req/min) を _RateLimiter で実装。
  - 冪等取得/保存:
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）。
    - save_daily_quotes / save_financial_statements / save_market_calendar: DuckDB への保存は ON CONFLICT DO UPDATE により冪等化。
  - リトライとエラー処理:
    - ネットワークエラー・HTTPエラーに対する指数バックオフリトライ（最大 3 回）。
    - 429 の場合は Retry-After ヘッダ優先。
    - 401 受信時はトークン自動リフレッシュして 1 回リトライ（再帰防止ロジックあり）。
  - Look-ahead Bias 対策: 保存時に fetched_at を UTC ISO タイムスタンプで記録。
  - ユーティリティ関数: _to_float / _to_int（安全な変換と不正値の扱い）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py):
  - RSS フィードから記事収集と DuckDB への保存を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML bomb 等の防止）。
    - SSRF 対策: リダイレクト時にスキーム/ホスト検証を行うカスタムハンドラ (_SSRFBlockRedirectHandler) と事前ホスト検証。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズ検査（Gzip-bomb 対策）。
    - 不正スキームやプライベートIPへのアクセスを拒否。
  - 正規化と冪等性:
    - URL 正規化 (クエリのトラッキングパラメータ除去、ソート、フラグメント削除、スキーム/ホスト小文字化)。
    - 記事 ID は正規化 URL の SHA-256 の先頭32文字で生成し冪等性を保証。
  - テキスト前処理: URL 除去、余分な空白正規化。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を用い、実際に新規挿入された記事IDを返却（チャンク化、トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けをバルクで保存（RETURNING で挿入件数取得、トランザクション）。
  - 銘柄抽出: テキストから4桁の銘柄コード候補を抽出し、known_codes による検証でフィルタ（重複除去）。
  - run_news_collection: 複数 RSS ソースの一括収集、個別ソース単位でエラーハンドリング、既知銘柄との紐付けをまとめて実行。

- スキーマ定義 / DuckDB 初期化 (src/kabusys/data/schema.py):
  - DataSchema.md に基づく多層スキーマを定義・初期化する init_schema():
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック・型指定を多用してデータ整合性を確保（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）。
  - 頻出クエリ向けにインデックスを作成。
  - get_connection: 既存 DuckDB への接続取得（初回は init_schema を推奨）。

- ETL / パイプライン基盤 (src/kabusys/data/pipeline.py):
  - ETL フローの骨組みとユーティリティを実装:
    - 差分更新のための最終取得日取得関数（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダー補正ヘルパー (_adjust_to_trading_day)。
    - ETLResult データクラス（品質問題とエラーの集計、シリアライズ用メソッド to_dict）。
    - run_prices_etl: 株価差分 ETL の実装方針（差分取得、backfill_days デフォルト 3、_MIN_DATA_DATE、保存とログ）。
  - 品質チェックとの連携ポイント（quality モジュール参照）：収集は継続しつつ、品質問題を収集して呼び出し元に委ねる設計。

Security
- ニュース収集と XML パース周りで複数のセキュリティ対策を導入:
  - defusedxml による安全な XML パース。
  - SSRF 対策（ホストプライベート判定、リダイレクト先事前検査）。
  - レスポンスサイズ上限と gzip 解凍後の再チェック。
  - URL 正規化によりトラッキングパラメータを削除してノイズを低減。

Known issues / Notes
- strategy, execution, monitoring パッケージは現在プレースホルダ（実装は今後）。
- pipeline.run_prices_etl の実装は差分取得と保存機能を含むが、ファイル断片の受領により提供コードの末尾が途切れているため、追加の結合ロジックや戻り値処理が今後必要な可能性があります（コードベースの完全実装を参照してください）。
- quality モジュールの実装は本差分では含まれておらず、品質チェックの具体的なルールは別途実装/連携が必要。

その他
- 本リリースは初期版として、データ取得・保存・ニュース収集・スキーマ定義・基本的な ETL ヘルパーに重点を置いています。今後は戦略ロジック、実行（発注）処理、監視・アラート機能、追加品質チェックの充実を予定しています。