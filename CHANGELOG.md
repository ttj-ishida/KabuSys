# Changelog

すべての変更は「Keep a Changelog」形式に従います。
このプロジェクトはセマンティックバージョニングを使用します。  

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システムの基盤となるコアモジュール群を追加しました。
主要な機能は下記の通りです。

### 追加
- パッケージ初期化
  - kabusys パッケージの公開バージョンを設定（__version__ = "0.1.0"）。
  - 公開モジュール一覧: data, strategy, execution, monitoring。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート判定は __file__ を基準に .git または pyproject.toml を探索（CWD に依存しない挙動）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
    - .env のパースは export 形式やクォート、インラインコメントに対応。
  - Settings クラスを提供（settings インスタンス経由で利用）。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須項目は未設定時に ValueError を送出。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の値検証を実装。
    - DB パス設定（DUCKDB_PATH, SQLITE_PATH）はデフォルト値を持つ（Path を expanduser して展開）。
    - is_live / is_paper / is_dev のヘルパープロパティを提供。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装（_request）。
    - レート制限: 120 req/min を満たす固定間隔スロットリング（_RateLimiter）。
    - リトライ: 指数バックオフで最大 3 回リトライ（対象: 408, 429, >=500）。
    - 401 応答時の自動トークンリフレッシュ（1回のみ）をサポート。
    - JSON デコードエラーやネットワークエラーに対するエラーハンドリング。
    - ページネーション対応（pagination_key を利用）。
  - 認証ヘルパー: get_id_token（リフレッシュトークンから id_token を取得）。
  - データ取得関数:
    - fetch_daily_quotes（株価日足 OHLCV、ページネーション対応）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices テーブル）
    - save_financial_statements（raw_financials テーブル）
    - save_market_calendar（market_calendar テーブル）
  - データ変換ユーティリティ: _to_float, _to_int（不正値や空値を安全に扱う）。
  - fetched_at に UTC タイムスタンプを付与して Look-ahead bias のトレースを可能に。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する一連の処理を実装。
  - セキュリティ・堅牢性強化:
    - defusedxml を使用して XML 関連攻撃（XML Bomb 等）に対処。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト先のスキーム/ホスト検査（_SSRFBlockRedirectHandler）、内部アドレス（プライベート/ループバック/リンクローカル/マルチキャスト）の拒否。
    - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）や gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding ヘッダを設定。
  - URL 正規化と記事 ID の生成:
    - トラッキングパラメータ（utm_* 等）を除去して正規化し、SHA-256（先頭32文字）で記事 ID を生成。
  - テキスト前処理: URL 除去、空白正規化（preprocess_text）。
  - RSS パース: content:encoded を優先、pubDate の RFC 形式パースとフォールバック時の現在時刻代替処理。
  - DB 保存:
    - save_raw_news: チャンク分割とトランザクションで INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事IDのみを返す。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの記事—銘柄紐付けをチャンク・トランザクションで保存し、実際に挿入された件数を返す。
  - 銘柄コード抽出:
    - 4桁数字パターン（日本株）を検出し、known_codes に含まれるもののみを返す（重複削除）。
  - run_news_collection: 複数ソースを順次処理し、各ソースは独立してエラーを扱う（1ソース失敗で他ソースに影響しない）。デフォルト RSS ソースに Yahoo Finance を含む。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataPlatform.md を想定した 3 層（Raw / Processed / Feature）＋Execution レイヤーのテーブルを定義。
  - 主要テーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型制約、CHECK 制約、PRIMARY/FOREIGN KEY を定義。
  - 頻出クエリ向けインデックスを作成（例: idx_prices_daily_code_date 等）。
  - init_schema(db_path) 実装:
    - 指定パスの親ディレクトリを自動作成し、すべての DDL とインデックスを実行して初期化（冪等）。
    - ":memory:" をサポート。
  - get_connection(db_path) で既存 DB への接続を提供（初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計・ユーティリティを実装（差分更新・バックフィル・品質チェック連携）。
  - ETLResult dataclass を実装（対象日、取得数/保存数、品質問題、エラーリストなどを保持）。品質問題は辞書化可能。
  - テーブル存在チェック、最終取得日の取得ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）を実装。
  - 市場カレンダーに基づいた営業日調整関数 (_adjust_to_trading_day) を実装。
  - run_prices_etl:
    - 差分更新ロジック: DB の最終取得日から backfill_days を考慮して date_from を自動算出。未取得時は最小データ日（2017-01-01）から取得。
    - J-Quants クライアントを利用してデータを取得し、保存関数で冪等保存を行う。
    - （品質チェックモジュールとの連携を想定。quality モジュールは別実装を想定）

### 変更
- 初版のため該当なし。

### 修正
- 初版のため該当なし。

### セキュリティ
- news_collector で XML パースに defusedxml を使用、SSRF 対策、内部ネットワークへのアクセス拒否、レスポンスサイズ制限、gzip 解凍時の追加チェックを実装。
- jquants_client の HTTP 呼び出しでタイムアウトと再試行を実装し、リトライ時に Retry-After ヘッダを尊重。

### 既知の制限 / 注意事項
- pipeline モジュールは ETL 全体の設計を含むが、quality モジュールの実装（欠損・スパイク検出など）は別モジュールとして想定される。ETLResult は品質チェック結果を格納する仕様になっている。
- strategy、execution、monitoring パッケージは __init__ のみであり、個別ロジックは未実装（今後拡張予定）。
- DuckDB の SQL 実行で直接文字列フォーマットを用いている箇所があるため（プレースホルダは用いているが注意が必要な箇所あり）、外部入力をそのまま SQL に組み込む場合は呼び出し元でのエスケープ/検証を推奨。

### 後方互換性（Breaking Changes）
- 初回リリースのため Breaking Changes はありません。

---
今後の予定（例）
- strategy / execution / monitoring の具体的実装追加
- quality モジュールの詳細実装と ETL への統合
- テストカバレッジと CI ワークフローの整備
- ドキュメント（DataPlatform.md 等）との同期・補強

お問い合わせや差分の提案があればお知らせください。