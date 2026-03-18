# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の仕様に準拠し、セマンティック バージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買プラットフォームの基礎機能群を実装。

### Added
- パッケージ基盤
  - パッケージメタ情報の定義（kabusys.__version__ = 0.1.0）。
  - 空のサブパッケージプレースホルダを配置（kabusys.execution, kabusys.strategy）。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイル／OS 環境変数を自動ロードする機能を実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
    - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env のパース機能を実装（export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープ処理に対応）。
  - 環境変数保護（既存 OS 環境変数を protected として扱う）および override ロジック。
  - Settings クラスを公開:
    - J-Quants / kabuステーション / Slack / DB パス（duckdb/sqlite）等の必須/デフォルト設定取得。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証（不正値で ValueError）。
    - ヘルパープロパティ: is_live / is_paper / is_dev。

- データ取得・永続化（kabusys.data.jquants_client）
  - J-Quants API クライアント実装:
    - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対応）。
    - 401 レスポンスでの自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes: raw_prices への INSERT ... ON CONFLICT DO UPDATE。
    - save_financial_statements: raw_financials への冪等保存。
    - save_market_calendar: market_calendar への冪等保存。
  - HTTP / JSON 処理は urllib を使用し、JSON デコードエラーやネットワーク例外に対するハンドリングを実装。
  - 型変換ユーティリティ: _to_float / _to_int（安全な変換と None 返却ポリシー）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからのニュース収集と DuckDB への保存機能を実装。
    - fetch_rss: RSS 取得・XML パース・記事抽出。
      - defusedxml を用いた安全な XML パース（XML Bomb 対策）。
      - HTTP レスポンスの最大バイト数制限（デフォルト 10 MB）と gzip 解凍後の上限チェック（Gzip bomb 対策）。
      - リダイレクト時にスキームとホストを検証するカスタムハンドラ（SSRF 対策）。
      - 最終 URL の再検証、Content-Length の事前チェック。
      - URL 正規化（トラッキングパラメータ除去・ソート・フラグメント削除）と記事 ID の生成（SHA-256 の先頭32文字）。
      - テキスト前処理（URL 除去、空白正規化）。
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING をチャンク化して実行し、実際に挿入された記事ID一覧を RETURNING で取得。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等に保存（INSERT ... ON CONFLICT DO NOTHING RETURNING で厳密な挿入数を取得）。
    - run_news_collection: 複数ソースを順次処理し、ソースごとのエラーハンドリングと新規保存数の集計を実施。
  - 銘柄コード抽出 util: テキストから 4 桁数字を抽出し、known_codes に基づいてフィルタリング（重複除去）。

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw Layer の DDL を実装（raw_prices, raw_financials, raw_news, raw_executions の定義を含む）。
  - 初期化・スキーマ管理のための基盤を用意。

- リサーチ / 特徴量（kabusys.research）
  - Feature exploration（kabusys.research.feature_exploration）:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト 1,5,21 営業日）にわたる将来リターンを DuckDB の prices_daily から一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装（欠損値/有限性の考慮、サンプル数チェック）。
    - rank: 同順位は平均ランクにするランク計算（浮動小数丸めで ties 検出の安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算（None を除外）。
  - Factor 計算（kabusys.research.factor_research）:
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200 日移動平均乖離率（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials から直近の財務指標（eps, roe）を取得し PER・ROE を計算（EPS 0 または欠損時は PER を None）。
  - 研究モジュールの設計方針:
    - DuckDB 接続を受け取り prices_daily / raw_financials のみ参照（外部 API にアクセスしない）。
    - 戻り値は (date, code) をキーとする dict のリスト形式。
    - 外部ライブラリに依存しない（可能な限り標準ライブラリのみ。ただしニュース収集では defusedxml を使用）。

- 研究モジュールのエクスポート（kabusys.research.__init__）
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank と zscore_normalize（kabusys.data.stats から）を公開する API としてまとめた。

### Security
- ニュース収集での SSRF 対策（ホストのプライベート判定、リダイレクト先検証）。
- XML パースに defusedxml を利用し XML Attack を軽減。
- HTTP レスポンスの最大バイト数制限と gzip 解凍後チェックによりメモリ DoS を低減。
- RSS 内リンクのスキーム検証で mailto: などの不正スキームを排除。

### Notes / Known limitations
- strategy / execution パッケージは初期プレースホルダで、実際の売買ロジック・発注実装は未実装。
- kabusys.data.stats の実装ファイルはここに含まれていないが、zscore_normalize が使用される設計を想定。
- DuckDB スキーマ定義は Raw Layer を中心に含むが、Feature Layer / Execution Layer の完全な DDL は追加実装が必要。
- J-Quants クライアントは urllib ベースで実装されているため、将来的には requests 等への移行を検討する余地あり。
- news_collector の URL 正規化ロジックは既知トラッキングパラメータのプレフィックス一覧に依存している（必要に応じて拡張可能）。

### Fixed
- 初回リリースのため無し。

[Unreleased]: /compare/v0.1.0...HEAD
[0.1.0]: /releases/tag/v0.1.0