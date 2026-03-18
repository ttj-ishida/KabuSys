# Changelog

すべての注記は Keep a Changelog のフォーマットに準拠します。  
このファイルは、コードベース（kabusys）から推測可能な主要変更点・機能をまとめたものです。

全般的な方針・補足
- 本リリースはパッケージ初版リリース相当（バージョン 0.1.0）を想定しています。パッケージバージョンは src/kabusys/__init__.py の __version__ に合わせています。
- 多くの機能が DuckDB を想定したデータ取得／保存／集計パイプライン、および研究用ファクター算出・RSS ニュース収集を提供します。
- 設計上の注意点（ログ／環境変数／安全対策等）を実装で考慮しています。以下に主要な追加機能・設計・セキュリティ対応を列挙します。

Unreleased
- （現時点のコードベースは初版リリースとして記録しています）

0.1.0 - YYYY-MM-DD
Added
- パッケージ基盤
  - kabusys パッケージを追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。
  - パッケージ公開 API として data / strategy / execution / monitoring を __all__ に定義。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数からの設定読み込みを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により、カレントワーキングディレクトリに依存しない自動 .env ロードを実現。
  - .env のパース機能を独自実装（コメント・export プレフィックス・クォート・エスケープ対応）。
  - OS 環境変数を保護する protected パラメータ、.env.local を優先的に上書きする処理、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を提供。
  - Settings クラスに主要設定プロパティを追加（J-Quants トークン、kabuAPI, Slack トークン/チャンネル、DBパス、環境種別とログレベル検証、is_live/is_paper/is_dev ヘルパー）。

- データ取得クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。日足（OHLCV）、財務データ、マーケットカレンダーの取得機能を提供（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - API レート制限制御（_RateLimiter、120 req/min 固定間隔スロットリング）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を再試行対象）を導入。
  - 401 応答時はリフレッシュトークンからの id_token 再取得を 1 回行い再試行する仕組みを実装（get_id_token を利用）。
  - Look-ahead bias 対策のため、取得時刻を UTC で記録（fetched_at）。
  - DuckDB への保存用ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT（UPSERT）で冪等性を担保。
  - データ変換ユーティリティ（_to_float/_to_int）を実装し、不正値や空値に対する堅牢性を確保。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集と前処理、DuckDB への保存の一連処理を提供（fetch_rss, save_raw_news, run_news_collection 等）。
  - セキュリティ対策：
    - defusedxml を利用した XML パースで XML-Bomb を防御。
    - SSRF 対策（URL スキーム検証、リダイレクト先のスキーム/プライベートIP検査）を実装。リダイレクト検査用のハンドラ _SSRFBlockRedirectHandler を導入。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）や gzip 解凍後のサイズチェックでメモリ DoS を抑止。
    - 許可されない URL スキームを拒否。
  - データ品質・冪等性：
    - 記事IDは正規化した URL の SHA-256（先頭32文字）で生成して冪等性を実現。
    - トラッキングパラメータ（utm_* や fbclid 等）を除去する正規化ロジックを用意。
    - raw_news 保存は INSERT ... ON CONFLICT DO NOTHING と INSERT ... RETURNING を使用し、実際に挿入された記事IDのリストを返す。
    - news_symbols（記事と銘柄の紐付け）をチャンク単位で一括挿入する内部ユーティリティを実装（_save_news_symbols_bulk）。
  - テキスト処理と抽出：
    - URL 除去や空白正規化を行う preprocess_text を実装。
    - RSS pubDate の堅牢なパース（_parse_rss_datetime）を実装し、パース失敗時は警告を出して UTC 現在時刻で代替。
    - 本文・タイトルから 4 桁の銘柄コードを抽出する extract_stock_codes（known_codes によるフィルタリング、重複除去）。

- 研究（research）モジュール（src/kabusys/research/）
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）：指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度の DuckDB クエリで取得。
    - IC（Information Coefficient）計算（calc_ic）：ファクター値と将来リターンの Spearman ランク相関を計算。有効レコードが 3 未満の場合 None を返す。
    - rank ユーティリティ：同順位は平均ランクで処理（丸め誤差対策として round(v,12) を採用）。
    - factor_summary：各ファクター列について count/mean/std/min/max/median を算出。
    - これらは外部ライブラリに依存せず標準ライブラリのみで実装（pandas 等に依存しない設計）。
  - ファクター計算（factor_research.py）
    - モメンタム（calc_momentum）：mom_1m/mom_3m/mom_6m/ma200_dev を計算。移動平均やラグはウィンドウベースで DuckDB のウィンドウ関数を使用。
    - ボラティリティ・流動性（calc_volatility）：20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を制御し正確にカウント。
    - バリュー（calc_value）：raw_financials から target_date 以前の最新財務データを結合して PER（EPS が有効な場合）と ROE を計算。
    - 共通設計方針として DuckDB の prices_daily / raw_financials のみ参照し、本番 API 等へアクセスしないことを保証。
  - research パッケージ __init__ にて主要関数をエクスポート（calc_momentum 等、zscore_normalize を data.stats からインポートして公開）。

- スキーマ定義（src/kabusys/data/schema.py）
  - DuckDB 用スキーマ DDL を追加（raw layer の raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義を含む）。各テーブルに適切な型チェック・PRIMARY KEY を設定。
  - スキーマ定義は DataSchema.md に基づき、Raw / Processed / Feature / Execution の各層を想定。

Changed
- （初回リリースのため変更履歴なし。実装設計上、外部挙動としては上記 Added を参照。）

Fixed
- （初回リリースのため修正履歴なし）

Security
- J-Quants クライアントと RSS 収集で以下のセキュリティ対策を実施：
  - API レート制御、リトライ制御、トークン自動リフレッシュ（J-Quants）。
  - RSS の XML パースに defusedxml を使用、SSRF 対策（リダイレクト検査・プライベートIP検出）、レスポンスサイズ制限、gzip 解凍後サイズ検査。
  - URL 正規化とトラッキングパラメータ除去により、記事 ID の冪等性を強化。

Notes / Limitations
- research モジュールは外部ライブラリに依存しない実装を意図しているため、巨大データの集計や高速処理は DuckDB 側の最適化に依存します。
- save_* 系関数は DuckDB の SQL 構文（ON CONFLICT / RETURNING）を使用しています。環境によっては DuckDB のバージョン差異に注意してください。
- news_collector の URL 正規化やプライベートホスト検出は完全ではありません（DNS の解決失敗時は安全側で通過させる設計）。運用時はネットワーク環境に応じた追加対策を推奨します。
- settings は環境変数に厳密なバリデーションを行います。環境変数未設定時は ValueError を送出するため、適切な .env の準備が必要です。

開発者向けヒント
- テスト時に自動 .env 読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- jquants_client のテストでは _rate_limiter や _urlopen のモック化、_ID_TOKEN_CACHE のクリア等が有用です。
- news_collector の _urlopen はテスト用に差し替え可能（コメントにも明記）。

今後の予定（示唆）
- Feature layer / Processed layer の詳細 DDL とマイグレーションツール追加
- strategy / execution / monitoring パッケージの実装充実（現状はパッケージ構造のみ）
- 増分取得（差分フェッチ）や効率的なバッチ処理の追加最適化
- 単体テストと統合テストの追加（外部 API をモックしたテストスイート）

----- End of Changelog -----