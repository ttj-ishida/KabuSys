CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティック バージョニングを採用します。

0.1.0 - 2026-03-17
------------------

Added
- 初期リリースを公開。
- パッケージ構成:
  - kabusys パッケージ（__version__ = 0.1.0）を導入。公開モジュール: data, strategy, execution, monitoring を意図的にエクスポート。

- 環境設定 / ロード機構 (kabusys.config):
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを特定（配布後も動作）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env パーサー強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの扱い、トークン化の堅牢化。
  - Settings クラス提供（settings インスタンス）:
    - 必須値取得時は未設定で ValueError を発生（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - デフォルト値と検証を用意（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV の有効値チェック、LOG_LEVEL の検証）。
    - 環境種別判定ユーティリティ: is_live / is_paper / is_dev。

- J-Quants API クライアント (kabusys.data.jquants_client):
  - J-Quants からの株価日足・財務データ・マーケットカレンダー取得機能を実装。
  - レート制限制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - リトライロジック: 指数バックオフ、最大リトライ回数 3、対象ステータス（408、429、5xx）。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回のみ）を実装。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements）。
  - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。INSERT ... ON CONFLICT DO UPDATE を使用。
  - データ取得時の fetched_at に UTC タイムスタンプを付与して Look-ahead bias 対策を実施。
  - 型変換ユーティリティ: _to_float / _to_int（空値・パース失敗に対する安全処理）。

- ニュース収集モジュール (kabusys.data.news_collector):
  - RSS フィードから記事を収集して raw_news テーブルへ保存する一連の機能を実装。
  - セキュリティ対策:
    - defusedxml を利用した XML パース（XML Bomb 等への対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカル/マルチキャストでないことを検査、リダイレクト時にも検証するカスタム HTTPRedirectHandler を導入。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ再検証（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid, gclid 等）を実施し、正規化 URL の SHA-256（先頭32文字）を記事 ID として生成して冪等性を保証。
  - テキスト前処理（URL 除去・空白正規化）。
  - INSERT ... RETURNING を使用して実際に挿入された記事 ID を返す save_raw_news。
  - ニュースと銘柄コードの紐付け: extract_stock_codes（4桁銘柄コード抽出、known_codes に基づく検証）と _save_news_symbols_bulk / save_news_symbols によるバルク挿入（チャンク処理・トランザクション）。
  - テストフック: _urlopen をモック差し替え可能にして HTTP 呼び出しをテスト容易化。
  - デフォルト RSS ソースとして Yahoo ビジネスカテゴリの RSS を登録。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema):
  - Raw / Processed / Feature / Execution の 3 層＋実行テーブルを含む包括的な DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed テーブル。
  - features, ai_scores などの Feature テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance などの Execution テーブル。
  - 各テーブルの CHECK 制約や PRIMARY KEY、外部キーを定義。
  - よく使うクエリに向けたインデックス群を作成。
  - init_schema(db_path) でディレクトリ作成→接続→DDL とインデックスを実行して初期化（冪等）。get_connection() も提供。

- ETL パイプライン (kabusys.data.pipeline):
  - 差分更新を中心とした ETL の骨組みを実装。
  - ETLResult データクラスを導入（取得数・保存数・品質問題・エラー等を保持、辞書化メソッド含む）。
  - 最終取得日の判定ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダーを考慮した営業日調整ヘルパー (_adjust_to_trading_day)。
  - run_prices_etl の差分更新ロジック（最終取得日からの backfill_days を考慮した date_from 自動算出、fetch→save の呼び出し）を実装。
  - 設計方針として品質チェックは検出しても ETL は継続し、呼び出し元に決定を委ねる（Fail-Fast ではない）。品質チェックは外部モジュール quality と連携する想定。

Security
- RSS/HTTP 周りに対する SSRF 対策、XML パースセーフガード、レスポンス上限、gzip 解凍後の検査などを実装。
- .env 読み込みで OS 環境変数を保護する仕組みを導入。

Notes / Implementation details
- ネットワーク操作では urllib を利用し、タイムアウトとヘッダ制御を設定。
- トークンキャッシュ（モジュールレベル）と強制リフレッシュ機能を持たせ、ページネーション間でトークンを再利用。
- DuckDB への大量挿入はチャンク化してパラメータ数や SQL 長の上限に配慮。
- ロギングを多用して操作の可観測性を確保（info/warning/exception）。
- 一部関数・処理はテストを想定したフック（例: _urlopen モック）を備える。

Removed / Changed / Fixed
- （初期リリースのため該当なし）

Security (今後の注意)
- J-Quants / kabu API の秘密情報は環境変数で管理する想定。README や .env.example に記載して配布することを推奨。

今後の予定（例示）
- ETL の残りジョブ実装（財務データ・カレンダーの差分 ETL 実装完了・品質チェックの統合）。
- strategy / execution / monitoring の実装拡充（現在はパッケージエントリのみ）。
- 詳細なテストカバレッジと CI ワークフローの追加。
- ドキュメントと .env.example の整備。

（以上）