CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠します。
<!-- 初期バージョンはパッケージの __version__ に合わせています -->

Unreleased
----------

- ドキュメント/内部注記の追加・微調整
- テスト・デバッグ用フラグやログ出力の調整（詳細は各モジュールのログメッセージ参照）

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初期リリース。
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を自動読み込みする機能。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - プロジェクトルートは __file__ から親ディレクトリを上がって .git または pyproject.toml を検出して決定。
      - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
    - .env ファイルの行パーサを実装（export プレフィックス、クォート、インラインコメント等に対応）。
    - Settings クラスを提供し、必須環境変数取得用の _require、検証済みプロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_*、DB パス等）を公開。
    - KABUSYS_ENV と LOG_LEVEL のバリデーションを実施（有効値の集合を定義）。

- データ取得/保存（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py
    - J-Quants API との通信クライアントを実装。
    - API レート制限（120 req/min）に従う固定間隔スロットリング (_RateLimiter) を導入。
    - リトライロジック（指数バックオフ、最大試行回数、408/429/5xx の扱い）を実装。
    - 401 応答時にリフレッシュトークンから自動で ID トークンを再取得して 1 回だけリトライ。
    - ページネーション対応の fetch_* 関数を実装:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への冪等保存関数を提供:
      - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT による更新で冪等性を確保）。
    - 型変換ユーティリティ (_to_float, _to_int) を提供（不正値・空値に対する堅牢な変換）。

- ニュース収集（RSS）
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュースを取得し、DuckDB (raw_news, news_symbols) に保存するフローを実装。
    - セキュリティ対策:
      - defusedxml を用いた XML パース（XML Bomb 等への対策）。
      - SSRF 対策: リダイレクト先と最終 URL のスキーム検証、プライベート IP/ホストの検出・ブロック（_is_private_host、_SSRFBlockRedirectHandler）。
      - 許可スキームは http/https のみ。
      - 最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の上限チェック。
    - 記事ID は正規化した URL の SHA-256（先頭32文字）を採用し冪等性を確保。
    - URL 正規化でトラッキングパラメータ（utm_*, fbclid 等）を削除。
    - テキスト前処理（URL 除去・空白正規化）。
    - DB 保存はチャンク化してトランザクション内で実施し、INSERT ... RETURNING で実際に挿入されたレコードを返す。
    - 銘柄抽出ロジック（4桁コード）と known_codes によるフィルタリング、news_symbols の一括保存ロジックを実装。
    - 公開関数: fetch_rss, save_raw_news, save_news_symbols, run_news_collection。

- DuckDB スキーマ定義
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution 層を意識したスキーマ定義群を追加（raw_prices, raw_financials, raw_news, raw_executions 等の CREATE TABLE 文を含む）。
    - 初期化用モジュールとしてロギングと DDL を定義。

- 研究（Research）用ファクター・探索
  - src/kabusys/research/factor_research.py
    - StrategyModel に基づくファクター計算を実装:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR/出来高系）
      - calc_value: per, roe（raw_financials と prices_daily を結合）
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみ参照し、本番発注 API 等にはアクセスしない設計。
    - ウィンドウ計算は SQL のウィンドウ関数を活用し、データ不足時は None を返す。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（LEAD を利用した一括取得）を実装。
    - スピアマンのランク相関（IC）を計算する calc_ic（ランク関数 rank を含む）。
    - factor_summary による基本統計量集計（count/mean/std/min/max/median）。
    - 設計上、外部ライブラリ（pandas 等）に依存せず標準ライブラリのみで実装。

  - src/kabusys/research/__init__.py
    - 主要ユーティリティをエクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize）。

- パッケージ構成（空初期化ファイル）
  - src/kabusys/execution/__init__.py（プレースホルダ）
  - src/kabusys/strategy/__init__.py（プレースホルダ）

Security
- news_collector にて SSRF 対策、XML パースの堅牢化、受信サイズ制限、URL スキーム検証などを導入。
- J-Quants クライアントで認証トークンの自動リフレッシュと安全なリトライを実装（不正な認証からの暴走を抑制）。

Notes / Design
- Research モジュールは外部 API にアクセスしない設計（DuckDB のテーブルのみ参照）で、Look-ahead Bias を避ける方針。
- J-Quants クライアントは低レイヤ（urllib）で実装され、RateLimiter により API 制限を尊重する。
- DuckDB への保存は冪等操作（ON CONFLICT）でデータ取込みの再実行に耐えるように実装。
- 設定関連は Settings を介して型変換・バリデーションを行い、誤設定を早期に検出する。

Removed
- なし（初回リリース）

Deprecated
- なし（初回リリース）

Fixed
- なし（初回リリース）

Contributing
- 変更を提案する場合は、まず Issue を作成し、ユニットテストとともに PR を送ってください。
- 環境依存の自動 .env ロードを行っているため、CI / テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨します。

以上。