CHANGELOG
=========

すべての注目すべき変更点をここに記録します。
このファイルは「Keep a Changelog」仕様に準拠しています。

[Unreleased]
-------------

なし

[0.1.0] - 2026-03-18
--------------------

Added
- 基本パッケージ追加
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - モジュール分割: data, strategy, execution, monitoring（__all__ に登録）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）により .env 自動読み込みを実装。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env の行解析ロジック（export 形式、引用符内エスケープ、インラインコメント処理など）。
  - 必須環境変数チェック（_require）と値検証（KABUSYS_ENV，LOG_LEVEL の許容値検査）。
  - J-Quants / kabuステーション / Slack / DB パスなどの設定プロパティを提供（duckdb/sqlite path を Path 型で返却）。

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 基本クライアント実装（ベースURL, rate limit, retry/backoff, JSON デコード処理）。
  - 固定間隔の RateLimiter（120 req/min 相当）を実装。
  - 再試行ロジック: 指数バックオフ、最大3回リトライ（408/429/5xx を対象）、429 の Retry-After サポート。
  - 401 応答時の自動トークンリフレッシュ（1回のみ）とモジュールレベルのトークンキャッシュ。
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）を実装。
  - DuckDB 保存用の save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE による冪等化）。
  - fetched_at を UTC で付与・記録、データ変換ユーティリティ（_to_float / _to_int）を実装。
  - ページネーション時に pagination_key を扱い重複ページ防止。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからニュースを取得して raw_news へ保存する機能を実装。
  - セキュリティ対策:
    - defusedxml を利用した XML パース（XML Bomb 等対策）。
    - SSRF 対策: URL スキーム検証、ホストがプライベート/ループバック/リンクローカルかを検査、リダイレクト時も検証するカスタムリダイレクトハンドラ実装。
    - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）によるメモリDoS対策、gzip 解凍後のサイズチェック。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事ID生成（正規化URL の SHA-256 先頭32文字）。
  - テキスト前処理（URL除去、空白正規化）。
  - save_raw_news：チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いることで挿入された新規記事IDのみを返す実装（トランザクションで一括処理、ロールバック対応）。
  - save_news_symbols / _save_news_symbols_bulk：news_symbols への紐付けをバルク挿入（ON CONFLICT DO NOTHING、INSERT ... RETURNING による実挿入数の算出）。
  - 銘柄コード抽出ロジック（4桁数字、既知コードセットとの照合）と run_news_collection による複数ソースの統合収集処理（ソース単位で独立したエラーハンドリング）。

- DuckDB スキーマ定義 & 初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層を想定したDDLを定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 各種制約（PRIMARY KEY, FOREIGN KEY, CHECK）やインデックス定義を用意。
  - init_schema(db_path)：親ディレクトリの自動作成、全テーブル・インデックスの作成（冪等）を行い接続を返す。
  - get_connection(db_path)：既存 DB への接続を返すユーティリティ。

- ETL パイプライン基礎（src/kabusys/data/pipeline.py）
  - ETLResult データクラスを導入し ETL 実行結果（取得数 / 保存数 / 品質問題 / エラー列）を集約。品質問題はシリアライズ可能な形で出力。
  - 差分取得ヘルパー: テーブル存在チェック、最大日付取得ユーティリティ。
  - 市場カレンダーに基づく trading day 調整ユーティリティ（非営業日の場合に過去方向で最近の営業日に調整）。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
  - run_prices_etl（差分更新ロジック）を実装開始: DB の最終取得日からの差分算出、backfill_days を考慮した再取得、J-Quants からの取得と保存（jquants_client の save_* を利用）。（ETL ワークフローの基盤を提供）

- その他
  - data パッケージ・モジュール初期化ファイル追加（空の __init__ を配置）。
  - strategy, execution パッケージの初期ファイル（現時点ではプレースホルダ）。

Security
- ニュース収集での SSRF 防止、受信サイズ制限、defusedxml による XML 脆弱性対応を導入。
- J-Quants API クライアントにてトークン自動リフレッシュ・キャッシュ、レート制御および安全なリトライ戦略を導入。

Performance & reliability
- DuckDB 側は ON CONFLICT による冪等保存や INSERT ... RETURNING を利用した正確な挿入検出を採用。
- RSS/DB バルク挿入はチャンク化してトランザクションで実行しオーバーヘッドを削減。
- API 呼び出しは固定間隔スロットリングと指数バックオフによる安定化。

Known issues / Notes
- strategy / execution パッケージは現状プレースホルダであり、発注ロジックや戦略本体は未実装。
- run_prices_etl など ETL 側の一部処理は基盤ロジックを実装済みだが、全体の統合・品質チェック（quality モジュールとの連携）は別途実装・テストが必要。
- テスト用の依存（ネットワーク／DB）を差し替えるためのフック（例: _urlopen のモック可能性等）を設けているが、ユニットテストは別途追加推奨。

--- 

（補足）: 本 CHANGELOG はソースコードから推測して作成しています。動作や API 仕様の詳細は実際の実装・ドキュメント（README, DataPlatform.md, DataSchema.md 等）を参照してください。