CHANGELOG
=========

すべての注目すべき変更履歴はここに記録します。本ファイルは「Keep a Changelog」の形式に準拠します。バージョンは semver に従います。

[Unreleased]
------------

- なし（初回リリース: 0.1.0）

0.1.0 - 2026-03-18
-----------------

Added
- 初期リリース。日本株自動売買システム「KabuSys」のコア実装を追加。
- パッケージ情報
  - パッケージトップで __version__ = "0.1.0" を設定。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD に依存しない読み込みを行う。
  - .env, .env.local の読み込み順序と override / protected オプションをサポート。
  - 行解析は export プレフィックス、クォート、インラインコメント等に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - Settings クラスを提供し、アプリで使用する必須設定値をプロパティとして公開：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）、LOG_LEVEL（厳格な列挙チェック）
    - 環境判定ユーティリティ: is_live / is_paper / is_dev

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装：
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）
  - レート制限制御（120 req/min）を固定間隔スロットリングで実装する RateLimiter。
  - 再試行ロジック（指数バックオフ、最大リトライ3回）と 408/429/5xx ハンドリング。
  - 401 受信時にはリフレッシュトークンを用いた id_token 自動再取得を1回試行する仕組みを搭載。
  - ページネーション間で共有するモジュールレベルの ID トークンキャッシュ実装。
  - DuckDB への保存ユーティリティ（冪等性を担保）を実装：
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE による保存
    - save_financial_statements: raw_financials テーブルへ冪等保存
    - save_market_calendar: market_calendar テーブルへ冪等保存
  - 型変換ヘルパー _to_float / _to_int を実装し、不正値を安全に None に変換。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を取得・正規化して raw_news に保存するモジュールを実装。
  - セキュリティおよび堅牢性の実装：
    - defusedxml による XML パース（XML Bomb 等の対策）。
    - SSRF 対策: URL スキーム検証、リダイレクト先のスキーム/ホスト検査、プライベートIP判定（DNS 解決含む）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）による DoS 対策。gzip 解凍後も検査。
    - RSS の最終 URL 再検証。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事ID生成（正規化後 SHA-256 の先頭32文字）。
  - テキスト前処理（URL 除去、空白正規化）。
  - save_raw_news: INSERT ... RETURNING id を使い、実際に挿入された記事 ID を返す。チャンク挿入および単一トランザクションで処理。
  - news_symbols（記事⇔銘柄）関連の保存ユーティリティ（単記事・複数記事向け）を実装。ON CONFLICT DO NOTHING で重複排除。
  - 銘柄コード抽出（4桁数字、known_codes によるフィルタ）と run_news_collection による統合収集ジョブを提供。
  - デフォルト RSS ソースとして Yahoo ビジネスカテゴリを設定。

- DuckDB スキーマ初期化 (kabusys.data.schema)
  - DataSchema.md に基づき Raw / Processed / Feature / Execution 層のテーブル定義を開始。
  - Raw 層の DDL を実装（例: raw_prices, raw_financials, raw_news, raw_executions 等。NOT NULL / CHECK / PRIMARY KEY を含む堅牢なスキーマ）。
  - スキーマ定義は CREATE TABLE IF NOT EXISTS で安全に初期化可能。

- リサーチ / 特徴量 (kabusys.research)
  - feature_exploration:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを DuckDB の prices_daily から一括取得
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（欠損/非有限値除外、有効件数3未満で None を返す）
    - rank: 同順位は平均ランクにするランク関数（round(...,12) による ties 対策）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（LAG / 移動平均を SQL で実装、データ不足時は None）
    - calc_volatility: 20日 ATR / 相対 ATR / 20日平均売買代金 / 出来高比率 を計算（true range 計算で NULL 伝播制御）
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出、target_date 以前の最新財務データを取得
  - research パッケージ __init__ で主要関数群（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank）と zscore_normalize（kabusys.data.stats から）を公開。

Security
- news_collector: SSRF 対策、defusedxml、応答サイズ上限、gzip 解凍後検査などを導入。
- jquants_client: API トークンリフレッシュや再試行ロジックで堅牢な外部 API 呼び出しを実現。

Notes / Usage
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - これらが未設定の場合、Settings の該当プロパティアクセスは ValueError を投げます。
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動 .env 読み込みはプロジェクトルートが検出できなければスキップされる点に注意。
- テストや CI で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用。

Known limitations / TODO
- strategy / execution / monitoring サブパッケージの実装は未完成（__init__ は存在するが具体的実装は未追加）。
- 一部の機能（PBR・配当利回りなどのバリューファクター、戦略レイヤー）は未実装。
- 外部依存（例: kabusys.data.stats の zscore_normalize）は別ファイルで提供される前提。

Breaking Changes
- なし（初回リリース）。

References
- 実装はソース内のドキュメンテーション文字列（モジュールヘッダ、関数 docstring）に従って設計されています。