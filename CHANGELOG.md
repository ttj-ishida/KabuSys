# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従っており、セマンティックバージョニングを使用します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17
初回公開リリース。

### Added
- パッケージのコア
  - kabusys パッケージを追加。バージョンは `0.1.0`。
  - public API（__all__）に data, strategy, execution, monitoring を定義（strategy, execution は初期の空パッケージ/プレースホルダを含む）。

- 環境設定 / 設定管理（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml）基準で自動読み込みする仕組みを実装。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env 行パーサを実装（コメント行、`export KEY=val`、シングル/ダブルクォート、エスケープ文字、インラインコメントの取り扱いに対応）。
  - 環境変数の上書きポリシー（OS 環境変数を保護する protected セット）を実装。
  - Settings クラスを提供し、J-Quants / kabu ステーション API / Slack / DB パス（DuckDB/SQLite） / 実行環境（development/paper_trading/live） / ログレベルの取得・検証用プロパティを実装。
  - env 値検証（KABUSYS_ENV と LOG_LEVEL の有効値チェック）、is_live / is_paper / is_dev のヘルパーを追加。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制御（固定間隔スロットリング）で 120 req/min を遵守する RateLimiter を実装。
  - 汎用リクエスト関数に対してリトライロジック（最大 3 回、指数バックオフ、408/429/5xx に対応）を実装。
  - 401 エラー受信時はリフレッシュトークンから id_token を再取得して 1 回だけリトライする自動リフレッシュ機構を実装（キャッシュ共有対応）。
  - ページネーション対応の取得関数を実装:
    - fetch_daily_quotes（株価日足 / OHLCV）
    - fetch_financial_statements（四半期 BS/PL）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB へ冪等的に保存する save_* 関数を実装（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 型安全な変換ユーティリティ _to_float / _to_int を実装し、データ不整合に寛容に対応。
  - ログ出力（取得件数・保存件数・スキップ件数等）を充実。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集して raw_news テーブルへ保存するモジュールを実装（DEFAULT_RSS_SOURCES を含む）。
  - セキュリティ対策:
    - defusedxml を使った XML パース（XML bomb 等の防御）。
    - URL スキーム検証（http/https のみ許可）、SSRF 対策のためのホスト/リダイレクト検証（プライベート/ループバック/リンクローカルの拒否）。
    - リダイレクト時の事前検証ハンドラ（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ上限検査（MAX_RESPONSE_BYTES、Gzip 解凍後も検査）。
  - URL 正規化（トラッキングパラメータ削除、フラグメント除去、パラメータソート）と記事ID生成（正規化 URL の SHA-256 先頭32文字）を実装。
  - テキスト前処理（URL 除去・空白正規化）。
  - DB 保存はチャンク化して単一トランザクションで行い、INSERT ... RETURNING を用いて実際に挿入された記事 ID を返す（save_raw_news）。
  - 記事と銘柄コードの紐付け機能（extract_stock_codes、save_news_symbols、_save_news_symbols_bulk）を実装。既知銘柄セットのみを紐付け、重複を排除。
  - run_news_collection による統合収集ジョブを実装。各ソースは独立してエラーハンドリングし、失敗しても他ソースは継続。

- DuckDB スキーマと初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層を含む DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル、prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル、features / ai_scores（Feature 層）、signals / signal_queue / orders / trades / positions / portfolio_performance（Execution 層）を定義。
  - 頻出クエリに対するインデックスを定義。
  - init_schema(db_path) によりディレクトリ自動作成とテーブル作成（冪等）を行う関数を提供。get_connection() で既存 DB への接続を返す。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー等を集約）。
  - テーブル存在/最大日付取得ユーティリティ、営業日調整ヘルパー（_adjust_to_trading_day）を実装。
  - 差分更新の方針（最小単位: 営業日1日分、backfill_days による再取得）をサポート。
  - run_prices_etl を実装し、DB の最終取得日に基づく date_from 自動算出、J-Quants から取得して保存する流れを実現。
  - 品質チェック（quality モジュール）との連携を想定する構成（quality チェックは外部モジュールとして扱う）。

### Security
- RSS パーサに defusedxml を採用して XML に対する攻撃を軽減。
- RSS フェッチで SSRF 対策を実装（スキーム検証、プライベートアドレス検出、リダイレクト検査）。
- .env 読み込み時に OS 環境変数を保護する protected セットを導入し、意図しない上書きを防止。
- HTTP 429 の Retry-After ヘッダ優先、ネットワーク/HTTP エラーに対して慎重なリトライ設計を実施。

### Performance
- J-Quants API へのリクエストを固定間隔（120 req/min）でスロットリングして API 制限順守。
- トークンのモジュールレベルキャッシュによりページネーション間での再認証を削減。
- news_collector の DB インサートをチャンク化してパフォーマンスとパラメータ上限を抑制。
- DuckDB 用のインデックスを複数定義し、銘柄×日付パターンなどのクエリを最適化。

### Notes / Known limitations
- strategy, execution, monitoring パッケージは初期プレースホルダ。実際の売買戦略、注文実行、監視ロジックは別途実装が必要。
- quality モジュールは pipeline 側で参照する設計だが、具体的なチェック実装は外部に委ねられる（別実装が必要）。
- Python バージョン要件: モダンな型ヒント（`X | Y`）を使用しているため、Python 3.10 以降を想定。
- 外部依存: duckdb, defusedxml などが必要。

### Migration notes
- 初回リリースのため既存バージョンからの移行は不要。

[0.1.0]: https://example.com/releases/0.1.0 (初回公開)