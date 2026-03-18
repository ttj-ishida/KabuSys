# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」ガイドラインに準拠します。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]
- 今後のリリース向けの未確定の変更点はここに記載します。

## [0.1.0] - 2026-03-18
初回リリース — 日本株自動売買システムの基盤ライブラリを追加。

### Added
- パッケージの基本セットアップ
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - __all__ に data, strategy, execution, monitoring を公開（将来的な拡張を想定）。

- 環境設定/ロード機能（src/kabusys/config.py）
  - .env/.env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - export KEY=val 形式やクォート・コメントの取り扱いに対応した行パーサー実装。
  - 読み込みの上書き制御（override と protected）と自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DBパス / 環境・ログレベル判定などのプロパティを用意（必須環境変数は未設定時に ValueError を送出）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - API レート制限対応（120 req/min）を守る固定間隔スロットリング（内部 _RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After を優先。
  - 401 発生時の自動トークンリフレッシュ（get_id_token を経由、1 回のみリトライ）およびモジュールレベルのトークンキャッシュ。
  - ページネーション対応（pagination_key の取り扱い）。
  - DuckDB へ冪等的に保存する save_* 関数（ON CONFLICT DO UPDATE を使用）：save_daily_quotes, save_financial_statements, save_market_calendar。
  - レスポンスの JSON デコード失敗検出、適切なエラーハンドリングとログ出力。
  - 入力値変換ユーティリティ (_to_float, _to_int) を提供（安全な型変換、空値処理）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS 取得と整形、raw_news への保存、記事と銘柄紐付け（news_symbols）までの一連処理を実装。
  - 設計上の安全対策:
    - defusedxml を利用した XML パース（XML Bomb 対策）。
    - リダイレクト時にスキームとホストの検証を行うカスタムハンドラ (_SSRFBlockRedirectHandler) を導入し SSRF を緩和。
    - URL スキーム検証（http/https のみ許可）、プライベートアドレス判定（DNS 解決・IP 判定）によるアクセス制限。
    - 受信最大サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 展開後のサイズ検証（Gzip bomb 対策）。
    - トラッキングパラメータ（utm_*, fbclid 等）の除去と URL 正規化、正規化 URL からの記事 ID 生成（SHA-256 の先頭32文字）。
  - RSS パーシングのフォールバック（名前空間付き等）と pubDate の健全なパース（UTC 変換、失敗時は現在時刻で代替）。
  - 記事保存時のバルク INSERT（チャンク分割、トランザクション、INSERT ... RETURNING による新規挿入判定）: save_raw_news、save_news_symbols、内部用の _save_news_symbols_bulk。
  - テキスト前処理ユーティリティ（URL除去・空白正規化）と銘柄コード抽出ロジック（4桁数字、known_codes によるフィルタリング）。
  - デフォルト RSS ソースとして Yahoo Finance ビジネスカテゴリを登録。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義し、init_schema で初期化可能。
  - raw_prices, raw_financials, raw_news, raw_executions など Raw 層、
    prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed 層、
    features, ai_scores など Feature 層、
    signals, signal_queue, orders, trades, positions, portfolio_performance など Execution 層を定義。
  - 適切な CHECK 制約、PRIMARY KEY、外部キーを設定。
  - よく使うクエリに対するインデックス定義を含む。
  - init_schema は db_path の親ディレクトリ自動作成と冪等実行をサポート。get_connection を提供。

- ETL パイプライン基礎（src/kabusys/data/pipeline.py）
  - 差分更新を意図した ETL の骨組みを実装（run_prices_etl 等の一部を実装開始）。
  - 最小データ取得開始日（_MIN_DATA_DATE）とデフォルトのバックフィル日数（_DEFAULT_BACKFILL_DAYS = 3）を定義。市場カレンダーの先読み日数変数を用意。
  - ETL 結果を表す dataclass ETLResult（品質チェック結果やエラー情報を集約、辞書化メソッドを提供）。
  - テーブル存在チェック、最大日付取得ユーティリティ、営業日調整ヘルパー（_adjust_to_trading_day）を実装。
  - run_prices_etl: 差分取得ロジック（DB 最終日から backfill を考慮して date_from を決定）と jq.fetch_daily_quotes / jq.save_daily_quotes 呼び出し（現在のコードでは fetch → save の呼び出しを実装、戻り値の一部が未完）。

### Changed
- 該当なし（初回リリースのため過去変更は無し）。

### Fixed
- 該当なし（初回リリースのためバグ修正履歴は無し）。

### Security
- RSS パーサで defusedxml を使用し XML 関連脆弱性に配慮。
- RSS フェッチ時のリダイレクト検査とプライベートIPブロッキングにより SSRF リスクを低減。
- .env 読み込みでファイルアクセス失敗時に警告を出す（読み取り例外を安全に処理）。

### Notes / Implementation details
- jquants_client の HTTP 呼び出しは urllib を使用しており、リトライやトークンリフレッシュのロジックはライブラリ内で完結する設計。テスト時の注入 (id_token 引数) による容易なモックが可能。
- news_collector._urlopen はテストで差し替え可能なポイントとして設計（外部通信をモックできる）。
- DuckDB の INSERT 文は安全上の理由からパラメータ化（プレースホルダ）で実行しているが、バルク生成部分は SQL を文字列連結して生成しているため、将来的に SQL 長やパラメータ数の上限に注意（チャンク処理で軽減済み）。
- pipeline.run_prices_etl の末尾で return のタプルが未完（len(records), ）となっているため、正式な戻り値の構築が必要（今後修正予定）。

もしこの CHANGELOG に追加してほしい点（例えばリリース日を別にする、細かい実装トレードオフの追記、未実装/ TODO の明示など）があればお知らせください。