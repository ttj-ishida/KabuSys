CHANGELOG
=========

すべての目立った変更はこのファイルに記載します。本ファイルは "Keep a Changelog" のフォーマットに準拠しています。  

※このCHANGELOGはリポジトリ内のコードから推測して作成した初期の変更履歴です。

Unreleased
----------

- なし

0.1.0 - 2026-03-18
------------------

追加 (Added)
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ名/バージョンは src/kabusys/__init__.py にて設定（__version__ = "0.1.0"）。
  - パッケージの公開 API を __all__ により data, strategy, execution, monitoring として宣言。

- 環境設定管理モジュール (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に __file__ を起点として探索（CWD非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - .env パーサーは export KEY=val 形式、クォート付き値、インラインコメント、エスケープシーケンスに対応。
  - 必須変数取得用の _require と Settings クラスを提供。Settings は下記のプロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証あり）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証あり）
    - is_live / is_paper / is_dev のヘルパー

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 基礎機能:
    - 株価日足 (OHLCV)、財務データ（四半期 BS/PL）、JPX 市場カレンダーを取得する fetch_* 関数を実装。
    - ページネーション対応（pagination_key を連続して取得）。
  - レート制御とリトライ:
    - 固定間隔スロットリングで 120 req/min を厳守（_RateLimiter）。
    - 再試行ロジック: 指数バックオフ、最大 3 回、ステータス 408/429/5xx を対象。429 の場合は Retry-After を優先。
    - 401 受信時はリフレッシュ（get_id_token）して 1 回だけ再試行（無限再帰防止の allow_refresh フラグ）。
    - ID トークンのモジュールレベルキャッシュをサポートしページネーション間で共有。
  - DuckDB への保存関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar: ON CONFLICT を使った冪等保存（INSERT ... ON CONFLICT DO UPDATE）。
    - PK 欠損行のスキップとログ出力。
  - 入力パース補助:
    - _to_float / _to_int は空値や非数を安全に None に変換。_to_int は "1.0" のような float 文字列を許容し、小数部がある場合は None を返す。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する機能を提供:
    - fetch_rss: RSS 取得、XML パース、記事抽出（title/content/link/pubDate）、前処理、返却。
    - save_raw_news: INSERT ... RETURNING を使って新規挿入された記事IDのリストを返す（チャンク挿入、トランザクションまとめ）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを冪等に保存（ON CONFLICT DO NOTHING、INSERT RETURNING により正確な挿入数を返す）。
    - run_news_collection: 複数 RSS ソースからの統合ジョブ。各ソースは独立してエラーハンドリングするため、一部失敗しても続行する。
  - セキュリティ・堅牢性対策:
    - defusedxml を利用して XML Bomb 等の攻撃を軽減。
    - SSRF 対策:
      - リダイレクト時にスキームと最終ホストが http/https かつプライベートアドレスでないかを検査するハンドラを導入（_SSRFBlockRedirectHandler）。
      - 初回接続前に URL のホストがプライベートでないかを事前検証（_is_private_host）。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10 MB) を適用し、読み取り時にもオーバーならスキップ。gzip 圧縮レスポンスは解凍後のサイズも検証（Gzip bomb 対策）。
    - URL スキーム検証: http/https のみ許可。
  - 前処理・正規化:
    - URL 正規化 (_normalize_url): スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）削除、フラグメント除去、クエリキーソート。
    - 記事ID は正規化 URL の SHA-256 の先頭32文字で生成（冪等性を担保）。
    - テキスト前処理 preprocess_text: URL 除去、連続空白を単一スペース化、トリム。
    - 日付パース (_parse_rss_datetime): RFC2822 形式を UTC naive datetime に変換。パース失敗時は警告を出して現在時刻で代替（raw_news.datetime は NOT NULL）。
    - 銘柄コード抽出 extract_stock_codes: 正規表現で4桁数字を抽出し、known_codes によるフィルタおよび重複除去を実装。
  - デフォルト RSS ソースを定義（例: yahoo_finance）。

- スキーマ定義・初期化モジュール (kabusys.data.schema)
  - DuckDB 用のスキーマ定義を提供し、init_schema() で必要なテーブル/インデックスを生成:
    - Raw, Processed, Feature, Execution 層に分けたテーブル群を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
    - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックスも定義。
    - init_schema は :memory: をサポートし、ファイルを使う場合は親ディレクトリを自動作成する。
    - get_connection は既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新・バックフィル設計:
    - run_prices_etl 等の差分 ETL を想定したユーティリティを実装（コード内に run_prices_etl の冒頭実装あり）。
    - 最終取得日から backfill_days (デフォルト 3 日) 前から再取得して API の後出し修正を吸収する設計。
    - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）や Naive な最小データ日付 (_MIN_DATA_DATE = 2017-01-01) を使用。
  - ETL 結果表現:
    - ETLResult dataclass を導入し、取得件数、保存件数、品質問題（quality.QualityIssue のリスト）、エラーの一覧を格納。has_errors / has_quality_errors / to_dict() を提供。
  - DB ヘルパー:
    - テーブル存在チェック、最大日付取得 (get_last_price_date, get_last_financial_date, get_last_calendar_date)、営業日調整ヘルパー（_adjust_to_trading_day）を提供。

変更 (Changed)
- なし（初期リリースのため機能追加中心）

修正 (Fixed)
- なし（初期リリースのため機能追加中心）

セキュリティ (Security)
- news_collector にて以下を実装して SSRF/XML 攻撃を軽減:
  - defusedxml 使用、リダイレクト先スキーム/ホスト検証、プライベートIPチェック、レスポンスサイズ制限、gzip 解凍後サイズチェック。

既知の注意点 / マイグレーション (Notes / Migration)
- init_schema() は既存スキーマとの互換性チェックは行わない。スキーマ定義を変更した場合、既存データとの衝突に注意してください。
- settings にて必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）が未設定だと ValueError を送出します。テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを抑制できます。
- J-Quants API のレート制限・リトライに関する実装はクライアント側で制御を行いますが、API 制限や挙動変更によりさらなる調整が必要になる可能性があります。
- news_collector の extract_stock_codes は known_codes を参照して4桁コードのみを有効とするため、known_codes の保持更新が重要です。

開発者向け (Developer notes)
- テスト容易性:
  - news_collector の HTTP オープナー（_urlopen）をモックして外部アクセスを置き換え可能。
  - jquants_client の id_token は引数注入および内部キャッシュから取得する設計でテスト可能。
  - pipeline の関数は conn と id_token を注入することで DB や外部 API をモックできる。

今後の提案 / TODO（推測）
- quality モジュール内の詳細な品質チェック実装と報告フローの統合（pipeline からの呼び出し）。
- strategy / execution / monitoring パッケージの具体実装（現状 __init__.py のみ存在）。
- ロギング設定の統一化（Settings.log_level を用いたグローバルロガー初期化の利便化）。
- J-Quants API のページネーションで大量データ取得時のメモリ使用最適化（ストリーミング処理など）。

----- 

この CHANGELOG はコードから推測して作成しています。実際の変更履歴や日付はリポジトリのコミット履歴に基づいて調整してください。必要であれば各リリースごとのファイル差分を参照してより詳細なエントリを生成します。