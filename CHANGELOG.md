# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠します。  

## [0.1.0] - 2026-03-19

初回リリース（ソースコードから推測して記載）。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__）。公開 API: data, strategy, execution, monitoring。
  - バージョン情報 __version__ = "0.1.0" を設定。

- 設定管理
  - 環境変数 / .env ファイルの自動ロード機能を実装（kabusys.config）。
    - プロジェクトルートは .git または pyproject.toml で検出。ルート未検出時は自動読み込みをスキップ。
    - 読み込み順序: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export形式、クォート、インラインコメント等に対応。
    - 環境変数取得ユーティリティ Settings を提供（必須変数チェックを含む）。
    - 主な環境変数（例）:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - KABUSYS_ENV（development / paper_trading / live のみ許可）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - DUCKDB_PATH, SQLITE_PATH
    - Settings に便利プロパティ（is_live / is_paper / is_dev）を実装。

- データ取得・永続化（J-Quants）
  - J-Quants API クライアントを実装（kabusys.data.jquants_client）。
    - レート制限対応（120 req/min、固定間隔スロットリング _RateLimiter）。
    - 自動リトライ（指数バックオフ、最大3回、408/429/5xx を再試行対象）。
    - 401 受信時のトークン自動リフレッシュ（1回まで）とモジュールレベルのトークンキャッシュ。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（四半期財務）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB へ冪等保存する save_* 関数:
      - save_daily_quotes（raw_prices）
      - save_financial_statements（raw_financials）
      - save_market_calendar（market_calendar）
    - 日付/数値変換ユーティリティ（_to_float, _to_int）を実装し不正値に寛容に対応。
    - fetched_at に UTC タイムスタンプを記録して Look-ahead バイアスを防止。

- ニュース収集（RSS）
  - RSS ニュース収集モジュールを実装（kabusys.data.news_collector）。
    - RSS フェッチ（fetch_rss）と記事保存（save_raw_news、save_news_symbols、_save_news_symbols_bulk）。
    - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
    - URL 正規化でトラッキングパラメータ（utm_* 等）を除去、クエリソート、フラグメント削除を実施。
    - Gzip 圧縮対応、受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）による DoS 対策。
    - SSRF 対策:
      - リダイレクト前後でスキームとホストを検証するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
      - ホストがプライベート/ループバック/リンクローカルならアクセス拒否（_is_private_host）。
      - 許可スキームは http/https のみ。
    - XML パースに defusedxml を利用して XML 攻撃を軽減。
    - テキスト前処理（URL除去、空白正規化）と銘柄コード抽出（4桁数字、known_codes フィルタ）を実装。
    - run_news_collection により複数ソースを順次処理し、失敗しても他ソースを継続。

- 研究用（Research）モジュール
  - 特徴量探索モジュール（kabusys.research.feature_exploration）を追加。
    - calc_forward_returns：指定日から各ホライズンの将来リターンを DuckDB の prices_daily から一括取得。
    - calc_ic：ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None を返す。
    - rank：同順位は平均ランクで処理（丸めにより ties 検出漏れ防止）。
    - factor_summary：count/mean/std/min/max/median を計算。
    - 標準ライブラリのみで実装（pandas 等に依存しない設計）。
  - ファクター計算モジュール（kabusys.research.factor_research）を追加。
    - calc_momentum：mom_1m/mom_3m/mom_6m、ma200_dev を計算。データ不足時は None。
    - calc_volatility：atr_20、atr_pct、avg_turnover、volume_ratio を計算（ATR 等はウィンドウ集計）。
    - calc_value：raw_financials から最新の財務データを取得し PER/ROE を計算。
    - DuckDB の prices_daily / raw_financials のみ参照し外部 API へはアクセスしない前提。
  - research パッケージの __all__ に主要関数群を公開（calc_momentum 等と zscore_normalize の参照）。

- スキーマ定義
  - DuckDB 用スキーマ定義モジュール（kabusys.data.schema）を追加。
    - Raw Layer のテーブル定義 DDL を提供: raw_prices、raw_financials、raw_news、raw_executions（実行履歴）などの定義文字列を含む。
    - 各テーブルに PRIMARY KEY や CHECK 制約を定義しデータ整合性を担保。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- ニュース収集での SSRF 対策、受信サイズ上限、defusedxml の利用など複数の安全対策を組み込んでいる点を明記。
- J-Quants クライアントは認証トークンの扱いに注意（トークンキャッシュ/自動リフレッシュ）し、不正レスポンス時の再試行ロジックを備える。

### Notes / Other
- 多くの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取り、prices_daily / raw_* テーブルを参照または更新する設計。
- 多くの処理は「本番口座への発注や外部発注 API へのアクセスを行わない」ことがドキュメント内に明示されており、研究・データ層と実行層を分離した設計思想が見受けられる。
- 一部 DDL や raw_executions の定義はソースが途中で切れている箇所があるため、実装の続き（Execution 層の完全な定義・初期化処理など）が別ファイルや今後のコミットで必要と推測される。

もしより詳細なリリースノート（各関数の入力/出力サンプルや既知の制約・既知の問題の一覧）を出力する必要があれば、対象モジュールを指定してください。