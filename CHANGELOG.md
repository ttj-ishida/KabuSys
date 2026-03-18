CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。本プロジェクトの変更履歴は「Keep a Changelog」の形式に準拠し、セマンティックバージョニングに従います。

[Unreleased]
------------

- （現在未リリースの変更はここに記載します）

[0.1.0] - 2026-03-18
-------------------

初回公開リリース。主要な機能追加、データ取得／保存、リサーチユーティリティ、および安全性対策を含みます。

Added
- パッケージ基盤
  - パッケージメタ情報を設定（kabusys.__version__ = "0.1.0"）。
  - モジュール公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 環境・設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート判定は .git または pyproject.toml を基準（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env パーサは export KEY=val、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - 環境変数保護（読み込み時の protected set）を実装し、既存 OS 環境変数の上書きを制御。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パスなどの設定取得と妥当性チェックを実装。
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL（DEBUG, INFO, ...）の検証。
    - duckdb / sqlite の既定パスを Path 型で返すユーティリティ。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）、408/429/5xx の再試行処理。
    - 401 受信時の自動トークンリフレッシュ（1 回）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応で全件取得（pagination_key を巡回）。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への保存ユーティリティ（冪等性を考慮）
    - save_daily_quotes、save_financial_statements、save_market_calendar：ON CONFLICT (UPSERT) を使用して冪等保存。
    - fetched_at を UTC ISO 形式で記録（Look-ahead bias のトレースを想定）。
  - 型変換ユーティリティ _to_float / _to_int を実装し、入力データの不正値耐性を確保。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存するパイプラインを実装。
    - feed 取得（fetch_rss）、前処理（URL 除去、空白正規化）、記事ID（正規化 URL の SHA-256 の先頭32文字）生成。
    - defusedxml を用いた XML パースで XML-Bomb 対策。
    - HTTP レスポンスの最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の検査。
    - リダイレクト時にスキームとホストを検査する SSRF 対策用ハンドラ (_SSRFBlockRedirectHandler)。
    - ホストがプライベート/ループバック/リンクローカルであれば拒否する _is_private_host。
    - URL 正規化でトラッキングパラメータ（utm_* 等）除去、フラグメント削除、クエリソートを実施。
    - save_raw_news：チャンク化したバルク INSERT と INSERT ... RETURNING による新規記事 ID の取得（1 トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk：news と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING、チャンク化）。
    - 銘柄コード抽出 extract_stock_codes（4桁数字パターンと known_codes フィルタ）。
    - run_news_collection：複数ソースを横断して収集・保存・銘柄紐付けを実行。ソース単位で個別エラーハンドリング。

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw レイヤーの DDL を定義（raw_prices, raw_financials, raw_news, raw_executions 等のテーブル骨格）。
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋Execution 層の設計に対応する土台を用意。

- リサーチ機能（kabusys.research）
  - feature_exploration:
    - calc_forward_returns：任意ホライズン（デフォルト 1,5,21 営業日）での将来リターンを DuckDB の prices_daily から計算。ホライズンの妥当性検証と一括 SQL による取得を実装。
    - calc_ic：ファクター値と将来リターンの Spearman ランク相関（IC）を計算。欠損・非有限値の除外、十分なサンプル（>=3）判定。
    - rank：同順位は平均ランクとする実装（浮動小数丸めによる ties 検出漏れ対策として round(..., 12) を利用）。
    - factor_summary：各列の count/mean/std/min/max/median を計算（None 除外）。
    - research モジュールは外部依存（pandas 等）に頼らず標準ライブラリ + DuckDB で動作することを目標。
  - factor_research:
    - calc_momentum：mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。データ不足時は None。
    - calc_volatility：atr_20（20日 ATR の単純平均）、atr_pct、avg_turnover、volume_ratio を計算。true_range 計算で NULL 伝播を正しく扱う。
    - calc_value：raw_financials から target_date 以前の最新財務データを結合し PER（EPS が 0/欠損時は None）、ROE を算出。
    - 各関数は DuckDB 接続を受け取る設計で、本番発注 API にはアクセスしない前提。

- モジュール公開（kabusys.research.__init__）
  - calc_momentum, calc_volatility, calc_value, zscore_normalize（data.stats から）、calc_forward_returns, calc_ic, factor_summary, rank を __all__ で公開。

Security
- SSRF 対策
  - RSS 取得時にスキーム・最終 URL の検査、リダイレクト先の検証、プライベートアドレス到達の拒否を実装。
- XML パース安全性
  - defusedxml を利用して XML 関連脆弱性へ対処。
- レスポンスサイズ制限
  - MAX_RESPONSE_BYTES による大容量レスポンス／圧縮後の上限チェックを導入（Gzip bomb 対策）。

Performance / Reliability
- API レート制御（固定間隔スロットリング）と指数バックオフによる堅牢なリトライ。
- ページネーション対応と ID トークンのモジュールキャッシュで効率化。
- DuckDB へのバルク挿入はチャンク化してトランザクションを最適化。
- 保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）を採用。

Notes / Design decisions
- Research モジュールは外部ライブラリに依存しない実装を目指し、DuckDB と標準ライブラリで完結する設計。
- 時刻管理
  - データ取得時の fetched_at は UTC で記録し、データ取得の可視化・再現性に配慮。
- .env パーサはシェル風の細かいケース（export プレフィックス、引用符内エスケープ、インラインコメント）に対応。

Breaking Changes
- なし（初回リリース）

Acknowledgements / TODO
- strategy / execution / monitoring パッケージの初期プレースホルダを含む。発注ロジック・モニタリング機能は今後追加予定。
- feature の単体テスト、負荷テスト、運用用の DB マイグレーションスクリプト等は今後整備予定。

※ 上記はソースコードの構造・コメント・実装内容から推測して作成した CHANGELOG です。実際のリリースノートとして利用する場合は、リリース時の正式な記述・日付・責任者情報を追加してください。