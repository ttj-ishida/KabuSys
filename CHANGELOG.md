# Changelog

すべての注釈は Keep a Changelog の形式に準拠しています。  
このリポジトリの初期公開リリース v0.1.0 に基づいて、コードベースから推測される変更点・実装内容を日本語でまとめています。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-18
初期リリース

### Added
- パッケージ全体
  - kabusys パッケージを追加。モジュール構成は data, strategy, execution, monitoring を想定するエントリポイントを公開。
  - パッケージバージョンを 0.1.0 に設定。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機構を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env のパース処理を実装（export 形式対応、クォート処理、インラインコメント処理を考慮）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - OS 環境変数を保護する protected 上書き制御（.env.local は既存環境を上書きできるが protected は除外）。
  - 必須設定を取得する _require ヘルパーと、J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供。
  - KABUSYS_ENV と LOG_LEVEL の入力検証ロジックを追加（許容値の検査）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants API からのデータ取得を行うクライアントを実装。
  - 取得対象: 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー。
  - レート制限制御（120 req/min）を固定間隔スロットリング方式の _RateLimiter で実装。
  - リトライと指数バックオフを実装（最大 3 回、408/429/5xx 対象）。429 の場合は Retry-After ヘッダ優先。
  - 401 Unauthorized を受けた場合にリフレッシュトークンで自動的に id_token を更新して 1 回だけリトライ。
  - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を提供。
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）を行う save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。
  - 数値変換ユーティリティ（_to_float, _to_int）を追加し、入力の型や不正値を安全に扱う。
  - データ取得時の fetched_at（UTC）記録で Look-ahead Bias のトレーサビリティを確保。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集し raw_news テーブルに保存するモジュールを実装。
  - セキュリティ重視の実装:
    - defusedxml を使った XML パースで XML Bomb 等を防御。
    - SSRF 対策（外部アクセス時にホストがプライベート/ループバック/リンクローカルでないことを検査）。
    - リダイレクト時にもスキーム・ホストを検査するカスタム HTTPRedirectHandler を導入。
    - URL スキームは http/https のみ許可。
    - レスポンス受信サイズを最大 MAX_RESPONSE_BYTES（10 MB）で制限し、gzip 解凍後もチェック（Gzip bomb 対策）。
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保（utm_* などトラッキングパラメータを除去）。
  - テキスト前処理（URL 除去・空白正規化）のユーティリティを追加。
  - fetch_rss 関数は RSS の様々なレイアウト（content:encoded/namepace 等）に対応して記事抽出を行う。
  - DB 保存はチャンク分割・1トランザクションでのバルク INSERT を行い、INSERT ... RETURNING により実際に挿入された記事IDを返す（save_raw_news）。
  - 記事と銘柄コードの紐付け保存 utilities を提供（save_news_symbols / _save_news_symbols_bulk）。
  - 日本株銘柄コード抽出ユーティリティ extract_stock_codes を実装（4桁数字パターン + known_codes フィルタ）。
  - run_news_collection により複数ソースの収集、個別ソースのエラーハンドリング、銘柄紐付けの一括処理を実現。

- DuckDB スキーマ（kabusys.data.schema）
  - DataSchema.md に基づく DuckDB の DDL を実装し、3 層（Raw / Processed / Feature / Execution）を網羅したテーブル群を定義。
  - 定義済みテーブル（一部）:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な CHECK 制約、PRIMARY KEY、外部キー（news_symbols → news_articles、orders → signal_queue など）を定義。
  - 頻出クエリを想定したインデックス群を定義。
  - init_schema(db_path) によりディレクトリ作成とテーブル/インデックス作成を行う初期化関数を提供（冪等）。
  - get_connection(db_path) で既存 DB への接続を取得可能。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ベースの ETL パイプラインを実装。
  - 処理の方針:
    - DB の最終取得日を参照して差分（未取得分）だけを取得。
    - backfill_days により最終取得日の数日前から再取得して API の後出し修正を吸収（デフォルト 3 日）。
    - 市場カレンダーは先読み（_CALENDAR_LOOKAHEAD_DAYS = 90 日）。
    - 品質チェック（quality モジュール想定）を行い、重大度を識別。品質問題があっても ETL は全件継続して収集。
    - id_token を引数で注入可能にしてテスト容易性を確保。
  - ETL 実行結果を表す ETLResult dataclass を追加（品質問題やエラー概要を保持、辞書化機能あり）。
  - DB テーブル存在/最大日付取得ユーティリティを追加（_table_exists, _get_max_date）。
  - 価格 ETL run_prices_etl を実装（差分計算、fetch_daily_quotes → save_daily_quotes の呼び出し、結果ロギング）。

### Changed
- （初回リリースのため過去変更はなし）

### Fixed
- （初回リリースのため以前の不具合修正はなし）

### Security
- ニュース収集での強力な SSRF 対策を実装（リダイレクト検査・ホストのプライベート判定・スキーム検証）。
- defusedxml を利用した XML パースで XML 関連攻撃に対処。
- 外部 URL 読み込みに対するサイズ制限と gzip 解凍後の検査を導入して DoS/Gzip Bomb を緩和。
- .env 読み込みで OS 環境変数を保護する仕組みを導入（.env.local による上書き制御）。

### Performance
- J-Quants API 呼び出しに対する固定間隔レートリミッタを導入してレート制限順守。
- ニュース収集の DB 操作はチャンク化 & 単一トランザクションでバルク挿入を行いオーバーヘッドを削減。
- DuckDB での ON CONFLICT を利用した冪等保存により二重取り込みを防止。

### Documentation / その他
- 各モジュールの docstring に目的・設計方針・処理フローを記載しているため、実装意図が明示されている。
- ログ出力（logger）を各所に組み込み、運用時の可観測性を向上。

### Known issues / 注意点
- pipeline.run_prices_etl の最後で return 値のタプルが途中で切れている（ソース断片のため、不完全に見える箇所あり）。実装の続き・最終 return の確認が必要。
- quality モジュールは参照されているが、このコードベース内に含まれていない（別モジュールとして実装済みまたは今後追加が必要）。
- strategy, execution, monitoring パッケージの具体的実装は現状空の __init__.py のみで、実装は今後追加予定。

---

参考:
- バージョンはパッケージ内 __version__ = "0.1.0" に基づく初期公開リリースとして記載しています。
- 日付は本回答生成日（2026-03-18）を使用しています。必要に応じて調整してください。