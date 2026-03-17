# CHANGELOG

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 変更はセクション（Added, Changed, Fixed, Security, …）ごとに分類しています。
- 各リリースはバージョンとリリース日を明示します。

なお、本リリース内容はコードベースから推測した実装/設計に基づく要約です。

## [0.1.0] - 2026-03-17
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"、__all__ の定義）。
- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出ロジック（.git または pyproject.toml を探索）を追加し、パッケージ配布後も CWD に依存しない自動 .env ロードを実現。
  - .env と .env.local の読み込み優先度を実装（OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パース処理を強化：export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い、無効行のスキップ。
  - 必須環境変数取得用の _require() と、KABUSYS_ENV / LOG_LEVEL の許容値検証を実装。
  - 各種設定プロパティを提供（J-Quants トークン、kabu ステーション API 設定、Slack、データベースパス、実行環境判定など）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants API から株価日足（OHLCV）、財務四半期データ、マーケットカレンダーを取得するクライアントを実装。
  - レート制限対策：固定間隔スロットリング（120 req/min、モジュールレベルの RateLimiter）。
  - リトライロジック：指数バックオフ、最大試行回数（3回）、HTTP 408/429/5xx に対するリトライ、429 の場合は Retry-After ヘッダを尊重。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1回だけ）実装。トークン取得関数 get_id_token を提供。
  - ページネーション対応（pagination_key を追跡して続次ページを取得）。
  - データ保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を追加。DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で実装し、fetched_at を UTC ISO8601 で記録して Look-ahead Bias を抑制。
  - データ型変換ユーティリティ（_to_float / _to_int）を実装。整数変換時の小数部チェック等による安全な変換。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからの記事収集と DuckDB への格納ロジックを実装。
  - セキュリティ対策・堅牢性：
    - defusedxml による XML パース（XML Bomb 等の対策）。
    - SSRF 対策：URL スキーム検証（http/https のみ）、リダイレクト時のスキーム／ホスト検査、ホストがプライベートアドレスかどうかの判定（直接 IP と DNS 解決の両方で判定）。
    - レスポンス受信最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding を設定しての取得。
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid, gclid 等の除去、フラグメント削除、クエリソート）。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - テキスト前処理（URL 除去、空白正規化）を提供。
  - fetch_rss：RSS のパースと NewsArticle 構造（id, datetime, source, title, content, url）で返す処理を実装。
  - DB 保存機能：
    - save_raw_news：チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に新規挿入された記事IDのリストを返す。トランザクションでまとめて実行し、失敗時にロールバック。
    - save_news_symbols / _save_news_symbols_bulk：news_symbols テーブルへの記事⇄銘柄紐付けをチャンクINSERTで保存。ON CONFLICT で重複を排除し、挿入実績を RETURNING で集計。
  - 銘柄コード抽出（4桁数字）ユーティリティ extract_stock_codes を実装し、既知銘柄セットでフィルタリング。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataSchema に基づく DuckDB テーブル定義を実装（Raw / Processed / Feature / Execution の多層構造）。
  - 主なテーブル：raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等。
  - 適切な制約（PRIMARY KEY / FOREIGN KEY / CHECK）やインデックス（頻出クエリ向け）を定義。
  - init_schema(db_path) を実装：親ディレクトリの自動作成、全DDLとインデックスを適用して接続を返す（冪等）。get_connection(db_path) も提供。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新・バックフィルに基づく ETL 実装方針をコードに反映。
  - ETLResult データクラスを実装し、ETL 実行結果（取得数/保存数/品質問題/エラー）を表現。品質問題を辞書化する to_dict() を提供。
  - 市場カレンダーの先読み日数やデフォルトバックフィル日数 (_CALENDAR_LOOKAHEAD_DAYS, _DEFAULT_BACKFILL_DAYS) を定義。
  - テーブル存在チェック、最大日付取得補助関数（_table_exists, _get_max_date）を実装。
  - 非営業日調整のヘルパー (_adjust_to_trading_day) を実装。
  - 差分更新ヘルパー関数（get_last_price_date, get_last_financial_date, get_last_calendar_date）を実装。
  - run_prices_etl: raw_prices に対する差分ETLの流れを実装（最終取得日からの backfill、J-Quants からの fetch と保存を呼び出す）。テスト容易性のため id_token 注入可能。

### Changed
- 新規初期リリースのため、該当なし。

### Fixed
- 新規初期リリースのため、該当なし。

### Security
- news_collector にて複数の SSRF / XML / DoS 対策を実装：
  - defusedxml を利用した XML パース。
  - リダイレクト先検査とホストのプライベートアドレス拒否。
  - レスポンスサイズ制限と gzip 解凍後のチェック。
  - URL スキームの厳密な検証（http/https のみ）。

### Notes / Usage
- 環境設定:
  - 自動 .env 読み込みはデフォルトで有効（プロジェクトルートが検出できる場合）。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
  - 設定は kabusys.config.settings を経由して利用できます（例: from kabusys.config import settings; token = settings.jquants_refresh_token）。
- DB 初期化:
  - 初回は data/schema.init_schema(db_path) を呼び出してスキーマを作成してください。その後は get_connection() で既存DBに接続します。
- J-Quants API:
  - API レート上限を守るためモジュール内でのスロットリングを行っています。大量バッチ取得時は実行時間に注意してください。
- ニュース収集:
  - デフォルト RSS ソースは Yahoo Finance のビジネスカテゴリに設定されています（DEFAULT_RSS_SOURCES）。sources 引数でカスタムソースを指定可能。
  - extract_stock_codes には known_codes（銘柄一覧セット）を渡すことで誤検出を低減できます。

### Known issues / TODO
- パイプラインの実装は複数のジョブ（calendar/backfill/qualityチェック等）を想定しており、今後以下の点が改善/追加される可能性があります：
  - 品質チェック（quality モジュール）との統合詳細（重大度別アクション）の拡充。
  - ETL のより細かいログ/メトリクス、運用向けのリトライ/スケジューリング統合。
  - ニュース収集における追加フィード形式や全文抽出の強化。
- （注）コード断片の関係で一部実装や戻り値の継ぎ目が未完または切り出し途中に見える箇所があります。実運用前にユニットテストと統合テストで各 ETL 関数の戻り値と例外ハンドリングを確認してください。

---

今後のリリースでは、品質チェックの拡張、戦略モジュール（strategy）と実行モジュール（execution）の具体的実装、監視（monitoring）統合、CI/テストカバレッジ向上などを予定しています。