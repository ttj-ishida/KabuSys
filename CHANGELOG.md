# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
慣例によりセクションは Added / Changed / Fixed / Security などで分類しています。

## [Unreleased]

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基盤実装を追加。
  - パッケージバージョンは src/kabusys/__init__.py の `__version__ = "0.1.0"`。
- 環境設定管理モジュール (kabusys.config)
  - .env / .env.local ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索）。
  - 自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - .env パーサ実装（export プレフィックス対応、クォート内のエスケープ処理、インラインコメントの扱い等）。
  - 環境変数の保護（OS 環境変数を protected として .env.local による上書きを制御）。
  - Settings クラスを公開（jquants/slack/kabu API 設定、DB パス、環境/ログレベルのバリデーション、 is_live 等のユーティリティプロパティ）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* API を実装（ページネーション対応）。
  - 認証: リフレッシュトークンから ID トークンを取得する get_id_token を実装。
  - レート制御: 固定間隔スロットリングによるレートリミッタ（120 req/min）。
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx に対するリトライ、429 の Retry-After 優先。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装。
  - DuckDB への保存用ユーティリティ save_daily_quotes / save_financial_statements / save_market_calendar を提供（ON CONFLICT DO UPDATE による冪等保存）。
  - データ型変換ユーティリティ (_to_float / _to_int)。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news テーブルに保存する機能を実装。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）。
  - defusedxml を用いた XML パース（XML Bomb 等の緩和）。
  - SSRF 対策: URL スキーム検証、ホストのプライベートアドレス判定、リダイレクト時の検査用ハンドラ(_SSRFBlockRedirectHandler) を導入。
  - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズ検証（Gzip bomb 対策）。
  - chunked なバルク INSERT / トランザクションで raw_news の一括保存 (save_raw_news)、ON CONFLICT DO NOTHING / INSERT ... RETURNING を利用して実際に挿入された ID を返却。
  - 記事と銘柄コードの紐付け機能（extract_stock_codes / save_news_symbols / _save_news_symbols_bulk）。
  - デフォルト RSS ソースを追加（Yahoo Finance ビジネス RSS）。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の多層スキーマを定義する DDL を追加。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw Layer。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols を含む Processed Layer。
  - features, ai_scores を含む Feature Layer。
  - signals, signal_queue, orders, trades, positions, portfolio_* を含む Execution Layer。
  - インデックス（頻出クエリに対する補助インデックス）定義を追加。
  - init_schema(db_path) によりディレクトリ作成→全テーブル / インデックス作成を行う初期化処理を実装。get_connection も提供。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETL 実行結果を表す ETLResult dataclass を追加（品質問題やエラーの集約、辞書化メソッド含む）。
  - 差分更新支援ユーティリティ (_table_exists, _get_max_date, get_last_price_date 等) を実装。
  - 市場カレンダーに基づき非営業日を直近営業日に調整するヘルパー (_adjust_to_trading_day) を追加。
  - 株価差分 ETL の run_prices_etl を実装（最終取得日の backfill、最小データ開始日の考慮、fetch→save の流れ）。
  - J-Quants クライアントからの id_token 注入に対応してテスト容易性を考慮。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- XML パースで defusedxml を利用し、XML Bomb 等の攻撃を軽減。
- RSS 取得時にスキームを http/https のみに制限、プライベートアドレス（ループバック・リンクローカル等）へのアクセスを拒否し SSRF を緩和。
- レスポンスの読み取りサイズ上限を導入してメモリ DoS を緩和（MAX_RESPONSE_BYTES）。
- .env ファイル読み込みで OS 環境変数を保護する仕組みを追加（protected keys）。

### Internal / Developer
- ネットワーク呼び出しや _urlopen、id_token のキャッシュ取得ロジックをモジュールレベルで分離し、テスト時にモックしやすい構造にしている（例: _urlopen の差し替え、id_token を引数で注入可能）。
- SQL 文は ON CONFLICT による冪等性を基本とし、INSERT ... RETURNING で実際の挿入結果を正確に取得する設計。
- ロガー出力を各所に追加して運用時のトラブルシュートを支援。

---

過去の変更履歴や今後のリリース方針に関する要望があればお知らせください。必要であれば英語版やリリースノートの簡易版（GitHub Releases 用）も作成します。