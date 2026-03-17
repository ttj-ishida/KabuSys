# CHANGELOG

すべての重要な変更履歴をここに記載します。本プロジェクトは Keep a Changelog の慣例に準拠します。  
リリースは後方互換性の方針に従い、Breaking changes がある場合は明示します。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-17
初回リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。
  - モジュール公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを抑制可能。
  - .env パースの堅牢化:
    - export プレフィックス対応、コメント行スキップ、クォートおよびバックスラッシュエスケープ処理、インラインコメント処理などをサポート。
  - 環境変数の上書き制御（override）、OS環境変数保護（protected）をサポート。
  - Settings クラスを導入し、J-Quants / kabu API / Slack / データベースパス 等のプロパティおよびバリデーションを提供。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）。
    - デフォルトの DB パス（DuckDB / SQLite）の既定値を提供。
    - is_live / is_paper / is_dev ヘルパープロパティを追加。

- J-Quants クライアント (kabusys.data.jquants_client)
  - API クライアントを実装（ベース URL: https://api.jquants.com/v1）。
  - レート制限対応: 固定間隔スロットリング（_RateLimiter）で 120 req/min を遵守。
  - リトライロジック: 指数バックオフ、最大 3 回のリトライ（408, 429, 5xx を考慮）。429 の場合は Retry-After ヘッダを優先。
  - 401 応答時のトークン自動リフレッシュを実装（1 回のみリフレッシュして再試行）。
  - ID トークンのモジュール内キャッシュ（ページネーション間で共有）。
  - ページネーション対応の取得関数を実装:
    - fetch_daily_quotes（株価日足/OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPXマーケットカレンダー）
  - DuckDB に冪等的に保存する関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ取り込み時に fetched_at を UTC ISO8601 形式で付与し、取得時点を記録（Look-ahead Bias 対策）。
  - 値変換ユーティリティを実装:
    - _to_float（空文字・不正値を None に）
    - _to_int（"1.0" を int に変換、非整数小数は None を返す）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を安全に収集する機能を実装（デフォルトに Yahoo Finance のビジネス RSS を設定）。
  - セキュリティ対策:
    - defusedxml を使った XML パース（XML Bomb 等に対する防御）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先のスキーム/ホスト検査、プライベートアドレス判定（IP と DNS 解決を利用）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_ 等を削除）、ハッシュ化で記事 ID を生成（SHA-256 の先頭32文字）。
  - テキスト前処理（URL 除去、空白正規化）。
  - RSS 取得関数 fetch_rss はエラー分離（1ソースの失敗が全体に影響しない）。
  - DuckDB への保存はトランザクションでまとめ、INSERT ... RETURNING を使って実際に挿入された行を返す実装:
    - save_raw_news（raw_news へ保存し新規ID一覧を返す）
    - save_news_symbols / _save_news_symbols_bulk（news_symbols への紐付けを一括保存して実挿入数を返す）
  - 銘柄コード抽出機能（テキストから4桁の銘柄コードを抽出し、known_codes によるフィルタリングを行う）。
  - run_news_collection により複数 RSS ソースを巡回して保存・銘柄紐付けを行う。

- スキーマ定義と初期化 (kabusys.data.schema)
  - DuckDB 用のスキーマを DataPlatform 設計（Raw / Processed / Feature / Execution 層）に従って実装。
  - テーブル群（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）を定義。
  - 各テーブルに制約（PRIMARY KEY, CHECK, FOREIGN KEY 等）を付与。
  - 代表的なインデックスを作成（頻出クエリ向け）。
  - init_schema(db_path) で親ディレクトリ自動作成後に DDL を実行してスキーマを初期化する関数を提供。get_connection で既存 DB に接続可能。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計に基づく差分更新処理の基礎を実装。
  - ETLResult データクラスを実装（取得数、保存数、品質問題一覧、エラー一覧などを保持）。
  - テーブル存在チェック、最大日付取得ヘルパーを提供（_table_exists, _get_max_date）。
  - 市場カレンダーに基づく営業日調整関数 _adjust_to_trading_day を実装（過去 30 日まで探索）。
  - 差分更新用の最終取得日取得関数を実装（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - run_prices_etl を実装（差分取得、backfill_days のサポート、jquants_client による取得と保存）。（注: このリリースでは prices ETL の実装が含まれており、さらなる ETL ジョブは順次追加予定）

### 変更 (Changed)
- 該当なし（初回リリース）

### 修正 (Fixed)
- 該当なし（初回リリース）

### セキュリティ (Security)
- RSS パーサで defusedxml を使用、SSRF の多層防御（スキーム検証・リダイレクト検査・プライベートアドレス検出）を導入。
- .env ローダーでファイル読み込み失敗時に warnings を出すなど堅牢化。

### 使い方メモ / 移行ノート
- DB を初めて利用する場合は、kabusys.data.schema.init_schema(settings.duckdb_path) を実行してスキーマを作成してください。
- 環境変数はプロジェクトルートの .env/.env.local から自動読み込みされます。テストなどで自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API 呼び出しは内部で自動的にトークンをリフレッシュしますが、トークン取得処理は get_id_token へ明示的に refresh_token を渡して呼ぶこともできます（テスト時の注入に利用可能）。
- 単体テストでは news_collector._urlopen をモックして HTTP 層を差し替えることで SSRF ハンドラなどを回避できます。
- ETLResult と pipeline の各関数はエラーを集約して返す設計になっているため、呼び出し側でログや外部通知（例: Slack）を行うことを想定しています。

### 既知の制約 / 今後の予定
- strategy, execution, monitoring の実装はパッケージ内にモジュール定義があるが、このリリースでは具象実装は含まれていない（今後実装予定）。
- pipeline の一部（例: 品質チェック quality モジュールの呼び出し箇所、その他 ETL ジョブの詳細）はこのバージョンでの骨格実装に留まっているため、品質チェックルールや追加 ETL は継続的に拡張予定。
- J-Quants API のエンドポイント追加やデータスキーマ拡張に伴うスキーマ変更は将来のマイナーバージョンで行います。DDL 変更はマイグレーションを伴う可能性があります。

---

貢献・問い合わせ: リポジトリの issue を作成してください。