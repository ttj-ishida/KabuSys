# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
SemVer に従い、リリースごとに主な追加・変更点をまとめています。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-18
初回公開リリース

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期構成を追加。
  - バージョン情報: kabusys.__version__ = "0.1.0"。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む機能を実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を起点）により、カレントディレクトリに依存せずに .env ファイルを探索。
  - .env と .env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。.env.local は .env の値を上書き可能。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト時の制御用）。
  - .env パーサを実装（コメント行、export プレフィックス、クォートとエスケープ、インラインコメントの処理に対応）。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供し、以下の設定をプロパティ経由で取得可能に:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live/is_paper/is_dev ヘルパー

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - J-Quants から株価日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーを取得するクライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）を実装。
  - 再試行（指数バックオフ、最大 3 回）を実装。対象はネットワークエラーおよび HTTP 408/429/5xx。
  - 401 Unauthorized を検出した場合、自動でリフレッシュトークンから id_token を再取得して 1 回リトライする仕組みを実装（無限再帰防止あり）。
  - ページネーション対応（pagination_key を用いたループ処理）。
  - データ取得関数:
    - fetch_daily_quotes
    - fetch_financial_statements
    - fetch_market_calendar
  - DuckDB への保存関数（冪等性を担保、ON CONFLICT DO UPDATE を利用）:
    - save_daily_quotes
    - save_financial_statements
    - save_market_calendar
  - データ型変換ユーティリティ:
    - _to_float（空値・不正値は None）
    - _to_int（"1.0" は許容、非整数小数は None）

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードから記事を収集し raw_news に保存する機能を実装。
  - 設計上の安全対策:
    - defusedxml を用いた XML パース（XML Bomb 等の対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト時の検査、ホスト→IP のプライベートアドレス判定。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - 受信ヘッダ Content-Length の事前チェック。
  - 記事 ID は URL 正規化後の SHA-256 ハッシュ先頭32文字で生成し冪等性を確保（utm_* などトラッキングパラメータを除去）。
  - URL 正規化処理を実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - DB 保存の最適化:
    - INSERT ... RETURNING を使って実際に挿入された記事 ID を返す save_raw_news。
    - チャンク挿入（_INSERT_CHUNK_SIZE）および単一トランザクションでのコミット。
    - news_symbols（記事と銘柄コードの紐付け）を一括で保存する _save_news_symbols_bulk と個別保存 save_news_symbols。
  - 銘柄コード抽出ロジック（4桁数値、known_codes フィルタ）を実装（extract_stock_codes）。

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - DataSchema.md に基づく多層スキーマを定義（Raw / Processed / Feature / Execution）。
  - 生データ・整形データ・特徴量・実行関連のテーブル DDL を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 必要なインデックスを作成する SQL を追加（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) で DB ファイルの親ディレクトリ作成を含めた初期化とテーブル作成を行う冪等 API を提供。
  - get_connection(db_path) で既存 DB への接続を返す。

- ETL パイプライン (`kabusys.data.pipeline`)
  - 差分更新を行う ETL パイプライン基盤を実装。
  - ETL 実行結果を格納する ETLResult データクラス（品質問題・エラー集約、to_dict 出力）を提供。
  - 差分取得ヘルパー:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _get_max_date（一般ユーティリティ）
    - _table_exists
  - 市場カレンダーを用いた営業日調整ヘルパー _adjust_to_trading_day を実装。
  - run_prices_etl の骨格を実装（差分計算、backfill_days による再取得、jquants_client 呼び出しと保存、ログ出力）。※ファイル末尾での戻り値タプルの一部コーディングがファイル切れのため完全実装は継続予定。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 脆弱性対応 (Security)
- ニュース収集における SSRF 対策を実装:
  - _validate_url_scheme によるスキームチェック。
  - リダイレクト検査用ハンドラ _SSRFBlockRedirectHandler。
  - ホストがプライベート IP/ループバック/リンクローカル/マルチキャストであれば拒否。
- XML パースに defusedxml を利用し、既知の XML 攻撃ベクタへの耐性を強化。

### パフォーマンス・信頼性 (Performance / Reliability)
- J-Quants クライアントでのレート制御（120 req/min）と再試行/指数バックオフの導入により大規模データ取得の安定性を向上。
- news_collector のバルク挿入・チャンク処理・トランザクションまとめにより DB 書き込みオーバーヘッドを削減。
- DuckDB 側は ON CONFLICT を利用した冪等保存を基本とし、反復実行可能な ETL を想定。

### 既知の制限・備考 (Notes)
- run_prices_etl の末尾がソース切れにより戻り値の実装が不完全に見える個所があります（len(records), の後続値が欠落）。今後のコミットで完了予定です。
- 必須環境変数が未設定の場合、Settings のプロパティアクセスで ValueError を発生させます。初回導入時は .env.example を参考に .env を用意してください。
- init_schema() を最初に呼んで DB スキーマを作成してから ETL 等を実行することを推奨します。

---

参考 — 必要となる主要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

デフォルトファイルパス（変更可能）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db

（以上）