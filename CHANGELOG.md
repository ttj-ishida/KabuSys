# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このプロジェクトはセマンティックバージョニングを使用しています。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。

### 追加
- パッケージ構成
  - kabusys パッケージの初期化（__version__ = 0.1.0、公開モジュール指定）。
  - サブパッケージのスケルトン：data, strategy, execution, monitoring。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込みを自動化（プロジェクトルートは .git / pyproject.toml を基準に探索）。
  - .env と .env.local の優先順位を考慮した読み込みロジック。
  - export KEY=val 形式やクォート/エスケープ、インラインコメントのパース対応。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得ヘルパー _require() と Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / システム設定用プロパティ）。
  - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証を実装。

- J-Quants クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ _request を実装（JSON デコード検証、詳細なエラーハンドリング、リトライ、指数バックオフ）。
  - API レート制限遵守のための固定間隔レートリミッタ (_RateLimiter) を実装（既定 120 req/min）。
  - リトライ対象のステータス（408, 429, >=500）に基づくリトライと Retry-After の利用。
  - 401 受信時にリフレッシュトークンから id_token を自動リフレッシュして 1 回再試行する仕組みを実装（キャッシュ付き、再帰防止）。
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar() を実装（ページネーション対応、pagination_key 処理）。
  - DuckDB への冪等保存関数 save_daily_quotes(), save_financial_statements(), save_market_calendar() を実装（ON CONFLICT DO UPDATE を利用、PK 欠損行のスキップ、fetched_at の記録）。
  - 型安全な数値変換ユーティリティ _to_float(), _to_int() を実装。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集する fetch_rss() を実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 対策）。
    - SSRF 対策：URL スキーム検証、プライベートアドレス検出、リダイレクト時の検査（カスタム HTTPRedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES、デフォルト 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - HTTP User-Agent と Accept-Encoding の指定。
  - テキスト前処理（URL 除去、空白正規化）implement preprocess_text()。
  - URL 正規化（トラッキングパラメータ除去、フラグメント除去、クエリソート）と記事 ID 生成（SHA-256 の先頭32文字）を実装。
  - save_raw_news(): チャンク分割・トランザクション・INSERT ... RETURNING による新規挿入ID取得を実装（冪等: ON CONFLICT DO NOTHING）。
  - news_symbols テーブルへの紐付け保存（save_news_symbols(), _save_news_symbols_bulk()）を実装（チャンク処理・トランザクション）。
  - 銘柄コード抽出ユーティリティ extract_stock_codes() を実装（4桁数字、known_codes によるフィルタ・重複除去）。
  - run_news_collection(): 複数 RSS ソースを扱う統合ジョブ。各ソースは独立してエラーハンドリングし継続実行。既知銘柄との紐付け処理を実装。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義を網羅する DDL を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 制約（PRIMARY KEY、CHECK、FOREIGN KEY）を含むテーブル定義。
  - パフォーマンスを考慮したインデックス一覧を定義。
  - init_schema(db_path) により親ディレクトリ作成、全テーブル・インデックスを冪等的に作成して DuckDB 接続を返す。
  - get_connection(db_path) ヘルパーを追加（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass で ETL 実行結果（取得数、保存数、品質問題、エラー等）を記録し、辞書化可能に実装。
  - テーブル存在確認や最大日付取得のユーティリティ（_table_exists(), _get_max_date()）を実装。
  - 市場カレンダ補正ヘルパー _adjust_to_trading_day() を実装（非営業日を直近営業日に調整、30日遡り）。
  - 差分更新ヘルパー get_last_price_date(), get_last_financial_date(), get_last_calendar_date() を提供。
  - run_prices_etl(): 差分取得ロジック（最終取得日からの backfill_days 再取得、_MIN_DATA_DATE を基準とした初回ロード）と jquants_client を使った fetch/save を実装。品質チェックフレームワーク（quality）との連携ポイントを用意。

### 変更
- （初回リリースのため無し）

### 修正
- （初回リリースのため無し）

### セキュリティ
- RSS 処理で SSRF 対策を実施（スキーム検証、プライベートIP検査、リダイレクト時検査）。
- XML パースに defusedxml を使用して XML 攻撃（XML Bomb など）に配慮。
- ネットワーク応答サイズ制限・gzip 解凍後サイズ確認によりメモリ DoS を軽減。

### 注意事項 / 移行ガイド
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings クラスのプロパティを参照）。
  - 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途等）。
- データベース:
  - 初回は init_schema(path) を呼び出して DuckDB のスキーマを作成してください。get_connection() は既存 DB へ接続するのみでスキーマ初期化は行いません。
- API レート:
  - J-Quants API のレート上限（120 req/min）を尊重するため内部でスロットリングを行っています。大量データ取得の際は時間がかかる点に留意してください。
- ETL:
  - run_prices_etl 等の差分ETLは backfill_days により後出し修正を吸収する挙動です。デフォルトは 3 日です。
- ニュース収集:
  - extract_stock_codes() は known_codes（有効銘柄コードのセット）を用いてフィルタする設計です。known_codes を与えない場合は紐付けステップをスキップします。

### 既知の制限 / TODO
- quality モジュール（品質チェック）の詳細実装は外部モジュール（kabusys.data.quality）に依存しており、品質チェックルール・重大度ハンドリングの拡充が必要。
- strategy / execution / monitoring の具体的な実装は本バージョンではスケルトンのみ（別途実装予定）。
- run_prices_etl の他の ETL ジョブ（financials, calendar 等）の統合的なジョブフローは今後追加予定。

---

今後のリリースでは戦略実装、実行連携（kabuステーション）、監視・アラート機能の追加、品質チェック強化、テストカバレッジ拡大を予定しています。