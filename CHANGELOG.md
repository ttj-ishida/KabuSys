# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

なおこの CHANGELOG は提示されたコードベースから実装内容を推測して作成しています。

## [Unreleased]

- （現在リリース予定の変更はありません）

## [0.1.0] - 2026-03-18

Added
- 初期リリース。日本株自動売買システム「KabuSys」の基礎モジュールを実装。
- パッケージ構成（モジュール群）
  - kabusys.config: 環境変数 / .env 管理、プロジェクトルート検出、自動ロード機能（.env < .env.local の優先度）、必須環境変数取得ユーティリティ（_require）を実装。
    - .env パースは export プレフィックス、クォート、インラインコメント等に対応。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - Settings クラスで J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等のプロパティを提供し、値検証を行う。
- data 層
  - kabusys.data.jquants_client: J-Quants API クライアントを実装。
    - API レート制御（120 req/min 固定間隔スロットリング）を組み込んだ RateLimiter を実装。
    - リトライ（指数バックオフ、最大3回）、429 の Retry-After 対応、408/429/5xx の再試行対象化。
    - 401 受信時の自動トークンリフレッシュ（1回）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応（pagination_key を用いたループ取得）。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への保存関数（冪等）: save_daily_quotes（raw_prices）、save_financial_statements（raw_financials）、save_market_calendar（market_calendar）。ON CONFLICT による上書きを利用。
    - 入力変換ユーティリティ: _to_float / _to_int（文字列・None 耐性）。
  - kabusys.data.news_collector: RSS からのニュース収集と DuckDB 保存の実装。
    - fetch_rss: RSS 取得・XML パース（defusedxml を使用して XML 攻撃を防止）、gzip 解凍、Content-Length/サイズ上限チェック（10 MB）、リダイレクト時のスキーム & プライベートホスト検査を実装。
    - URL 正規化（トラッキングパラメータ除去・クエリソート・フラグメント除去）と ID 生成（正規化URL の SHA-256 先頭32文字）。
    - 記事前処理（URL 除去、空白正規化）と pubDate の堅牢なパース（フォールバックで現在時刻）。
    - DB 保存: save_raw_news（チャンク分割、トランザクション、INSERT ... RETURNING による実際挿入IDの取得）、save_news_symbols / _save_news_symbols_bulk（重複除去、チャンク・トランザクション）。
    - 銘柄コード抽出: 4桁数字パターン抽出と既知コードセットによるフィルタ（extract_stock_codes）。
    - run_news_collection: 複数ソース一括収集、各ソース独立したエラーハンドリング、記事→銘柄紐付け処理を提供。
- research 層
  - kabusys.research.feature_exploration:
    - 将来リターン計算: calc_forward_returns（複数ホライズン同時取得、SQL の LEAD を使用）。
    - IC（Information Coefficient）計算: calc_ic（Spearman のρ相当のランク相関を実装、欠損・非有限値除外、サンプル不足時は None を返す）。
    - ランク関数: rank（同順位は平均ランク、丸め（round 12 桁）による ties の検出安定化）。
    - ファクター統計: factor_summary（count/mean/std/min/max/median を計算）。
  - kabusys.research.factor_research:
    - モメンタム: calc_momentum（mom_1m, mom_3m, mom_6m, ma200_dev。200日移動平均のカウントチェックを行う）。
    - ボラティリティ/流動性: calc_volatility（20日 ATR, atr_pct, avg_turnover, volume_ratio。true_range の NULL 伝播制御に注意）。
    - バリュー: calc_value（raw_financials の直近財務データと価格を結合して PER/ROE を計算）。
  - kabusys.research.__init__: 主要関数をエクスポート（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize を公開）。
- スキーマ / 初期化
  - kabusys.data.schema: DuckDB 用テーブル定義（Raw Layer の raw_prices, raw_financials, raw_news, raw_executions 等の DDL を定義。DataSchema に基づく3層モデルを想定）。
    - DDL は CHECK 制約や PRIMARY KEY を含むスキーマでデータ整合性を強化。
- パッケージメタ
  - kabusys.__init__ による version ("0.1.0") と主要モジュールの __all__ を設定。

Security
- RSS パースに defusedxml を使用して XML 関連の攻撃を緩和。
- fetch_rss での SSRF 対策:
  - URL スキーム検査（http/https のみ許可）。
  - リダイレクト時にスキーム・ホスト検査を行うカスタムハンドラを使用。
  - ホスト名に対して DNS 解決を行い、プライベート / ループバック / リンクローカル / マルチキャストをブロック。
- レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ再チェックにより DoS 対策を実施。
- ニュース URL 正規化でトラッキングパラメータを除去し ID 汚染を抑制。

Performance / Reliability
- J-Quants クライアントに固定間隔の RateLimiter を導入し、API レート制限を遵守。
- J-Quants のリトライ（指数バックオフ）と pagination_key キャッシュにより耐障害性を向上。
- DuckDB 保存処理はバルク INSERT（executemany / チャンク挿入）を使用し、ON CONFLICT で冪等性を確保。
- ニュース保存はチャンク分割と単一トランザクション制御でオーバーヘッドを削減。

Internals / Implementation Notes
- ファクター/リサーチ機能は DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみを参照（外部 API へのアクセスは行わない設計）。
- calc_forward_returns やファクター計算は SQL ウィンドウ関数（LEAD / LAG / AVG / COUNT）を多用している。
- スピアマン相関はランク化（同順位は平均ランク）→ Pearson で算出する方式を採用し、ties と浮動小数丸めに配慮。
- Settings.env / log_level の検証で不正な値は ValueError を送出。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Removed / Deprecated
- 初期リリースのため該当なし。

Breaking Changes
- なし（初期リリース）。

Notes
- 実際の運用では .env.example を参考に必要な環境変数（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）を設定してください。
- DuckDB スキーマのうち raw_executions 定義など一部が今回提示コードでは途中までの可能性があるため、実運用前にスキーマ全体を確認してください。
- 外部依存は最小化されているが、defusedxml と duckdb は実行時に必要です。

[Caveat]
- この CHANGELOG は提供されたソースコードからの推測に基づいて作成しています。実際のリリースノートやリリース日、細部の仕様はリポジトリの正式な履歴（git タグ / コミットメッセージ）に基づいて確定してください。