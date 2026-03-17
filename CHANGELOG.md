# Changelog

すべての変更は Keep a Changelog の形式に準拠し、Semantic Versioning を意識しています。  

なお、本CHANGELOGは提供されたソースコードから実装内容を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-17
初期リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョン管理（__version__ = "0.1.0"）と公開モジュールを定義（data, strategy, execution, monitoring）。
- 環境変数 / 設定管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダーを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
  - Settings クラス: J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite）/実行環境（development/paper_trading/live）/ログレベル等のプロパティを提供。必須キー未設定時は ValueError を送出。
- J-Quants クライアント（kabusys.data.jquants_client）
  - API 接続基盤を実装。共通設計方針としてレート制限（120 req/min）、リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ、ページネーション対応、取得時刻（fetched_at）による Look-ahead Bias トレース、DuckDB への冪等保存（ON CONFLICT）を導入。
  - 固定間隔のレートリミッタ実装。
  - id_token のモジュールキャッシュと強制リフレッシュ対応。
  - 汎用 HTTP リクエスト関数（_request）：JSON デコードエラー・HTTP エラー・ネットワークエラーのハンドリング、429 の Retry-After 優先処理等を実装。
  - get_id_token(): リフレッシュトークンから ID トークン取得（POST）。
  - データ取得関数:
    - fetch_daily_quotes(): 株価日足（OHLCV）をページネーション対応で取得。
    - fetch_financial_statements(): 四半期財務（BS/PL）をページネーション対応で取得。
    - fetch_market_calendar(): JPX マーケットカレンダー取得。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes(): raw_prices へ ON CONFLICT DO UPDATE で保存。
    - save_financial_statements(): raw_financials へ ON CONFLICT DO UPDATE で保存。
    - save_market_calendar(): market_calendar へ ON CONFLICT DO UPDATE で保存。
  - ユーティリティ: 値変換ヘルパー _to_float / _to_int（曖昧な数値表現を安全に扱うロジック）。
- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからニュースを収集して raw_news に保存する処理を実装（DataPlatform.md に基づく設計）。
  - セキュリティ・堅牢性のための対策を実装:
    - defusedxml を利用して XML Bomb 等を防御。
    - HTTP/HTTPS 以外のスキームは拒否して SSRF を緩和。
    - リダイレクト時にスキームとプライベートアドレスを検査するカスタム RedirectHandler を導入（リダイレクト先の内部アドレス到達をブロック）。
    - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検査を追加（メモリ DoS 対策）。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば接続拒否。
  - フィード処理:
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリキーのソート）。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）。
    - fetch_rss(): RSS 取得・パース・記事生成（content:encoded を優先）。
  - DB 保存:
    - save_raw_news(): チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用し、実際に挿入された記事 ID のリストを返す。1 トランザクションでの挿入、エラー時ロールバック。
    - save_news_symbols(): 個別記事の銘柄紐付けを INSERT ... RETURNING で実行。
    - _save_news_symbols_bulk(): 複数記事分を一括保存する内部ユーティリティ（重複排除、チャンク挿入、トランザクション）。
  - 銘柄コード抽出:
    - extract_stock_codes(): テキスト中の 4 桁数字を候補に、与えられた known_codes セットと照合して有効な銘柄コードのみ返す（重複除去）。
  - 統合収集ジョブ:
    - run_news_collection(): 複数 RSS ソースを順次処理し、raw_news に保存、新規挿入記事に対して銘柄紐付けを一括挿入する。各ソースは独立して例外処理し、1 ソース失敗でも他ソースを継続。
    - デフォルト RSS ソースとして Yahoo Finance のビジネス RSS を定義。
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataSchema.md に基づく多層スキーマを作成する DDL を実装（Raw / Processed / Feature / Execution 層）。
  - 主要テーブルを定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 型制約・CHECK 制約・外部キーを含む堅牢なスキーマ設計。
  - パフォーマンスを考慮したインデックス定義を多数用意。
  - init_schema(db_path) でディレクトリ作成（必要時）・テーブル作成（冪等）・インデックス作成を行い DuckDB 接続を返す。get_connection() で既存 DB へ接続可能。
- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETL の設計方針（差分更新、backfill、品質チェックと非 Fail-Fast の動作、テスト容易性のための id_token 注入）を実装。
  - ETL 実行結果を表す ETLResult データクラスを追加（品質問題の要約、エラー一覧、シリアライズ用 to_dict）。
  - テーブル存在チェック、最終取得日取得ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）を実装。
  - 市場カレンダー補正ヘルパー（_adjust_to_trading_day）を実装。
  - run_prices_etl(): 差分更新ロジック（最終取得日に基づく date_from 自動算出、backfill_days を考慮）と J-Quants からの取得→保存フローを実装（fetch_daily_quotes と save_daily_quotes を使用）。（ファイル末尾は一部実装が継続する形で提供されています）
- 型ヒント・ロギング・ドキュメント文字列
  - 主要関数に型ヒント、docstring を付与し設計意図を明記。
  - ロガーを活用した情報・警告・例外ログを配置。

### Security
- RSS パーサで defusedxml を採用して XML 脅威を軽減。
- URL/リダイレクト検証とプライベートアドレス検査により SSRF を緩和。
- 外部通信関係でタイムアウトやレスポンスサイズ上限を設定して DoS・リソース枯渇に対処。
- .env 読み込みでは OS 環境変数保護（protected set）を設け、明示的に override が行われない限り上書きしない設計。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Known issues / Notes
- pipeline.run_prices_etl の実装はファイル末尾が途中で切れているため、完全な ETL ワークフロー（品質チェック呼び出しや結果集約等）は継続実装が必要です。
- strategy, execution, monitoring パッケージはパッケージ階層として存在するものの、現時点の提供コードでは具象実装は未追加です。
- 外部 API（J-Quants / kabuステーション / Slack 等）の実運用接続や認証設定は環境変数が必須です。README や .env.example による導入ドキュメントが必要です。

---

作成・更新履歴やリリースノートの粒度は将来のコミットに応じて Unreleased セクションに追記してください。