# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このリポジトリはセマンティックバージョニングに従います。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-18

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システム（バージョン 0.1.0）。
  - パッケージエントリポイント: kabusys.__version__ = "0.1.0"、__all__ に主要サブパッケージを公開。

- 環境設定管理モジュール (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは __file__ を基準に親ディレクトリから .git または pyproject.toml を探索して特定。
    - 読み込み順序: OS環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサー:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理。
  - Settings クラスを提供（settings インスタンス経由で利用）。
    - 必須環境変数の取得 (例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD)。
    - デフォルトや型変換: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等。
    - KABUSYS_ENV の検証 (development|paper_trading|live) と LOG_LEVEL の検証。
    - ユーティリティプロパティ: is_live, is_paper, is_dev。

- Data レイヤー
  - DuckDB スキーマ定義・初期化モジュール (kabusys.data.schema)
    - Raw / Processed / Feature / Execution 層を想定した DDL（raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義を含む）。
  - J-Quants API クライアント (kabusys.data.jquants_client)
    - API レスポンス取得・ページネーション対応（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。対象ステータス: 408 / 429 / 5xx。429 時は Retry-After ヘッダを優先。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回だけ再試行（無限再帰防止フラグあり）。
    - ページネーション間での ID トークン共有のためのモジュールレベルキャッシュ。
    - DuckDB への冪等保存関数:
      - save_daily_quotes: raw_prices へ保存（ON CONFLICT DO UPDATE）。fetched_at を UTC ISO8601 で記録。
      - save_financial_statements: raw_financials へ保存（ON CONFLICT DO UPDATE）。fetched_at を記録。
      - save_market_calendar: market_calendar へ保存（ON CONFLICT DO UPDATE）。
    - 数値変換ユーティリティ: _to_float / _to_int（変換失敗や不正値は None を返す。小数部がある "1.9" などは int に変換しない等の挙動を明示）。
  - ニュース収集モジュール (kabusys.data.news_collector)
    - RSS フィードから記事を収集し raw_news / news_symbols に保存するワークフローを実装。
    - セキュリティ設計:
      - defusedxml を利用して XML Bomb 等を防御。
      - SSRF 対策: リダイレクト時のスキーム検査・プライベートIP検出、事前ホスト検証（_is_private_host）。
      - URL スキームは http/https のみ許可。
      - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10 MB) の採用と読み取り上限チェック。gzip 解凍後のサイズ検査も実施。
    - URL 正規化: トラッキングパラメータ（utm_*, fbclid, gclid 等）除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート。
    - 記事 ID は正規化 URL の SHA-256 ハッシュの先頭 32 文字で生成し冪等性を担保。
    - RSS パース/記事前処理:
      - content:encoded 優先、description フォールバック、URL 除去、空白正規化。
      - pubDate の RFC2822 パース (_parse_rss_datetime)、失敗時は警告ログを出力して現在時刻で代替。
    - DB 保存: save_raw_news はチャンク INSERT + INSERT ... RETURNING を用いて新規挿入 ID を返す。save_news_symbols / _save_news_symbols_bulk で銘柄紐付けを行う。全操作はトランザクションで保護。
    - 銘柄コード抽出: 4 桁数字パターン（例 "7203"）から known_codes セットに基づいて抽出（重複除去）。
    - 統合ジョブ run_news_collection を提供。既定 RSS ソース (DEFAULT_RSS_SOURCES) を持ち、各ソースの失敗は個別に処理して他ソースに影響を与えない設計。

- Research / Feature 作成
  - 特徴量探索モジュール (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定基準日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度に取得。horizons は正の整数かつ <= 252 を要求。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 件未満の場合は None を返す。
    - rank: 同順位は平均ランクを採用するランク計算（float 丸め誤差対策に round(..., 12) を使用）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算（None と非有限値を除外）。
  - ファクター計算モジュール (kabusys.research.factor_research)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）を計算。必要行数が不足する場合は None を返す。
    - calc_volatility: atr_20（20 日 ATR の単純平均） / atr_pct / avg_turnover / volume_ratio を計算。ATR・移動平均の必要観測数が不足すると None を返す。
    - calc_value: raw_financials から target_date 以前の最新財務を取得して PER（EPS が 0 または欠損の場合は None）・ROE を計算。prices_daily と結合して結果を返す。
  - 研究用 API をまとめて kabusys.research.__init__ で再エクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- 初回リリースのため変更履歴なし。

### Fixed
- 初回リリースのため修正履歴なし。

### Security
- RSS パーサーで defusedxml を使用、SSRF対策のリダイレクトハンドラおよびプライベートIPチェックを導入。
- J-Quants クライアントは認証トークンを保護し、401 に対して自動リフレッシュを行う（無限ループ防止の設計あり）。
- 外部に公開されうる URL の検証とレスポンスサイズ上限により、いくつかの DoS/SSRF ベクトルを軽減。

### Notes / Usage
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 環境設定の上書き・保護:
  - OS 環境変数は .env/.env.local による上書きから保護される（protected ロジック）。
  - .env.local は .env を上書きする（override=True）。
- J-Quants API のレート制限: 120 req/min。内部的にスロットリングしているため、外部からは基本的に意識不要だが大量リクエスト時は注意。
- DuckDB への保存は可能な限り冪等（ON CONFLICT ... DO UPDATE / DO NOTHING）で設計している。
- NewsCollector の run_news_collection は既知銘柄セット（known_codes）を渡すことで記事と銘柄の紐付けを自動で行う。

### Known issues / TODO
- schema.py の execution 層（raw_executions 等）の DDL 定義は継続拡張を想定（将来的に発注・約定・ポジション管理テーブルの詳細設計を追加予定）。
- 外部依存を最小化する設計だが、実運用ではパフォーマンスやエラー監視（メトリクス／モニタリング）の追加が必要。

---

開発者向け: その他 API の詳細挙動（例: fetch_daily_quotes の pagination_key 処理、save_* の戻り値）や関数の入力制約はコード中にドキュメント文字列で記載済みです。質問や追記希望があればお知らせください。