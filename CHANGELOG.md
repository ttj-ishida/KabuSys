CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

[Unreleased]
------------

（現在のところ保留中の変更はありません）

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初期リリース。基本モジュール群を実装。
  - kabusys.__init__ にバージョン情報と公開サブパッケージを定義。
- 環境設定管理: kabusys.config.Settings
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - export 形式やクォート・インラインコメントに対応した .env パーサ実装。
  - 環境変数取得ヘルパ（必須変数で未設定の場合は ValueError）を提供。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/...）の検証。
  - パス設定（DUCKDB_PATH / SQLITE_PATH）の Path 変換と展開。
- J-Quants API クライアント: kabusys.data.jquants_client
  - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得機能を提供（ページネーション対応）。
  - リクエストのレート制御（固定間隔スロットリング、120 req/min 相当）。
  - 再試行ロジック（指数バックオフ、最大 3 回。408/429/5xx を対象）。
  - 401 受信時の自動 ID トークンリフレッシュ（1 回のみリトライ）を実装。
  - ページネーション間でトークンをモジュールレベルでキャッシュして共有。
  - 取得データに対して fetched_at を UTC ISO 形式で記録（Look-ahead bias 対策）。
  - DuckDB への保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で実装（save_daily_quotes, save_financial_statements, save_market_calendar）。
  - 型変換ユーティリティ（_to_float, _to_int）で安全に数値変換。
- ニュース収集モジュール: kabusys.data.news_collector
  - RSS フィード取得・パース・前処理・DB 保存の一連処理を実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection 等）。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）と記事ID生成（正規化 URL の SHA-256 先頭32文字）。
  - テキスト前処理（URL 除去・空白正規化）。
  - defusedxml を用いた安全な XML パース（XML Bomb 等の対策）。
  - SSRF 対策:
    - URL スキームは http/https のみ許可。
    - ホストのプライベート/ループバック/リンクローカル判定（直接IPおよび DNS 解決結果をチェック）。プライベートアドレスへのアクセスを拒否。
    - リダイレクト時に検査するカスタムハンドラを使用。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズチェックによる DoS対策。
  - DuckDB への保存はチャンク処理およびトランザクションで実行し、INSERT ... RETURNING により実際に挿入された件数を返す（冪等性: ON CONFLICT DO NOTHING）。
  - 記事中の銘柄コード抽出 util（4桁数字パターン、既知コードセットとの照合）。
- DuckDB スキーマ定義: kabusys.data.schema
  - Raw / Processed / Feature / Execution の多層スキーマを DDL として実装。
  - raw_prices, raw_financials, raw_news, raw_executions など Raw 層テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed 層。
  - features, ai_scores など Feature 層。
  - signal_queue, orders, trades, positions, portfolio_performance など Execution 層。
  - 外部キー制約・チェック制約・インデックスを含むDDLを定義し、init_schema(db_path) で冪等に初期化可能。
- ETL パイプライン: kabusys.data.pipeline
  - 差分更新ロジック（最終取得日からの差分取得、バックフィル日数による後出し修正吸収）。
  - 市場カレンダーの先読み、デフォルトバックフィル日数の設定。
  - ETLResult データクラスにより ETL 実行結果（取得/保存件数、品質問題、エラー等）を構造化。
  - テーブル存在チェックや最大日付取得などのヘルパ関数を提供。
  - 個別ジョブ run_prices_etl の実装（fetch -> save の流れを想定）。  

Security
- XML パースに defusedxml を採用し、XML-based攻撃（Billion Laughs 等）への耐性を確保。
- RSS 取得時にスキーム検証・プライベートホストチェック・リダイレクト検査・最大読み取りバイト数の制限を実施し、SSRF / メモリDoS を軽減。
- .env ロード時に OS 環境変数を保護する「protected」仕組みを導入（.env.local の override 動作の制御含む）。

Performance
- J-Quants API 呼び出しに単純固定間隔のレートリミッタを導入し、API レート制限遵守を評価。
- DuckDB へのバルク挿入をチャンク処理およびトランザクションでまとめて行うことによりオーバーヘッドを低減。
- ニュースの銘柄紐付けをバルク挿入する内部関数を用意。

Notes / Known limitations
- 現時点は主要機能の実装が中心で、外部インテグレーション（Slack 通知、kabuステーションでの発注など）や詳細な品質チェックモジュール（quality）は別実装を想定している。
- run_prices_etl 等一部関数は外部モジュール（quality 等）との連携を前提としているため、運用時は依存モジュールの導入・設定が必要。
- id_token キャッシュはモジュールレベルで保持する単純実装のため、長時間実行プロセスや並列実行時は運用ルールの検討が必要。

開発者向け情報
- 環境読み込み順: OS 環境変数 > .env.local > .env
- 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 初期化は init_schema(db_path)、既存 DB に接続するだけなら get_connection(db_path) を使用してください。

---