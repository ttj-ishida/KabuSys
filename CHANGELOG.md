# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

## [0.1.0] - 2026-03-17

初回公開リリース。

### 追加 (Added)
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境設定モジュールを実装 (src/kabusys/config.py)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装
    - 読み込み優先順: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env パーサーの実装
    - export プレフィックス対応、クォート内のエスケープ対応、インラインコメント判定
  - 環境変数取得ヘルパーと必須チェック（_require）
  - Settings クラス（settings インスタンス）を提供
    - J-Quants / kabuAPI / Slack / DB パス等のプロパティ
    - KABUSYS_ENV / LOG_LEVEL の妥当性検証
    - is_live / is_paper / is_dev ヘルパー

- J-Quants クライアントを実装 (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダーを取得する fetch_* 関数を実装（ページネーション対応）
  - HTTP リクエストユーティリティを実装
    - 固定間隔のレートリミッタ（120 req/min）を実装
    - リトライ（指数バックオフ、最大3回）・429 の Retry-After 考慮・408/429/5xx リトライ対象
    - 401 受信時はリフレッシュトークンで id_token を自動更新して再試行（1回まで）
    - JSON デコード失敗時に詳細なエラーを送出
  - id_token のキャッシュ化（モジュールレベル）と強制リフレッシュの仕組み
  - DuckDB へ冪等的に保存する save_* 関数を実装（ON CONFLICT DO UPDATE）
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - fetched_at に UTC タイムスタンプを記録
    - 型変換ユーティリティ (_to_float, _to_int) を実装し堅牢に変換

- ニュース収集モジュールを実装 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事収集し raw_news テーブルへ保存する機能を実装
  - セキュリティ・耐障害機能
    - defusedxml による XML パース（XML Bomb 等の防御）
    - SSRF 対策：URL スキーム検証（http/https 限定）、リダイレクト時のスキーム/内部アドレス検証、接続前のホストのプライベートアドレス検査
    - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズチェック（Gzip bomb 対策）
    - 受信時の最大読み込みバイト数制限
  - URL 正規化とトラッキングパラメータ削除（_normalize_url）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保
  - テキスト前処理（URL 除去、空白正規化）
  - DB 保存の堅牢化
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用、トランザクション管理、挿入された ID のリストを返す
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入し、実際に挿入された件数を返す。重複除去、トランザクション制御あり
  - 銘柄コード抽出機能（4桁数字パターン）と既知コードフィルタ（extract_stock_codes）
  - run_news_collection: 複数 RSS ソースを順次処理し、失敗したソースはスキップして継続。既定のソース辞書 DEFAULT_RSS_SOURCES を提供（例: Yahoo Finance）

- DuckDB スキーマ定義と初期化を実装 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の 3 層（+実行層）を反映したテーブル群を定義
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）を設定
  - クエリ性能向上のためのインデックス定義
  - init_schema(db_path): DB ファイルの親ディレクトリ自動作成、DDL を順序に従って実行しテーブルを作成（冪等）
  - get_connection(db_path): 既存 DB へ接続（スキーマ初期化は行わない）

- ETL パイプライン基盤を実装 (src/kabusys/data/pipeline.py)
  - ETLResult データクラスで実行結果・品質問題・エラーを集約
  - 差分更新ヘルパー（最終取得日取得、テーブル存在チェック）
  - 市場カレンダーを参照して非営業日を過去方向に調整するヘルパー (_adjust_to_trading_day)
  - run_prices_etl の基礎実装（差分取得ロジック、backfill_days による再取得、jquants_client の fetch/save 呼び出し）
  - 初回データ読み込みのための最小開始日定数 (_MIN_DATA_DATE = 2017-01-01)、カレンダー先読み日数等の定数

### 安全性・信頼性 (Security / Reliability)
- 外部データ取得に関する安全策を多数導入
  - defusedxml による XML パース
  - SSRF 対策（スキーム検証・プライベートアドレス拒否・リダイレクト時検査）
  - レスポンスサイズ制限と gzip 解凍後のサイズ検査（メモリ DoS / Gzip bomb 対策）
  - J-Quants クライアント側のレート制限・リトライ・トークン自動更新ロジック
- DB 操作は冪等性とトランザクション制御を重視
  - ON CONFLICT / DO UPDATE / DO NOTHING を活用
  - INSERT ... RETURNING で実際の挿入件数を正確に把握
  - トランザクション失敗時は rollback とログ記録

### ドキュメント・ログ
- 各モジュールに docstring を充実させ、設計・想定挙動（例: レート制限、品質チェック方針、バックフィル方針）を明記

### 既知の制約 / 今後の改善点（Notes / TODO）
- ETL の品質チェックモジュール (quality) は参照されているが、本リリースでの実装範囲は pipeline 側のフックまで（quality の詳細実装は別途）
- strategy / execution / monitoring パッケージはパッケージ構成として存在するが、具体的な戦略ロジックや発注実装は今後追加予定
- run_prices_etl の戻り値の最後の行でタプル返却が途中で切れている（コード断片のため、実装続きを追加する必要あり）

---

今後のリリースでは、strategy / execution ロジック、品質チェック実装、運用用ドキュメント・CLI の追加、テストカバレッジ拡充などを予定しています。