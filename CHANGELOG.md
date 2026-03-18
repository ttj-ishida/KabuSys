Keep a Changelog
================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

v0.1.0 - 2026-03-18
-------------------

初期リリース。日本株自動売買システム「KabuSys」のコア基盤を実装しました。
主に以下の機能・モジュールを追加しています。

Added
- パッケージ初期化
  - pakage version を 0.1.0 として設定（src/kabusys/__init__.py）。
  - 公開サブパッケージ: data, strategy, execution, monitoring をエクスポート。

- 環境設定 / ロード
  - .env ファイルまたは環境変数から設定を読み込む設定モジュールを実装（src/kabusys/config.py）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により、CWDに依存せず .env を自動ロード。
  - .env と .env.local の読み込み優先度制御、既存 OS 環境変数保護（protected）、上書きフラグ対応。
  - 行パーサは export 気、クォート、インラインコメント、エスケープシーケンスに対応。
  - 環境変数取得ヘルパ（必須チェック）と Settings クラスを提供。J-Quants / kabuAPI / Slack / DB パス等のプロパティを定義。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - KABUSYS_ENV / LOG_LEVEL の許容値検証とユーティリティプロパティ（is_live 等）。

- DuckDB スキーマ初期化
  - DataSchema.md に基づく多層スキーマ定義を実装（src/kabusys/data/schema.py）。
  - Raw / Processed / Feature / Execution 層のテーブル定義（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, ai_scores, signals, orders, trades, positions など）。
  - 各テーブルの CHECK 制約・主キー・外部キー定義を含む DDL。
  - 頻出クエリ向けのインデックス定義。
  - init_schema(db_path) によりディレクトリ作成・DDL 実行して接続を返す。get_connection() で既存 DB 接続を取得。

- J-Quants API クライアント
  - jquants_client モジュールを追加（src/kabusys/data/jquants_client.py）。
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - ページネーション対応（pagination_key を使用）、モジュールレベルの id_token キャッシュ。
  - HTTP レート制御（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダ優先。
  - 401 受信時は自動でリフレッシュトークンから id_token を取得して1回だけリトライ（無限再帰防止）。
  - DuckDB へ冪等に保存する関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE を利用して重複・更新を安全に処理。
  - レコード保存時に fetched_at を UTC ISO8601（Z）で記録して Look‑ahead bias を防止。
  - 数値変換ユーティリティ（_to_float, _to_int）で不正値や小数点の切り捨て回避。

- ニュース収集モジュール
  - RSS からニュースを収集・前処理・DB保存する news_collector を実装（src/kabusys/data/news_collector.py）。
  - デフォルト RSS ソース（Yahoo Finance）を定義。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事ID生成（正規化 URL の SHA‑256 の先頭32文字）で冪等性を確保。
  - defusedxml を使用した安全な XML パース（XML Bomb 等の緩和）。
  - SSRF 対策: 
    - 初回リクエスト前のホストプライベートチェック、
    - リダイレクト時にスキーム検証・プライベートアドレス拒否を行うカスタム RedirectHandler を導入、
    - HTTP スキームの検証（http/https のみ許可）。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - RSS のパース（channel/item 検出）、pubDate の RFC2822 パース（UTC への正規化）、テキスト前処理（URL除去・空白正規化）。
  - DB 保存はトランザクションでまとめ、チャンク処理・INSERT ... RETURNING を使って実際に挿入されたレコードを返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 銘柄コード抽出ロジック（4桁数字、known_codes フィルタ）を提供。

- ETL パイプライン
  - pipeline モジュールを実装（src/kabusys/data/pipeline.py）。
  - 差分更新ロジック: DB の最終取得日を確認して未取得分のみを取得（最小データ日や backfill_days に対応）。
  - run_prices_etl 等の個別 ETL ジョブ、差分判定ユーティリティ（get_last_price_date 等）、非営業日調整ヘルパ（_adjust_to_trading_day）。
  - ETLResult dataclass で実行結果／品質問題／エラーを集約。品質チェック結果（quality.QualityIssue）を取り扱う設計。
  - ETL は品質チェックで致命的な問題があっても処理を継続し、呼び出し元がアクションを判断できる設計（Fail‑Fast ではない）。

- ロギング・エラーハンドリング
  - 各モジュールで適切に logger を使用し、警告・エラーを記録。トランザクション失敗時はロールバックして例外再送出。

Security
- SSRF 緩和（リダイレクト時の検証、プライベートアドレスチェック、許可スキーム限定）。
- defusedxml による安全な XML パース。
- レスポンス読み取りサイズ上限（10MB）と gzip 解凍後の再チェックを導入し、メモリ DoS / Gzip bomb を防止。
- 環境変数ロード時のファイル読み取り失敗は警告に留めるなど安全なフォールバック。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Notes / Migration
- DuckDB スキーマは init_schema() で作成してください。既存 DB への接続のみを行う場合は get_connection() を使用します（スキーマ自動作成は行いません）。
- 自動 .env 読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利です）。
- J-Quants API のレート制限や再試行ポリシーを組み込んでいますが、運用環境ではログと監視を有効にし、必要に応じて backoff やスロットリングの調整を行ってください。

今後
- strategy / execution / monitoring の具体的なトレード実装、品質チェックモジュール quality の充実、ユニットテスト・統合テストの追加等を予定しています。