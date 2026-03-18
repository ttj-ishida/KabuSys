# Changelog

すべての変更は Keep a Changelog の慣例に従い記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]


## [0.1.0] - 2026-03-18
初回リリース。

### Added
- パッケージ基盤
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。パッケージ公開用の基本的なモジュール構成（data, strategy, execution, monitoring）をエクスポート。
- 環境設定管理（kabusys.config）
  - .env ファイル / 環境変数読み込みの自動化を実装。プロジェクトルートの検出は `.git` または `pyproject.toml` を基準に行い、CWD に依存しない仕様。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能）。
  - .env パーサーはコメント、`export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理等に対応。
  - 必須環境変数チェック `_require`、`Settings` クラスを提供。J-Quants / kabuAPI / Slack / DB パス等のプロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH）を取得可能。
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（有効値のチェック）を実装。環境種別判定ヘルパー（is_live, is_paper, is_dev）を追加。
- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。主な機能:
    - API レート制御（120 req/min 固定間隔スロットリング）を `_RateLimiter` で管理。
    - 冪等なトークンキャッシュと自動リフレッシュ（401 系で一度だけ再取得して再試行）。
    - リトライロジック（指数バックオフ、最大試行回数、429 の Retry-After 尊重、408/429/5xx に対するリトライ）。
    - ページネーション対応の fetch 関数群: `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`。
    - DuckDB へ保存する冪等保存関数: `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`。`ON CONFLICT DO UPDATE` による重複上書き、fetched_at による取得時刻記録（UTC）。
    - HTTP/JSON 処理およびユーティリティ関数 `_to_float`, `_to_int`（安全な変換ロジック）。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集の包括的実装:
    - RSS 取得 (`fetch_rss`)：defusedxml を用いた安全な XML パース、gzip 解凍対応、Content-Length/受信サイズ上限チェック（10MB）、リダイレクト時のスキーム/ホスト検証（SSRF 対策）。
    - URL 正規化 (`_normalize_url`) とトラッキングパラメータ除去（utm_*, fbclid 等）、その正規化 URL から SHA-256（先頭32文字）で記事 ID を生成 (`_make_article_id`)。
    - テキスト前処理（URL 除去、空白正規化）および RSS pubDate パース（UTC 揃え、パース失敗時のフォールバック）。
    - DB 保存: `save_raw_news`（チャンク挿入、トランザクション、INSERT ... RETURNING により実際に挿入された記事IDを返す）、`save_news_symbols`/内部 `_save_news_symbols_bulk`（news と銘柄の紐付けを冪等に保存）。
    - 銘柄コード抽出ユーティリティ `extract_stock_codes`（4桁コード抽出、既知銘柄セットでフィルタ、重複排除）。
    - 統合ジョブ `run_news_collection`：複数ソースの独立処理、失敗時のソーススキップ、新規記事に対する一括銘柄紐付け。
- 研究用モジュール（kabusys.research）
  - 特徴量探索・IC 計算（kabusys.research.feature_exploration）
    - 将来リターン計算: `calc_forward_returns(conn, target_date, horizons=None)`（1,5,21日デフォルト、単一クエリでまとめ取得、ホライズンバリデーション）。
    - IC（Spearman の ρ）計算: `calc_ic(factor_records, forward_records, factor_col, return_col)`（結合、None/非有限値除外、レコード不足時は None）。
    - 基本統計量: `factor_summary(records, columns)`（count/mean/std/min/max/median、None を除外）。
    - ランク変換ユーティリティ `rank(values)`（同順位は平均ランク、丸めにより ties の検出漏れを抑制）。
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: `calc_momentum(conn, target_date)`（mom_1m,mom_3m,mom_6m,ma200_dev、200日 MA のデータ不足ハンドリング）。
    - Volatility / Liquidity: `calc_volatility(conn, target_date)`（20日 ATR/相対ATR、平均売買代金、出来高比率、true range の NULL 伝播制御）。
    - Value: `calc_value(conn, target_date)`（raw_financials から直近財務データを採取し PER/ROE を計算、欠損/ゼロ除外）。
    - DuckDB の prices_daily / raw_financials を参照する独立した実装（外部発注APIにはアクセスしない設計）。
- スキーマ定義（kabusys.data.schema）
  - DuckDB 用 DDL 定義（Raw Layer のテーブル定義を含む: raw_prices, raw_financials, raw_news, raw_executions（部分）など）を実装。初期化・定義をコードで保持。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集における SSRF 対策を実装。リダイレクト先のスキーム/ホスト検証、ホストがプライベート/ループバック/リンクローカル/マルチキャストかの判定等を導入。
- XML 処理に defusedxml を利用して XML Bomb 等を軽減。
- RSS/HTTP レスポンスサイズ制限を導入（メモリ DoS 対策）。

### Notes / Migration
- 環境変数名（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH）を .env または OS 環境に設定する必要があります。未設定の必須キーは起動時に ValueError を投げます。
- DuckDB のスキーマは DataSchema.md に従った定義を行います。初回実行時にテーブル作成が必要です（本リリースには DDL 定義が含まれています）。
- J-Quants API 利用時はレート制限とリトライ挙動に注意してください（内部で制御済み）。トークン自動更新を行うため、リフレッシュトークン（JQUANTS_REFRESH_TOKEN）の設定が必要です。
- ニュース収集はデフォルトで `DEFAULT_RSS_SOURCES` に Yahoo ビジネスカテゴリの RSS を含む実装になっています。既知銘柄セットを与えると自動で銘柄紐付けを行います。

署名:
- 実装は Python 標準ライブラリおよび DuckDB を使用する設計です（外部依存は defusedxml と duckdb を想定）。