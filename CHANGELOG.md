CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の規約に従います。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

0.1.0 - 2026-03-18
-----------------

Added
- 初回リリース。日本株自動売買システムの基盤モジュール群を導入。
  - パッケージメタ情報
    - kabusys.__version__ = "0.1.0" を設定。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルまたは OS 環境変数から設定を自動ロード（プロジェクトルートを .git / pyproject.toml で探索）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パースの堅牢化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメントの扱い（クォート有無での挙動違い）。
  - Settings クラスを提供し、必須設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を必須として検証。
    - DUCKDB_PATH / SQLITE_PATH の既定値処理。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG / INFO / ...）。
    - is_live / is_paper / is_dev の補助プロパティ。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティを実装:
    - ベース URL とエンドポイント呼び出しを統一する _request() を提供。
    - レートリミッタ（120 req/min）を固定間隔スロットリングで実装。
    - 再試行ロジック（指数バックオフ、最大3回、対象: 408/429/5xx、429 の場合は Retry-After を尊重）。
    - 401 受信時はリフレッシュトークンで id_token を自動更新して 1 回だけリトライ（無限再帰を防止）。
    - JSON デコードエラー時の明示的エラー報告。
  - 認証: get_id_token(refresh_token) を提供（POST /token/auth_refresh）。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes（OHLCV 日足）
    - fetch_financial_statements（四半期 BS/PL）
    - fetch_market_calendar（JPX マーケットカレンダー）
    - 取得時の pagination_key を追跡して重複ページを防止。
  - DuckDB への保存関数（冪等性を考慮）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - fetched_at を UTC ISO 形式で記録し、Look-ahead-bias を防止するトレーサビリティを確保。
    - ON CONFLICT DO UPDATE により重複挿入を上書き（冪等）。
    - 主キー欠損行はスキップして警告ログを出力。
  - 型変換ユーティリティ:
    - _to_float / _to_int により不正値や空値を安全に None に変換。_to_int は "1.0" を許容するが小数部がある場合は None を返す。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得・前処理・DB 保存のフローを実装。
  - セキュリティ／堅牢性機能:
    - defusedxml を利用した XML パース（XML Bomb 等の防御）。
    - SSRF 防止: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバックであれば拒否。リダイレクト時も検査するカスタムハンドラを実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を実施しメモリ DoS を軽減。gzip 圧縮応答は解凍後にも上限チェック（gzip bomb 防止）。
    - User-Agent と Accept-Encoding を指定してリクエスト。
    - 受信の Content-Length を事前チェック。超過はスキップ。
  - URL 正規化・記事ID生成:
    - _normalize_url によりスキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）の除去、フラグメント除去、クエリソートを実施。
    - _make_article_id は正規化 URL の SHA-256 ハッシュ先頭32文字を記事IDとして生成（冪等性確保）。
  - テキスト前処理: URL 除去・空白正規化（preprocess_text）。
  - RSS パースの互換性を確保（channel/item の有無にフォールバック）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用い、実際に挿入された記事 ID を返却。チャンク化してトランザクションで処理。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けを一括挿入。重複除去・チャンク化・トランザクションを実施。INSERT ... ON CONFLICT DO NOTHING RETURNING を用いて実挿入数を正確に取得。
  - 銘柄コード抽出:
    - extract_stock_codes では正規表現で 4 桁数字を抽出し、known_codes セットと照合して重複を除去して返却。
  - run_news_collection: 複数ソースを独立して収集し、失敗したソースはスキップして全体処理を継続。新規挿入記事に対して銘柄紐付けを一括実行。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層 + Execution 層のテーブル定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切なカラム制約（CHECK、NOT NULL、PRIMARY KEY、外部キー）を付与。
  - 頻出クエリ向けのインデックスを複数定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) によりディレクトリ自動作成・全DDL/インデックス適用を行い、接続を返却。
  - get_connection(db_path) による既存 DB への接続サポート。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計方針に基づく初期実装:
    - ETLResult データクラス: 各種取得数、保存数、品質問題、エラー一覧を保持。品質問題はタプル形式で出力可能。
    - 差分更新ユーティリティ:
      - get_last_price_date / get_last_financial_date / get_last_calendar_date
      - _table_exists / _get_max_date による存在確認と最大日付取得。
    - 市場カレンダー補助: _adjust_to_trading_day により非営業日を直近営業日に調整（最大30日遡り）。
    - run_prices_etl の骨組み:
      - 最終取得日に基づく差分日付計算（_MIN_DATA_DATE, backfill_days の考慮）。
      - jquants_client.fetch_daily_quotes → save_daily_quotes を呼び出す流れを実装。
      - （品質チェックは別モジュール quality を想定する設計。）
  - 設計上のポイント:
    - 差分更新はデフォルトで営業日単位・backfill を組み込むことで API の後出し修正を吸収。
    - id_token を呼び出し元から注入可能でテスト容易性を確保。
    - 品質チェックは重大エラーがあっても ETL 本体は継続する（呼び出し元で判断）。

Security
- 複数箇所でセキュリティ対策を実施:
  - RSS の XML パースに defusedxml を使用。
  - SSRF 対策（スキーム検証、ホストのプライベート判定、リダイレクト時の検査）。
  - 外部入力（RSS 等）に対するサイズ上限と gzip 解凍後のサイズ検証。
  - DB のトランザクション処理で例外時にロールバックし一貫性を保護。

Deprecated
- なし

Removed
- なし

Fixed
- なし

Notes / Known limitations
- 現バージョンは初期実装。将来的には以下の強化を想定:
  - ETL の単体テスト用フック・モックの追加（現状は一部でモックの注入を想定した設計あり）。
  - quality モジュールの詳細実装と ETL との統合（pipeline は品質チェック呼び出しを想定）。
  - execution（発注）関連モジュールの実装拡張（パッケージ構成に空 __init__ が存在）。
- run_prices_etl 等のパイプライン処理は今後さらにカバレッジを拡充予定。

Authors
- 初期実装: 開発チーム

License
- プロジェクトの権利・ライセンス情報はリポジトリの LICENSE ファイルを参照してください。