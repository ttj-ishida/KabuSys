CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠します。

Unreleased
----------

- 既知の問題
  - data.pipeline.run_prices_etl が想定される (int, int) タプルのうち 2 番目の値を返していません（現状は単一要素のタプルを返す実装）。呼び出し側でのアンパック時や型期待値と矛盾するため修正が必要です。
  - strategy/ および execution/ パッケージは __init__.py が存在するのみで実装がありません（将来的な追加予定）。

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - src/kabusys/__init__.py にバージョン定義（__version__ = "0.1.0"）と公開モジュール一覧の定義。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を上位ディレクトリから検索）により CWD 非依存でのロードを実現。
  - .env と .env.local の読み込み順（OS 環境変数を最優先、.env.local が .env を上書き）を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加（テスト目的）。
  - 値のパースでシングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - settings オブジェクト（Settings クラス）を公開し、以下の設定プロパティを提供（必須チェックおよび妥当性検証を含む）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV 値検証（development, paper_trading, live）
    - LOG_LEVEL 値検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する関数を実装:
    - fetch_daily_quotes (ページネーション対応)
    - fetch_financial_statements (ページネーション対応)
    - fetch_market_calendar
  - トークン管理:
    - get_id_token (refresh token → idToken)
    - モジュールレベルキャッシュを用いた id_token の共有／自動リフレッシュ機構（401 を受けた際に1回リフレッシュして再試行）
  - HTTP リクエストユーティリティ _request:
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）
    - リトライ（指数バックオフ、最大 3 回）、408/429/5xx に対する再試行、429 の Retry-After ヘッダ尊重
    - JSON デコードエラー時の明示的なエラーメッセージ
  - DuckDB への冪等保存関数:
    - save_daily_quotes（raw_prices、ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials、ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar、ON CONFLICT DO UPDATE）
  - データ変換ユーティリティ: _to_float, _to_int（空値や不正フォーマットに寛容で安全に None を返す）

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得と前処理、DuckDB への保存処理を実装:
    - fetch_rss: RSS 取得、XML パース、コンテンツ正規化、記事リストを返す
    - save_raw_news: raw_news へチャンク挿入（INSERT ... RETURNING で挿入された id を返す）、トランザクション管理
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への記事と銘柄の紐付け（チャンク挿入、RETURNING を利用して実際に挿入された件数を返す）
    - extract_stock_codes: テキストから 4 桁銘柄コードを抽出（known_codes フィルタ適用）
    - run_news_collection: 複数 RSS ソースの統合ジョブ（各ソースは独立してエラーハンドリング）
  - セキュリティと堅牢性:
    - defusedxml による XML パース（XML Bomb 等への対策）
    - SSRF 対策: URL スキーム検証、プライベートアドレス判定、リダイレクト検査を行う _SSRFBlockRedirectHandler と _is_private_host
    - 最大受信バイト数上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）
    - トラッキングパラメータ削除および URL 正規化（_normalize_url、_make_article_id による SHA-256 ベースの記事 ID 生成）
    - レスポンス Content-Length の事前チェック、HTTP ヘッダに対する堅牢な処理
  - テキスト前処理: URL 除去・空白正規化（preprocess_text）
  - 公開型 NewsArticle（TypedDict）を利用

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層を含むスキーマ DDL を網羅的に定義:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY / FOREIGN KEY / CHECK）やインデックスを定義し、頻出クエリを考慮したインデックス群を作成
  - init_schema(db_path) により DB ファイル親ディレクトリ自動作成からテーブル作成・インデックス作成までを一括実行（冪等）
  - get_connection(db_path) による既存 DB への接続取得（初期化は行わない）

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新（差分取得）と保存のワークフローを実装するためのユーティリティ群:
    - ETLResult データクラス（品質問題やエラーの集約、辞書出力）
    - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists, _get_max_date）
    - 市場カレンダーを参照した営業日調整ヘルパー（_adjust_to_trading_day）
    - raw_prices / raw_financials / market_calendar の最終取得日を取得する関数（get_last_price_date, get_last_financial_date, get_last_calendar_date）
    - run_prices_etl の枠組み（差分計算、backfill_days と _MIN_DATA_DATE に基づく初回ロード方針、jquants_client の fetch/save の呼び出し）
  - 設計方針:
    - 差分更新のデフォルトは「営業日1日分」、backfill_days による後出し修正吸収
    - 品質チェックは別モジュール（quality）と連携して問題を収集し、ETL の継続性を優先

- その他
  - モジュールや関数に対する詳細な docstring（設計意図・前提・例外条件）を多数追加し、可読性・保守性を向上。
  - テスト容易性を考慮したフック（例: news_collector._urlopen のモック差し替え想定）。

Security
- XML パースに defusedxml を導入し、XML ベースの攻撃に対する耐性を確保。
- ニュース取得での SSRF 対策を実装（スキーム検査、プライベート IP 判定、リダイレクト検査）。
- .env 読み込みで OS 環境変数を保護する protected 機構を導入。

Known issues / Notes
- run_prices_etl の戻り値が期待される (int, int) に揃っていない（Unreleased 欄に記載）。ETL の呼び出し元でのアンパック等に影響があります。
- strategy モジュール、execution モジュール本体は未実装（インターフェースの追加が必要）。
- quality モジュールの参照はあるが、本コードベースに実装（抜粋内）は含まれていません。品質チェックの実装／統合が必要。
- DuckDB の SQL を直接組み立てる箇所があり（プレースホルダを使っているが長いプレースホルダ列の生成あり）、将来的に SQL 注入やパフォーマンスを見直す可能性あり（現状は内部 DB での使用想定のためリスクは限定的）。

Migration notes
- 既存の利用者は .env の自動読み込みに依存する場合、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して挙動を制御できます。
- DuckDB の初期化は init_schema() を明示的に呼ぶことを推奨します（get_connection() は初期化を行いません）。

Authors
- コードベースに含まれるドキュメント文字列に基づく要約を作成しました。

---

このCHANGELOGは、提供されたソースコードの内容から機能・設計上の差分・既知問題を推測して作成しています。実際のリリースノートには、コミット履歴や実際の変更差分に基づく追加情報（バグ修正の詳細、依存関係のバージョン、マイグレーション手順など）を適宜追記してください。