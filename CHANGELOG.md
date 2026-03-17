CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベース（src/kabusys 以下）の内容から推測して作成しています。

フォーマット:
- Unreleased: 将来的に修正予定の既知の問題や作業中の項目
- 各バージョンには追加（Added）、変更（Changed）、修正（Fixed）、セキュリティ（Security）などのカテゴリで記載

Unreleased
----------
- Known issue: ETL パイプラインの run_prices_etl の戻り値処理が途中で切れており（len(records), のまま）意図した saved 値が返らない可能性あり。次リリースで修正予定。
- TODO: pipeline モジュール内で他の ETL ジョブ（financials, calendar 等）の実装を追加し、全体の統合テストを充実させる予定。
- TODO: quality モジュールの依存と品質チェックの挙動（重大度ハンドリング）に関するドキュメント整備。

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加し、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 環境設定管理モジュール（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を自動的に読み込む機能を実装。
  - プロジェクトルートを .git または pyproject.toml から探索する _find_project_root を実装し、カレントディレクトリに依存しない自動読み込みを実現。
  - .env と .env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。.env の上書き／保護ロジック（protected set）を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - 必須設定を取得して未設定時に例外を投げる _require を実装。
  - env（development/paper_trading/live）と LOG_LEVEL の検証ロジック、各種パス（DUCKDB_PATH, SQLITE_PATH）プロパティを提供。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、四半期財務データ、マーケットカレンダー等の取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - レート制御: 固定間隔スロットリングで 120 req/min 制限を守る _RateLimiter を実装。
  - リトライロジック: 指数バックオフ・最大 3 回（対象ステータス 408, 429, 5xx）、429 の Retry-After を優先。
  - 401 Unauthorized 受信時に自動トークンリフレッシュ（get_id_token）を行い 1 回だけリトライする安全策を実装。
  - ページネーション対応（pagination_key を用いた取得ループ）。
  - DuckDB への保存用関数を提供（save_daily_quotes, save_financial_statements, save_market_calendar）。いずれも冪等（ON CONFLICT DO UPDATE）で重複や更新を処理。
  - データ型変換ユーティリティ（_to_float, _to_int）を実装し、不正値や空値を適切に扱う。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news テーブルへ保存する処理を実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 等への対策）。
    - SSRF 対策: リダイレクト時のスキーム/ホスト検証を行うカスタムハンドラ（_SSRFBlockRedirectHandler）、ホストがプライベート/ループバックかどうかを判定する _is_private_host を実装。
    - URL スキーム検証（http/https のみ）、受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）によるメモリ DoS 対策、gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - データ品質/冪等性:
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
    - トラッキングパラメータ（utm_*, fbclid 等）を除去する URL 正規化を実装。
    - DB 保存はチャンク分割（_INSERT_CHUNK_SIZE）とトランザクションでまとめ、INSERT ... RETURNING を利用して実際に挿入された件数を返す。
  - テキスト前処理（URL 除去・空白正規化）と銘柄コード抽出（4桁数字、known_codes フィルタ）を実装。
  - run_news_collection により複数 RSS ソースの独立した取得処理と、取得済記事に対する銘柄紐付けを一括で行うワークフローを実装。
- DuckDB スキーマ定義 & 初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層に渡るテーブル群の DDL を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY）を設定し、頻出クエリ向けのインデックスを用意。
  - init_schema(db_path) でディレクトリ作成から全テーブル・インデックスの作成までを行い、冪等に初期化できるように実装。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult dataclass を導入し、ETL 実行結果（取得件数・保存件数・品質問題・エラーメッセージ）を一元化。
  - 差分更新のためのユーティリティ（テーブル存在チェック、テーブルの最終日付取得）を実装。
  - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）を実装。
  - run_prices_etl を実装（差分更新ロジック、backfill_days による後出し修正の吸収、jq.fetch_daily_quotes / jq.save_daily_quotes の利用）。
  - 設計方針の文書化（差分更新、バックフィル、品質チェックは Fail-Fast にならない等）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- news_collector において SSRF、XML Bomb、Gzip Bomb、メモリ DoS、トラッキングパラメータなど複数の攻撃ベクタに対する防御を実装。
- J-Quants クライアントはトークン自動リフレッシュ・リトライ・レート制御を組み込み、API 呼び出し失敗に対する堅牢性を高める設計。

Notes / 補足
- 外部依存: defusedxml, duckdb が利用されている（環境にインストールが必要）。
- jquants_client は urllib を用いているため、将来セッション管理や接続再利用（requests/HTTPX への移行）を検討する余地あり。
- pipeline モジュールは品質チェック（quality モジュール）を呼び出す設計になっているが、quality の実装や ETL の他ジョブ（財務・カレンダー等）の完全な統合テストはまだ必要。
- テスト用の差し替えポイントを設けており（例: news_collector._urlopen をモック可能）、単体テストの作成が容易な構造になっている。

作者注
- この CHANGELOG はソースコードから推測して作成したものであり、実際の変更履歴や履歴管理方法と差異がある場合があります。必要に応じて日付や項目を調整してください。