CHANGELOG
=========

All notable changes to this project will be documented in this file.
このプロジェクトにおける目に見える変更はすべてここに記録します。

フォーマットは "Keep a Changelog" に準拠します。
（https://keepachangelog.com/ja/1.0.0/）

Unreleased
----------

（現時点の開発中の変更はここに記載します。）

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリースを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 基本構成 / 設定管理
  - kabusys.config: 環境変数・設定管理を提供
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み（CWD 非依存）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env のパースはコメント行、export プレフィックス、シングル/ダブルクォートやバックスラッシュエスケープ、インラインコメントに対応。
    - settings オブジェクト経由で各種必須設定を取得:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック（未設定時は ValueError）。
      - デフォルトの API ベース URL、DB パス（DUCKDB_PATH / SQLITE_PATH）、環境（KABUSYS_ENV）の検証（development/paper_trading/live）および LOG_LEVEL 検証。

- データ収集 / 永続化（DuckDB）
  - kabusys.data.jquants_client:
    - J-Quants API クライアント実装（/prices/daily_quotes, /fins/statements, /markets/trading_calendar）。
    - レート制御（120 req/min）を固定間隔スロットリングで実装（内部 RateLimiter）。
    - リトライと指数バックオフ（最大3回）。408/429/5xx を再試行対象に設定。429 の場合は Retry-After を優先。
    - 401 受信時にリフレッシュトークンから id_token を自動更新して 1 回リトライ（無限再帰防止ロジックあり）。
    - ページネーション対応（pagination_key を追跡）。
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes: raw_prices に INSERT ... ON CONFLICT DO UPDATE。
      - save_financial_statements: raw_financials に INSERT ... ON CONFLICT DO UPDATE。
      - save_market_calendar: market_calendar に INSERT ... ON CONFLICT DO UPDATE。
    - 型変換ユーティリティ: _to_float, _to_int（文字列や空値の安全変換）。

- ニュース収集（RSS）
  - kabusys.data.news_collector:
    - RSS フェード取得/パースと raw_news 保存の実装。
    - セキュリティ対策:
      - defusedxml を利用した XML パース（XML Bomb 等の防御）。
      - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベートアドレスかの判定（DNS 解決・IP 判定）、リダイレクト時検査用ハンドラ実装。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の上限検査。
      - URL 正規化とトラッキングパラメータ除去（utm_* 等）。
      - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字で生成し冪等性を担保。
    - 保存ロジック:
      - save_raw_news: チャンク INSERT + INSERT ... RETURNING で実際に挿入された記事IDを返す。トランザクションでまとめて処理。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けをチャンク化して挿入（ON CONFLICT DO NOTHING、挿入数を正確に把握）。
    - テキスト前処理（URL 除去、空白正規化）や RSS pubDate の安全なパースロジックを提供。
    - extract_stock_codes: テキスト中の4桁銘柄コード抽出（既知銘柄セットでフィルタ、重複除去）。

- データスキーマ
  - kabusys.data.schema:
    - DuckDB 用スキーマ定義モジュール（Raw / Processed / Feature / Execution 層のテーブル定義）。
    - raw_prices / raw_financials / raw_news / raw_executions 等の DDL を定義（存在しなければ作成）。

- リサーチ / ファクター計算
  - kabusys.research.factor_research:
    - Momentum, Volatility, Value（および一部流動性指標）ファクター計算関数を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を DuckDB の窓関数と組み合わせて計算。必要行数が不足する場合は None を返す。
      - calc_volatility: 20日 ATR（true range を正確に扱う）、相対 ATR (atr_pct)、20日平均売買代金、volume_ratio を計算。データ不足時は None。
      - calc_value: raw_financials から最新の財務データを取得し、PER (EPS による) / ROE を計算。
    - 設計方針: DuckDB 接続を受け取り、prices_daily / raw_financials のみを参照。外部 API にはアクセスしない。

  - kabusys.research.feature_exploration:
    - calc_forward_returns: 指定基準日から各ホライズン（デフォルト 1,5,21 営業日）後のリターンを一度の SQL クエリで取得。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装。ties の平均ランク処理、有限値チェック、有効レコード数が小さい場合は None を返す。
    - rank: 同順位を平均ランクに変換（丸め誤差対策で round(...,12) を使用）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算（None 値は除外）。

  - kabusys.research.__init__ で主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank）と zscore_normalize ユーティリティの再エクスポート。

Other
- パッケージ構造の初期化ファイルを用意（kabusys.__init__ に __version__ と __all__ を定義）

Security
- ニュース収集: SSRF・XML・メモリ DoS（巨大レスポンス）対策を実装。
- J-Quants クライアント: 認証トークン管理と自動リフレッシュで 401 を安全に処理。

Notes / Known limitations
- DuckDB のテーブル名や一部 SQL はプロジェクト内のスキーマ定義と対応することを期待（prices_daily 等のテーブルは前処理層で整備される前提）。
- log メッセージや警告は多くの場面で出力する設計。実運用ではログ設定（ログレベルやハンドラ）を適切に調整してください。
- 外部依存は最小化（標準ライブラリ中心）する方針だが、defusedxml と duckdb は使用している。

Deprecated
- なし

Removed
- なし

Fixed
- なし

Security
- 上述のセキュリティ改善（news_collector の SSRF/DefusedXML/サイズ制限 等）を反映

（以降のリリースでは、各関数の挙動変更・API追加・バグ修正をこのファイルに記載してください。）