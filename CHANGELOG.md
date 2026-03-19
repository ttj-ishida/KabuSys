# Changelog

すべての重要な変更をこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

※ 本 CHANGELOG はコードベースから推測して作成しています（初期リリース相当: 0.1.0）。

## [0.1.0] - 2026-03-19

初期リリース。KabuSys のコア機能群を実装しました（環境設定・データ取得・DuckDB スキーマ・ニュース収集・特徴量/ファクター計算等）。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名と __version__ = "0.1.0" を定義。
  - __all__ で主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パースの堅牢化（export 形式対応、クォート内エスケープ、行末コメント処理など）。
  - 環境変数保護機能（既存 OS 環境変数を上書きしない・.env.local は上書き可能）。
  - 必須設定取得ユーティリティ _require および Settings クラスを提供。
  - Settings が提供する主要プロパティ:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルト値あり）
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティ（urllib ベース）を実装。
  - レート制限制御: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter。
  - 再試行ロジック: 指数バックオフ、最大リトライ回数 3、対象ステータス（408, 429, 5xx）に対応。
  - 401 応答時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
  - ページネーション対応のデータ取得:
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（財務四半期データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT ... DO UPDATE を利用）:
    - save_daily_quotes -> raw_prices テーブル
    - save_financial_statements -> raw_financials テーブル
    - save_market_calendar -> market_calendar テーブル
  - 型変換ユーティリティ _to_float / _to_int（入力の堅牢化）
  - レート制限・リトライ挙動・トークンリフレッシュに関するログ出力と警告処理を実装

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集と DuckDB への保存ワークフローを提供。
  - セキュリティ/堅牢性対策:
    - defusedxml による XML パース（XML Bomb 等の防御）
    - URL スキーム検証（http/https のみ許可）
    - リダイレクト時のスキーム/ホスト検査（_SSRFBlockRedirectHandler）
    - ホストのプライベートアドレス判定（_is_private_host）による SSRF 対策（DNS 解決して A/AAAA を検査）
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後サイズ検査（Gzip bomb 対策）
    - HTTP ヘッダ Content-Length の事前チェック
  - URL 正規化と記事 ID 生成:
    - トラッキングパラメータ除去（utm_*, fbclid 等）
    - URL 正規化後に SHA-256 の先頭 32 文字を記事 ID として採用（冪等性）
  - テキスト前処理（URL 除去・空白正規化）
  - RSS パースの柔軟化（content:encoded 優先、guid を代替リンクとして使用）
  - DB 保存（DuckDB）:
    - save_raw_news: INSERT ... RETURNING id を用いて新規挿入された記事 ID を返す。チャンク化（_INSERT_CHUNK_SIZE）と単一トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（重複除去・チャンク化・トランザクション）。
  - 銘柄コード抽出:
    - 4桁数字パターンに基づき既知コードセットでフィルタ（extract_stock_codes）。
  - 統合収集ジョブ run_news_collection を提供（複数ソースの逐次処理・個別エラーハンドリング・既知銘柄紐付け）

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - DataSchema.md に基づく 3 層構造（Raw / Processed / Feature / Execution）を想定した DDL を定義。
  - 以下の Raw 層テーブル DDL を実装（CREATE TABLE IF NOT EXISTS）:
    - raw_prices, raw_financials, raw_news, raw_executions（断片的に記載、続きあり）
  - スキーマ初期化用ユーティリティ（ログ出力付き）

- リサーチモジュール（src/kabusys/research/*）
  - feature_exploration.py:
    - calc_forward_returns: DuckDB の prices_daily を参照して複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: ファクターと将来リターンのランク相関（Spearman ρ）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクを割り当てるランク関数（丸めで ties の検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
    - 実装は標準ライブラリと duckdb 接続のみで動作（pandas 等に依存しない）。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（20日平均関連）を計算。true_range の NULL 伝播を正しく扱う。
    - calc_value: raw_financials から最新財務を取得し per / roe を計算（EPS=0/欠損時は None）。
    - 各関数は prices_daily / raw_financials のみ参照し、本番 API には触れない設計。
  - src/kabusys/research/__init__.py で主要関数群をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）

### Security
- RSS フィード取得周りで SSRF 対策を強化:
  - スキーム検証、リダイレクト時の事前検査、ホストのプライベートアドレス判定。
  - XML パースに defusedxml を使用。
  - レスポンスサイズ制限と gzip 解凍後の検査を実装（大規模応答による DoS 対策）。
- J-Quants クライアント:
  - トークンの自動リフレッシュは 401 のみで 1 回に制限し、無限再帰を防止（allow_refresh フラグ）。
  - API レート制限を守ることで外部 API 側への負荷や IP ブロックを回避。

### Notes / Implementation details
- DuckDB を前提とした設計。全てのデータ保存/集計は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取る API を提供。
- リサーチ関数群は標準ライブラリのみで実装（pandas などには依存しない）。
- jquants_client は urllib を利用した同期 HTTP 実装。必要なら将来的に requests 等に差し替え可能。
- news_collector の _urlopen はテスト用にモック可能（テスト時の差し替えを想定）。
- 一部テーブル・DDL（raw_executions 等）はファイル内で続きが存在する想定。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

---

今後の改訂で記載してほしい情報（例）
- マイグレーションやスキーマ変更の手順
- 追加したユーティリティ関数の使用例
- パフォーマンス改善や API 仕様変更の注意点

必要であれば、各モジュールの使用例や期待される DB スキーマ全体（DDL）を追記して CHANGELOG に反映します。