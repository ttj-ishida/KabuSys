CHANGELOG
=========

すべての変更は Keep a Changelog の慣習に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-18
--------------------

Added
- 初回リリース。パッケージ名: kabusys (バージョン 0.1.0)。パッケージの top-level __init__ を追加。
- 環境設定管理 (kabusys.config)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みする仕組みを実装。
  - 読み込みの上書き挙動（.env → .env.local）と OS 環境変数保護機構をサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 複雑な .env 行パーシングを実装（コメント、export 句、クォート・エスケープ処理など）。
  - Settings クラスを提供し、必須環境変数の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）や
    環境モード検証 (development / paper_trading / live)、ログレベル検証を実装。
  - デフォルトの DB パス (DUCKDB_PATH, SQLITE_PATH) を設定。

- データ取得 / 永続化 (kabusys.data)
  - J-Quants API クライアント (jquants_client)
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回）を導入。対象ステータスコード（408, 429, 5xx）に対応。
    - 401 受信時のリフレッシュトークン自動リフレッシュをサポート（1 回だけリトライ）。
    - ページネーション対応の fetch_daily_quotes, fetch_financial_statements。
    - JPX マーケットカレンダー取得 fetch_market_calendar。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT を使った冪等性を確保。
    - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正値を安全に処理。
    - ページネーション間で共有する ID トークンのモジュールレベルキャッシュを実装。

  - ニュース収集モジュール (news_collector)
    - RSS フィード取得 fetch_rss、前処理 preprocess_text、URL 正規化（トラッキングパラメータ除去）を実装。
    - defusedxml を用いた安全な XML パース、gzip 対応、受信サイズ上限 (10 MB) による DoS 緩和。
    - SSRF 対策: リダイレクト先のスキーム検証、プライベート/ループバックアドレス判定、カスタム RedirectHandler を導入。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
    - DuckDB への保存関数 save_raw_news（INSERT ... RETURNING を用いて実際に挿入された記事IDを返す）、
      save_news_symbols（記事と銘柄の紐付け）、および複数記事の一括紐付け用内部関数を実装。
    - テキストから銘柄コード（4桁）を抽出する extract_stock_codes、と既知銘柄セットを用いた紐付けを行う run_news_collection を実装。
    - デフォルト RSS ソースを定義 (例: Yahoo Finance のカテゴリ RSS)。

  - DuckDB スキーマ定義 (data.schema)
    - Raw Layer のテーブル DDL を実装（raw_prices, raw_financials, raw_news, raw_executions 等の定義を含む）。
    - テーブル定義には型チェック・主キー・NOT NULL 制約を含み、データ整合性を考慮。

- 研究 / 特徴量計算 (kabusys.research)
  - feature_exploration モジュール
    - calc_forward_returns: 与えた基準日から各ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを DuckDB から一括取得して計算。
    - calc_ic: Spearman ランク相関（Information Coefficient）を計算する実装。欠損や ties を考慮。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸め誤差対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算するサマリ。
    - 設計上、標準ライブラリのみで実装（pandas等に依存しない）し、prices_daily テーブルのみ参照することを明示。
  - factor_research モジュール
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）を計算。
    - calc_volatility: 20日 ATR（ATR の単純平均）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の財務指標を取得し PER / ROE を計算（EPS が無効な場合は None）。
    - DuckDB のウィンドウ関数を活用し、スキャン範囲にバッファを持たせることで週末・祝日を吸収する設計。
  - research パッケージの __init__ にて主要ユーティリティをエクスポート（zscore_normalize を data.stats から利用）。

- Strategy / Execution / Monitoring
  - パッケージ構成として strategy/, execution/, monitoring/ のプレースホルダ __init__.py を追加（詳細実装は今後）。

Security
- ニュース収集で defusedxml と SSRF 対策、レスポンスサイズ検査を導入。外部入力や HTTP リダイレクトに対する安全性を改善。

Notes / Usage
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  必要に応じて .env/.env.local をプロジェクトルートに作成してください。
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（主にテスト用途）。
- DuckDB パスのデフォルトは data/kabusys.duckdb、SQLite のデフォルトは data/monitoring.db。
- J-Quants API のレート制限・リトライ・トークン更新は jquants_client が内部で管理するため、fetch_* 関数は通常そのまま利用可能です。

Known limitations / TODO
- DataSchema の一部（例: execution 層の完全な DDL や processed/feature 層のテーブル）は引き続き拡張が必要。
- strategy / execution の具体的な発注ロジック・モックインターフェースは今後実装予定。
- research モジュールは標準ライブラリ実装のため、大規模データ処理や高度な分析を行う場合は pandas 等を利用するオプションを検討する余地あり。

Authors
- 初回実装: kabusys 開発チーム（コードベースから推測して記載）

-----