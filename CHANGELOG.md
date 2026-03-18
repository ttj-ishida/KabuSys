CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

[0.1.0] - 2026-03-18
--------------------

Added
- パッケージの初期バージョンを追加。
  - パッケージ名: kabusys、バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動読み込み機能を追加。
    - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行われ、CWD に依存しない挙動。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env、既存 OS 環境変数は protected として上書きから保護。
  - .env パーサを実装（_parse_env_line）
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱い等に対応。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / システム設定等のプロパティを提供。
    - 必須変数未設定時は ValueError を送出する _require を実装。
    - KABUSYS_ENV の値検証（development/paper_trading/live）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティ（_request）を実装。
    - 固定間隔レートリミッタ（120 req/min）を実装（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回）。429 の場合は Retry-After を優先。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライする仕組みを実装（無限再帰防止）。
    - JSON デコードエラーやネットワークエラーの取り扱いを整備。
    - ページネーション対応。モジュールレベルの ID トークンキャッシュを共有（_get_cached_token）。
  - 認証補助関数 get_id_token を実装（refresh token から idToken を取得）。
  - データ取得関数を追加:
    - fetch_daily_quotes (株価日足、ページネーション対応)
    - fetch_financial_statements (四半期財務データ、ページネーション対応)
    - fetch_market_calendar (JPX マーケットカレンダー)
  - DuckDB への保存関数を追加（冪等性を考慮した ON CONFLICT ロジック）:
    - save_daily_quotes: raw_prices に保存し fetched_at を UTC で記録
    - save_financial_statements: raw_financials に保存
    - save_market_calendar: market_calendar に保存（取引日/半日/SQ 判定）
  - 値変換ユーティリティ _to_float / _to_int を実装し、空値や不正値の安全な扱いを実現。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事取得と DuckDB への保存を実装。
  - セキュリティ・堅牢性対策:
    - defusedxml を利用して XML Bomb 等に対処。
    - SSRF 対策: HTTP リダイレクト時にスキーム検証とプライベートアドレス検査を行うハンドラ実装（_SSRFBlockRedirectHandler）。
    - URL スキームは http/https のみ許可。ホストがプライベートアドレスの場合は拒否。
    - 受信サイズ上限(MAX_RESPONSE_BYTES=10MB) と gzip 解凍後のサイズ検査を実装（メモリ DoS 対策）。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）を利用し冪等性を担保（utm_* 等のトラッキングパラメータ除去）。
  - クレンジング / 前処理:
    - URL 除去・空白正規化を行う preprocess_text。
    - RSS pubDate のパース（_parse_rss_datetime）と UTC 正規化。
    - URL 正規化関数 _normalize_url を提供（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリソート）。
  - DB への高性能保存:
    - save_raw_news: INSERT ... RETURNING id を用いて実際に挿入された記事IDのみ返す（チャンク処理、トランザクションでまとめる）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けを一括挿入（重複排除、RETURNING を利用）。
  - 銘柄コード抽出:
    - extract_stock_codes を実装。4桁数字パターンを抽出し、known_codes に含まれるもののみを返す。
  - 統合収集ジョブ run_news_collection を実装。各ソース個別にエラーハンドリングし、既知銘柄との紐付けを行う。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataSchema.md に基づく三層（Raw / Processed / Feature / Execution）スキーマを実装。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル定義を追加。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed テーブル定義を追加。
  - features, ai_scores などの Feature レイヤーテーブルを追加。
  - signals, signal_queue, orders, trades, positions, portfolio_performance などの Execution レイヤーテーブルを追加。
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）およびインデックスを定義。
  - init_schema(db_path) を実装し、ディレクトリ自動作成と DDL の冪等実行で初期化を行う。
  - get_connection(db_path) を提供（既存 DB への接続。初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計に基づく差分更新／品質チェックフレームワークを実装（部分的）。
  - ETLResult データクラスを実装（取得数、保存数、品質問題、エラーの集約）。
    - quality_issues を整形して辞書化する to_dict を提供。
  - market_calendar の先読み等の定数を定義（_CALENDAR_LOOKAHEAD_DAYS 等）。
  - テーブル存在チェックおよび最大日付取得ユーティリティを実装（_table_exists, _get_max_date）。
  - 取引日の調整ヘルパー _adjust_to_trading_day を実装（非営業日の補正、30 日遡りのフォールバック）。
  - 差分更新ヘルパー関数:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
  - run_prices_etl を実装（差分 ETL、backfill_days による再取得、J-Quants から取得して DuckDB に保存）。

Changed
- 初期リリースのため、特に既存機能の変更はなし（n/a）。

Fixed
- 初期リリースのため、既知のバグ修正歴はなし（n/a）。

Security
- news_collector にて以下のセキュリティ対策を実装:
  - defusedxml による XML パース硬化。
  - SSRF 対策（リダイレクト先のスキーム/プライベートホスト検査、初期 URL のホスト検査）。
  - レスポンスサイズ制限および gzip 解凍後のサイズチェック（Gzip bomb 対策）。
- jquants_client の HTTP ロジックでタイムアウトと再試行制御、Retry-After の尊重、401 リフレッシュ戦略を実装し、安定性を向上。

Notes / Implementation details
- 多くの DB 保存ロジックは冪等性を重視しており、ON CONFLICT DO UPDATE / DO NOTHING を用いて重複や上書きを扱う。
- 日時の fetched_at は UTC で記録して Look-ahead Bias を防止可能な形でトレースできるようにしている。
- ネットワーク要求にはタイムアウトや再試行、レートリミット（固定間隔）を組み合わせ、外部 API の制限に準拠する設計を採用。
- pipeline モジュールは品質チェック（quality モジュール）と連携する設計になっており、品質問題は収集を止めず呼び出し側での判断を想定。

破壊的変更
- 初回リリースのため、破壊的変更はなし。

Acknowledgements
- 初期実装（データ収集・保存・ETL 基盤）を含む広範な機能群を追加。今後、テストカバレッジの拡充・ドキュメント整備・品質チェックルールの実装が推奨されます。