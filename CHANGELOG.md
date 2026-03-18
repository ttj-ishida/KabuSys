KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠（https://keepachangelog.com/ja/）。

## [0.1.0] - 2026-03-18
初回公開リリース。

### 追加 (Added)
- パッケージ初期構成
  - kabusys パッケージの公開 API を設定（__version__ = 0.1.0、__all__ に data/strategy/execution/monitoring を追加）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local からの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して判定）。
  - 環境変数読み込み時のパーサ実装（export プレフィックス、クォート、インラインコメント対応、エスケープ処理）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）/LOG_LEVEL を取得するプロパティを実装。
  - バリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）とユーティリティプロパティ（is_live/is_paper/is_dev）を追加。

- データ取得・保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API への HTTP クライアントを実装。
  - RateLimiter による固定間隔スロットリング（120 req/min）実装。
  - 再試行ロジック（指数バックオフ、最大リトライ3回）とステータスコードに基づく挙動（408/429/5xx のリトライ）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装。モジュールレベルで ID トークンをキャッシュ。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への冪等保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT による更新で重複排除。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し不正データ耐性を向上。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得して raw_news に保存するフローを実装。
  - トラッキングパラメータ除去付き URL 正規化、記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
  - defusedxml を用いた安全な XML パースで XML Bomb 等への耐性を確保。
  - SSRF 対策:
    - 取得前にホストがプライベートアドレスか検査。
    - リダイレクトを検査するカスタム RedirectHandler を導入（スキーム/プライベートアドレスの検証）。
    - URL スキームは http/https のみ許可。
  - 受信バイト数上限（MAX_RESPONSE_BYTES = 10MB）や gzip 解凍後サイズチェックを導入。
  - 前処理（URL 除去・空白正規化）を行う preprocess_text を提供。
  - raw_news へのバルク挿入はチャンク化してトランザクションで処理し、INSERT ... RETURNING により新規挿入 ID を返す（save_raw_news）。
  - 記事と銘柄の紐付け機能（extract_stock_codes, save_news_symbols, _save_news_symbols_bulk）を提供。
  - デフォルトRSSソースに Yahoo Finance のビジネスカテゴリを登録（DEFAULT_RSS_SOURCES）。

- データスキーマ (src/kabusys/data/schema.py)
  - DuckDB 用の初期 DDL を定義（raw_prices, raw_financials, raw_news, raw_executions などのテーブル定義を含むスキーマファイル）。
  - Raw / Processed / Feature / Execution 層の設計に基づくスキーマ骨子を実装。

- 研究（Research）モジュール (src/kabusys/research)
  - feature_exploration.py を追加:
    - calc_forward_returns: DuckDB の prices_daily を参照して複数ホライズンの将来リターンをまとめて取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。欠損や ties を考慮。
    - rank: 同順位は平均ランクで扱うランク変換（丸め誤差対策あり）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - 設計方針として DuckDB の prices_daily テーブルのみ参照し外部 API に依存しない実装。
  - factor_research.py を追加:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、当日出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得し PER（EPS が0/欠損なら None）、ROE を計算。
    - 各関数とも prices_daily / raw_financials のみ参照し本番発注 API 等にはアクセスしない方針。

- 研究パッケージ初期エクスポート (src/kabusys/research/__init__.py)
  - 主要ユーティリティ（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を __all__ で公開。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- news_collector において SSRF 対策を複数実装（ホストのプライベート判定、リダイレクト前検証、スキーム制限）。
- XML パースに defusedxml を使用し、XML ベースの攻撃に対する保護を追加。
- RSS 受信サイズ制限（10MB）と gzip 解凍後のサイズチェックによりメモリ DoS を軽減。

### 実装上の注意（Notes）
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意/デフォルト: KABUSYS_ENV (default: development)、LOG_LEVEL (default: INFO)、DUCKDB_PATH / SQLITE_PATH（デフォルト path を参照）
  - 自動 .env 読み込みはプロジェクトルート検出に依存するため、配布後は .env ファイルの配置に注意。自動読み込みを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB:
  - データ取得・保存関数は duckdb.DuckDBPyConnection を受け取る想定。スキーマ初期化は schema モジュールの DDL を使用して行う必要あり。
  - save_* 関数は冪等（ON CONFLICT / DO UPDATE / DO NOTHING）を意図して実装されている。
- Research 関数:
  - 外部ライブラリ（pandas 等）に依存せず純粋に標準ライブラリ + DuckDB SQL で実装。大量データ環境でのパフォーマンスは DuckDB の実行プランに依存。
  - 不足データや同値系列に対して None / 平均ランクで扱う等の挙動は仕様であり、上位ロジック側でのフィルタリング・処理が必要。
- J-Quants クライアント:
  - API 制限を守るため内部で待機する挙動がある。ユニットテストでは _rate_limiter.wait() や _urlopen をモックすることを推奨。
  - トークンリフレッシュは 401 のみトリガーされ、get_id_token 呼び出し内では allow_refresh=False により再帰的リフレッシュを防止。
- NewsCollector:
  - RSS 解析で pubDate パースに失敗した場合、現在時刻（UTC）で代替する設計になっている（raw_news.datetime は NOT NULL）。
  - extract_stock_codes は日本株の 4 桁銘柄コードに限定。known_codes によるフィルタリングを行うため、事前に有効銘柄コードセットを準備すること。

### 既知の制限 (Known limitations)
- 現バージョンでは PBR・配当利回り等のバリューファクターは未実装（calc_value の注記参照）。
- strategy / execution / monitoring パッケージはパッケージルートに公開されているが、個別実装は今後追加予定。
- 外部 API（kabuステーション 等）との統合層は今後の拡張を想定しており、このリリースの多くの関数は読み取り・収集・特徴量生成に注力している。

---

今後のリリースでは次のような点を予定しています:
- Strategy / Execution 層の具体的実装（発注・注文管理・ポジション管理）
- モニタリング（Slack 通知統合）のサンプル実装
- より詳細なテストカバレッジと CI ワークフロー
- パフォーマンス改善（DuckDB 用最適化クエリ、並列収集オプション等）

もし CHANGELOG に追記してほしい点や、各機能の説明をより詳しくまとめてほしい箇所があれば教えてください。