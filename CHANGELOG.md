# Keep a Changelog — CHANGELOG.md

すべての変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17
初回リリース

### 追加 (Added)
- パッケージのエントリポイントを追加
  - kabusys.__version__ = 0.1.0、パッケージ public API に data / strategy / execution / monitoring を公開。
- 環境設定モジュール（kabusys.config）
  - .env ファイルまたは環境変数から設定読み込みを実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準、__file__ を起点に探索）。
  - .env パーサを独自実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメントの扱いに対応）。
  - 自動ロード順を定義（OS 環境変数 > .env.local > .env）。自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - 必須キーの取得時に未設定なら例外を投げる _require() を提供。
  - 設定オブジェクト Settings を追加（J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DB パス、環境種類・ログレベル判定ユーティリティなど）。
  - 有効な環境値およびログレベルの入力検証を実装。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - ベースURL、レートリミット（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - 再試行（指数バックオフ、最大3回）、HTTP 429 の Retry-After を考慮したリトライ実装。
  - 401 受信時にリフレッシュトークンから id_token を自動更新して1回リトライする仕組み。
  - id_token のモジュールレベルキャッシュ（ページネーション間で共有）を実装。
  - JSON レスポンスのデコードエラーハンドリングを追加。
  - データ取得関数を実装：fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
  - DuckDB へ冪等に保存する関数を実装：save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT を用いた更新）。
  - 値変換ユーティリティ：_to_float, _to_int（文字列/None を安全に扱う）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからの記事取得・前処理・保存の一連処理を実装。
  - セキュリティ対策：
    - defusedxml による XML パース（XML Bomb 等への対策）。
    - SSRF 対策：スキーム検証（http/https 限定）、プライベートIP/ループバック/リンクローカル/マルチキャストの検出・排除、リダイレクト時の検査（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_ 等）を実装し、SHA-256（先頭32文字）で記事IDを生成。
  - テキスト前処理（URL除去・余白正規化）関数を提供。
  - fetch_rss（RSS 取得・パース）、save_raw_news（DuckDB へのバルク挿入、トランザクション、INSERT ... RETURNING による実挿入ID取得）、save_news_symbols、_save_news_symbols_bulk を実装。
  - 銘柄コード抽出ロジック（4桁数字、既知銘柄セットでフィルタ）と run_news_collection（複数ソースの統合収集）を実装。
  - デフォルト RSS ソースに Yahoo Finance を追加。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataPlatform の設計に基づくスキーマを定義（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw 層テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層テーブルを定義。
  - features, ai_scores の Feature 層テーブル、signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層を定義。
  - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）と索引（頻出クエリ想定）を用意。
  - init_schema(db_path) による初期化関数（ディレクトリ作成含む）と get_connection() を提供。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETL 実行結果を表す dataclass ETLResult を追加（品質問題・エラーの収集、シリアライズ機能）。
  - テーブル存在確認、最大日付取得ユーティリティを追加。
  - 市場カレンダーを用いた営業日調整ヘルパー _adjust_to_trading_day を実装（最大30日バックシフトのロジック）。
  - 差分更新のための最終日取得関数（get_last_price_date, get_last_financial_date, get_last_calendar_date）を実装。
  - run_prices_etl の骨組みを実装（差分計算、backfill_days、fetch と保存の呼び出し）。（実装はファイル末尾で未完了の可能性あり）

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- ニュース収集に関して複数の SSRF 対策および XML パースの安全化、レスポンスサイズ制限を実装。
- .env 読み込みにおいて OS 環境変数が保護されるよう protected セット運用を導入（.env.local による上書きは可能だが OS 環境を上書きしない設計）。

### 既知の制限 / 注意点
- jquants_client のリトライ対象ステータスは 408, 429 と 5xx。アプリケーション側でのさらに細かい制御は将来的に拡張可能。
- ETL の品質チェックモジュール (kabusys.data.quality) は参照されているが、このスコープのコードには実装の詳細が含まれていない（外部モジュールとして存在する想定）。
- run_prices_etl の戻り値や一部処理がファイル末尾で切れており、完全実装の有無はコード全体を参照する必要あり。

---

開発の方針や実装意図は各モジュールの docstring に記載しています。必要であれば各機能ごとの詳細な使用例・設計ノート（API 仕様、DB スキーマ図、ETL フロー図など）も作成できます。どの項目を優先してドキュメント化しますか？