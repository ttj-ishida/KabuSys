# Changelog

すべての重要な変更点をここに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  

最新版: 0.1.0

## [0.1.0] - 2026-03-18
初回公開リリース。

### 追加
- パッケージ基盤
  - kabusys パッケージの初版を追加。パッケージバージョンは 0.1.0。
  - パッケージの公開 API としてモジュール群を用意: data, strategy, execution, monitoring。

- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を起点）を実装。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを強化:
    - export プレフィックス対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの扱い（クォートあり/なしでの違い）
  - 必須値チェック（_require）と検証ロジック（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を追加。
  - デフォルト値: KABUSYS_API_BASE_URL、データベースパス（DUCKDB_PATH, SQLITE_PATH）など。

- J-Quants クライアント（kabusys.data.jquants_client）
  - J-Quants API からのデータ取得クライアントを実装。
  - 主なデータ取得 API:
    - fetch_daily_quotes: 株価日足（OHLCV）、ページネーション対応
    - fetch_financial_statements: 財務データ（四半期 BS/PL）、ページネーション対応
    - fetch_market_calendar: JPX マーケットカレンダー
  - 認証: get_id_token（リフレッシュトークン→IDトークン取得）
  - 信頼性とレート制御:
    - 固定間隔スロットリングで 120 req/min に準拠する RateLimiter（最小間隔算出）を実装
    - リトライロジック（指数バックオフ、最大 3 回、対象は 408/429/5xx、ネットワークエラー含む）
    - 401 発生時はトークン自動リフレッシュして 1 回リトライ（無限再帰防止のため allow_refresh フラグを適用）
    - ページネーション間で利用するモジュールレベルの ID トークンキャッシュを持つ
  - DuckDB への保存（冪等性）
    - save_daily_quotes: raw_prices に INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials に INSERT ... ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar に INSERT ... ON CONFLICT DO UPDATE
    - 値変換ユーティリティ（_to_float, _to_int）を提供し、空・不正値の安全な取り扱いを実装
    - PK 欠損レコードはスキップしてログ出力

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集して DuckDB に保存するモジュールを実装。
  - 安全性・堅牢性の設計:
    - defusedxml を用いた XML パース（XML Bomb 等対策）
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルかを判定して拒否、リダイレクト時にも検証するカスタム RedirectHandler を実装
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後の再チェック（Gzip-bomb 対策）
    - トラッキングパラメータ（utm_* 等）を除去して URL 正規化、正規化 URL の SHA-256 から記事 ID（先頭32文字）を生成して冪等性を担保
    - HTTP ヘッダーに User-Agent / Accept-Encoding 指定
  - 機能:
    - fetch_rss: RSS の取得・パース・記事抽出（title, content, pubDate のパース）を提供。XML パース失敗や不正なレスポンスはログ出力して空リストを返す。
    - preprocess_text: URL 除去・空白正規化
    - save_raw_news: raw_news テーブルへチャンク INSERT（INSERT ... RETURNING）して実際に挿入された記事IDを返す。トランザクションでまとめて安全に挿入。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの記事⇄銘柄紐付けをチャンク挿入で行い、実際に挿入された件数を返す（ON CONFLICT DO NOTHING）。
    - extract_stock_codes: テキストから 4 桁の銘柄コードを抽出（既知コードセットでフィルタ）し重複除去して返す。
    - run_news_collection: 複数 RSS ソースの収集を統合して DB に保存。ソースごとに独立してエラーハンドリングし、既知コードセットが与えられた場合は新規記事に対して銘柄紐付けを行う。

- DuckDB スキーマ（kabusys.data.schema）
  - DataPlatform 設計に基づく多層スキーマを追加（Raw / Processed / Feature / Execution）。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）を定義しデータ整合性を確保。
  - 頻出クエリに備えたインデックスを定義。
  - init_schema(db_path) でディレクトリ作成→テーブル・インデックス作成を行い、接続を返す。get_connection は既存 DB への単純な接続取得。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の共通処理、差分更新ルール、品質チェックフックのための基盤を追加。
  - ETLResult データクラスで ETL 実行結果（取得数・保存数・品質問題・エラー）を集約して返却する仕組みを実装。
  - 差分更新ユーティリティ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装（テーブル未作成や空テーブルは None を返す）
    - _adjust_to_trading_day: 非営業日を直近過去の営業日に調整（market_calendar が存在する場合）
  - run_prices_etl: 株価日足の差分 ETL を実装（最終取得日から backfill_days 前を date_from に設定する挙動、既定のバックフィルは 3 日）。J-Quants クライアント経由で取得し、保存は jquants_client.save_daily_quotes を使用。

### セキュリティと堅牢性の強化
- ネットワーク関連の堅牢化: タイムアウト、リトライ、Retry-After ヘッダ考慮、指数バックオフ、リダイレクト時の検証などを取り入れた。
- 入力パースの堅牢化: .env の厳密パース、RSS XML の安全パース（defusedxml）、レスポンスサイズ制限。
- データ整合性: DuckDB スキーマに制約を多く設定し、冪等な保存（ON CONFLICT）で重複や再取得への耐性を確保。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 既知の制限 / 今後の予定
- pipeline モジュールは ETL の骨格を提供しているが、品質チェック（quality モジュール）や一部の上位ジョブ（完全なスケジューリングや監視連携）はプロジェクト内の他モジュール実装に依存するため、追加実装・統合が必要。
- strategy / execution / monitoring パッケージはパッケージ構造として存在するが、個別の戦略実装や発注フロー、監視ルールは今後の実装対象。
- 大量データ/大規模運用における最適化（並列取得・バッチ戦略など）は今後の拡張領域。

#### 補足
- 本リリースでは主にデータ収集・保管・ETL 基盤と設定管理、セキュリティ対策に注力しています。戦略・実行層の具象実装は今後のリリースで追加予定です。