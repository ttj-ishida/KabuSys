# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog のフォーマットに準拠しており、セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-17

初回リリース — 日本株自動売買基盤 (KabuSys) の最小実装を追加しました。

### 追加 (Added)
- パッケージ初期構成
  - src/kabusys/__init__.py にパッケージメタ情報（__version__ = "0.1.0"）、公開サブパッケージを定義。
  - 空のモジュールプレースホルダを配置:
    - src/kabusys/execution/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/data/__init__.py

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート判定は .git または pyproject.toml）。
  - .env パーサの実装: export prefix, クォート処理、インラインコメント処理、エスケープシーケンス対応。
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB / システム設定（KABUSYS_ENV, LOG_LEVEL 等）を型安全に取得。
  - 環境値検証（KABUSYS_ENV の許容値, LOG_LEVEL の許容値）および is_live/is_paper/is_dev のユーティリティを追加。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 通信用ユーティリティ実装（GET/POST、JSON パース）。
  - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を追加。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (財務データ)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 数値変換ユーティリティ (_to_float, _to_int) を実装し不正値に対する堅牢性を確保。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集と前処理パイプラインを実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策: URL スキーム検証、リダイレクト時のスキーム/ホスト検査、プライベートIP拒否（DNS 解決で A/AAAA を検査）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後の再検査（Gzip bomb 対策）。
  - URL 正規化およびトラッキングパラメータ除去処理。
  - 記事ID生成: 正規化 URL の SHA-256 ハッシュ先頭32文字（冪等性の確保）。
  - RSS 解析・前処理:
    - preprocess_text（URL除去、空白正規化）
    - _parse_rss_datetime（pubDate の堅牢なパースとフォールバック）
  - DuckDB への保存（冪等）:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + INSERT ... RETURNING id（チャンク挿入、1 トランザクション）
    - save_news_symbols / _save_news_symbols_bulk: news と銘柄コードの紐付けをチャンク挿入（ON CONFLICT DO NOTHING、RETURNINGで実際の挿入数を返す）
  - 銘柄コード抽出ロジック: 4桁数値パターンに基づき known_codes によるフィルタリング（重複除去）。
  - 統合収集ジョブ run_news_collection: 複数ソースを個別に処理し、エラーがあっても他ソースへ影響を与えない設計。

- データベーススキーマ (src/kabusys/data/schema.py)
  - DuckDB 用の完全なスキーマ定義を追加（Raw / Processed / Feature / Execution 層）。
  - テーブル群（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）を定義。
  - 適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）および頻出クエリ向けのインデックスを追加。
  - init_schema(db_path) によりディレクトリ作成→テーブル作成→インデックス作成を行い、接続を返す（冪等）。get_connection を提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計方針と差分更新ロジックを実装。
  - ETLResult データクラスを追加し、処理結果・品質問題・エラーの集約を提供。
  - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists, _get_max_date）。
  - trading day 調整ユーティリティ（_adjust_to_trading_day）。
  - 差分更新用ヘルパー: get_last_price_date, get_last_financial_date, get_last_calendar_date。
  - run_prices_etl の骨組みを実装（差分計算、backfill_days による再取得、fetch + save の呼び出し）。  

### 変更 (Changed)
- 初回リリースのため、変更履歴なし。

### セキュリティ (Security)
- news_collector にて複数の SSRF / XML パース / 圧縮爆弾対策を実装（defusedxml、レスポンスサイズ上限、プライベートIP判定、リダイレクトハンドラによる事前検証）。
- HTTP リクエスト時のタイムアウト設定や最大再試行回数、J-Quants API クライアントでの再試行ポリシーにより外部依存の堅牢性を強化。

### 既知の注意点 / マイグレーション情報 (Notes)
- 環境変数必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings により必須と判定される（未設定の場合 ValueError）。
- .env 自動読込はプロジェクトルート判定に依存する (.git または pyproject.toml)。CI/テスト環境等で自動読み込みを無効化する場合、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化: データベースファイルを使用する場合は、必ず init_schema() を実行してスキーマを作成してください（get_connection は既存DB接続用）。
- J-Quants API 利用時:
  - レート制限 (120 req/min) を遵守する必要があるため、クライアント側でスロットリングを行います。
  - トークンの自動リフレッシュ処理が組み込まれているため、refresh token（JQUANTS_REFRESH_TOKEN）の管理に注意してください。
- news_collector.fetch_rss は HTTP/HTTPS スキームの URL のみ許可します。ローカルファイルや特殊スキームは拒否されます。

### 互換性 (Compatibility)
- 初回リリースのため Breaking change はなし。

-- End of changelog --