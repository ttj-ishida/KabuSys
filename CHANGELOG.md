CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトの初回リリースを記録しています。

Unreleased
----------

- 今後の変更点をここに記載します。

[0.1.0] - 2026-03-19
--------------------

Added
- パッケージ初回リリース。
  - バージョン: 0.1.0
  - パッケージ名: kabusys

- コア初期化
  - src/kabusys/__init__.py によるパッケージ公開インターフェース定義。
  - __all__ に data, strategy, execution, monitoring を含む。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートは .git または pyproject.toml を基準に自動検出（CWD 非依存）。
    - 自動ロードを無効化するために環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能。
  - .env パーサ: export 形式やクォート、インラインコメントなどに対応した堅牢なパーサを実装。
  - Settings クラスを提供:
    - 必須環境変数の検査（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
    - デフォルト値や型変換、検証（KABUSYS_ENV: development/paper_trading/live、LOG_LEVEL 検証）。
    - データベースパスのデフォルト（DUCKDB_PATH= data/kabusys.duckdb, SQLITE_PATH= data/monitoring.db）。
    - ヘルパープロパティ: is_live / is_paper / is_dev。

- データ取得クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアント実装:
    - レート制限対応（120 req/min）: 固定間隔スロットリングによる RateLimiter を採用。
    - リトライロジック（最大3回、指数バックオフ）と 408/429/5xx ハンドリング。
    - 401 Unauthorized を受けた場合の自動トークンリフレッシュ（1回のみ）とトークンキャッシュ。
    - ページネーション対応 API 呼び出し（fetch_daily_quotes, fetch_financial_statements）。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）: save_daily_quotes, save_financial_statements, save_market_calendar。
    - 型変換ユーティリティ: _to_float / _to_int（堅牢な変換ルール）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードの取得と前処理機能を実装:
    - RSS パースに defusedxml を使用して XML 攻撃を軽減。
    - SSRF 対策: URL スキーム検証、リダイレクト時のスキーム/ホスト検査、プライベートアドレス判定。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10 MB)、gzip 解凍および Gzip bomb 検出。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url）。
    - 記事ID は正規化 URL の SHA-256 の先頭32文字で生成（冪等性確保）。
    - テキスト前処理（URL 除去、空白正規化）。
    - 銘柄コード抽出（4桁数字、既知コードフィルタリング）。
    - DB 保存:
      - raw_news へのチャンク INSERT + RETURNING による新規記事 ID 取得（save_raw_news）。
      - news_symbols への紐付けを一括保存（_save_news_symbols_bulk / save_news_symbols）。
    - 統合ジョブ run_news_collection を提供（各ソースの独立したエラーハンドリング）。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - feature_exploration.py:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily テーブルから一括計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（ties の平均ランク処理を含む）。
    - rank: 同順位は平均ランクにする独自ランク関数（浮動小数の丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median の基本統計量を標準ライブラリのみで計算。
    - 設計方針: DuckDB 接続を受け取り、prices_daily のみ参照。本番 API にはアクセスしない。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）を計算。データ不足時は None を返す。
    - calc_volatility: atr_20（20日 ATR）、atr_pct、avg_turnover（20日平均売買代金）、volume_ratio（当日/20日平均）を計算。true_range の NULL 伝播に注意した実装。
    - calc_value: raw_financials から直近の財務を取得して PER/ROE を計算。prices_daily と組み合わせて出力。
    - 定数／ウィンドウ設定（例: _MA_LONG_DAYS=200, _ATR_DAYS=20）を明確化。
    - 全て DuckDB クエリ主体で実装し、外部ライブラリ（pandas 等）に依存しない。

- データベーススキーマ (src/kabusys/data/schema.py)
  - DuckDB 用スキーマ定義 (DDL) を実装（Raw / Processed / Feature / Execution 層を想定）。
  - raw_prices, raw_financials, raw_news, raw_executions などの CREATE TABLE 文を含む（CHECK 制約・PRIMARY KEY を定義）。

- モジュール統合 (src/kabusys/research/__init__.py)
  - 主要なリサーチユーティリティをエクスポート: calc_momentum, calc_volatility, calc_value, zscore_normalize（kabusys.data.stats 由来）、calc_forward_returns, calc_ic, factor_summary, rank。

Security
- ニュース収集における SSRF 対策、defusedxml の使用、受信サイズ制限を実装。
- J-Quants クライアントでのレート制限とリトライにより API 誤用/過剰リクエストを抑制。

Notes / マイグレーション / 必須設定
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われる。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB / SQLite のデフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- DuckDB テーブルのスキーマ定義は schema モジュールにあり、初期化スクリプトから実行することを想定。

Removed
- （初回リリースのため該当なし）

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Acknowledgements
- 初版は DuckDB を中心とした設計で、外部依存を最小化する方針で作成されています。RSS パーサや HTTP 周りは堅牢性（SSRF、サイズ上限、gzip 対応）を重視しています。

  
（以上）