# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のパッケージバージョン: 0.1.0

## [Unreleased]
### Known issues
- run_prices_etl の最後の return 文が不完全（コード末尾に単独のカンマがあり、意図した (fetched, saved) タプルが返らない可能性があります）。動作確認・修正が必要です。

---

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買プラットフォームの基礎モジュール群を追加しました。主な追加内容・設計方針は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージの初期化（__version__ = "0.1.0"）と公開サブパッケージ指定（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理）。
  - 環境変数の上書き制御（override, protected キー）をサポート。
  - Settings クラスを提供し、J-Quants リフレッシュトークン、kabu API 設定、Slack トークン/チャネル、DB パスなどの取得用プロパティを用意。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値のチェック）と便宜的判定プロパティ（is_live / is_paper / is_dev）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ（_request）を実装：
    - 固定間隔のレート制限（120 req/min）を守る RateLimiter を導入。
    - 再試行（最大 3 回）、指数バックオフ、HTTP ステータス 408/429/5xx を再試行対象として扱う。
    - 429 の場合は Retry-After ヘッダを尊重。
    - 401 受信時はトークンを自動リフレッシュして 1 回だけリトライ（無限再帰を防止）。
    - ページネーション対応とトークンのモジュールレベルキャッシュ。
  - get_id_token（refresh token → id token）実装。
  - データ取得 API：
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数：
    - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を利用）
    - fetched_at は UTC（ISO8601/Z）で保存して Look-ahead Bias を追跡可能に。
  - ユーティリティ関数：_to_float, _to_int（安全な型変換）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集と前処理の実装。
  - セキュリティ対策：
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - URL スキーム検証（http/https のみ許可）。
    - プライベート / ループバック / リンクローカル / マルチキャストアドレスへのアクセス拒否（_is_private_host）。
    - リダイレクト時にスキームとホスト検証を行うカスタム RedirectHandler（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後の再チェック（Gzip Bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
  - 記事ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保。
  - 取得記事の前処理（URL除去、空白正規化）。
  - DuckDB への保存：
    - save_raw_news：チャンク化して一括 INSERT、INSERT ... RETURNING により新規挿入 ID を返す。トランザクションまとめてコミット/ロールバック。
    - save_news_symbols / _save_news_symbols_bulk：記事と銘柄コードの紐付けを冪等的に保存（ON CONFLICT DO NOTHING、RETURNING で実挿入数を取得）。
  - 銘柄コード抽出機能（4桁数字パターンを known_codes でフィルタ、重複除去）。
  - run_news_collection：複数 RSS ソースを順次処理し、失敗しても他ソースを継続する堅牢な収集ジョブ。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataPlatform 設計に基づくスキーマ定義（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル群。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores（Feature 層）、signals, signal_queue, orders, trades, positions, portfolio_performance（Execution 層）。
  - 頻出クエリ向けのインデックス群。
  - init_schema(db_path)：親ディレクトリ自動作成、全 DDL とインデックスを idempotent に実行して接続を返す。
  - get_connection(db_path)：既存 DB への接続取得（初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新に基づく ETL 設計（DB の最終取得日を参照して未取得分のみ取得）。
  - バックフィル（backfill_days デフォルト 3 日）で後出し修正を吸収する方針。
  - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）。
  - ETLResult dataclass による実行結果の集約（取得数、保存数、品質問題、エラー一覧を保持）。
  - テーブル存在チェックや最大日付取得ユーティリティ（_table_exists, _get_max_date）。
  - 取引日調整ヘルパ（_adjust_to_trading_day）。
  - 個別ジョブ例として run_prices_etl（J-Quants からの差分取得と DuckDB 保存のワークフロー）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS/XML 処理における以下の保護を導入：
  - defusedxml による XML パース（外部エンティティや XML Bomb の緩和）。
  - HTTP リダイレクト時のスキーム/ホスト検証で SSRF を低減。
  - ホストがプライベートアドレスの場合の接続拒否。
  - レスポンスサイズ上限と gzip 解凍後のサイズ確認でメモリ DoS を抑制。
  - URL 正規化でトラッキングパラメータを除去（分析の一貫性向上と冗長リンクの防止）。

---

貢献、バグ報告、改善要望は issue を立ててください。初回リリース以降の追加機能・修正は CHANGELOG に追記していきます。