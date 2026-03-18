# CHANGELOG

すべての重要な変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠し、意味的バージョニングを想定しています。

※この CHANGELOG は、提供されたコードベースの内容から実装・設計意図を推測して作成した要約です。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-18
初回リリース。以下の主要機能・モジュールを実装。

### Added
- パッケージ基盤
  - kabusys パッケージの初期バージョン（__version__ = "0.1.0"）。
  - public API として data / strategy / execution / monitoring を __all__ に定義。

- 設定管理
  - 環境変数／.env 管理モジュールを追加（kabusys.config.Settings）。
  - .env 自動ロード機能を実装
    - プロジェクトルートの検出は __file__ を起点に `.git` または `pyproject.toml` を探索して行うため、CWD に依存しない。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサは `export KEY=val` 形式、シングル/ダブルクォート、エスケープ、行内コメントなどに対応。
  - 必須環境変数取得での検証機構を提供（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
  - 設定の妥当性チェック（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を実装。
  - デフォルトの DB パス設定（DUCKDB_PATH, SQLITE_PATH）を提供。

- データ層（DuckDB）スキーマ定義
  - Raw Layer 用テーブル DDL を追加（raw_prices, raw_financials, raw_news など）。
  - raw_executions テーブルの定義を開始（発注／約定データ管理のための列を整備）。
  - スキーマは DataSchema.md の設計に準拠（Raw / Processed / Feature / Execution の層構造を想定）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants から株価（日足）・財務データ・マーケットカレンダーを取得するクライアントを実装。
  - 機能:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
    - get_id_token: リフレッシュトークンから ID トークンを取得。
    - save_daily_quotes, save_financial_statements, save_market_calendar: DuckDB へ冪等に保存する関数（ON CONFLICT DO UPDATE を使用）。
  - 信頼性と保護機能:
    - 固定間隔スロットリング（RateLimiter）で API レート制限（120 req/min）を遵守。
    - リトライロジック（指数バックオフ、最大試行回数）を実装。対象はネットワーク系エラーと 408/429/5xx。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰を防止）。
    - モジュールレベルの ID トークンキャッシュを実装（ページネーション間でトークン共有）。
  - レスポンスの型変換ユーティリティ `_to_float`, `_to_int` を実装し、不正値を安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集して raw_news テーブルへ保存する機能を実装。
  - 機能／設計のハイライト:
    - RSS 取得（fetch_rss）：defusedxml を用いた安全な XML パース、gzip 対応、Content-Length / 実バイト数上限（MAX_RESPONSE_BYTES = 10MB）チェック。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時に遷移先のスキームとホストを検査するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
      - ホストがプライベート/ループバック/リンクローカルかを判定し、内部ネットワークへのアクセスを拒否。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証（utm_* 等のトラッキングパラメータを除去して正規化）。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用い、新規挿入された記事 ID を正確に返す。チャンク挿入とトランザクション制御で安全に保存。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（重複除去、チャンク、トランザクション）。
    - 銘柄コード抽出ロジック（extract_stock_codes）：4桁数字パターンを抽出し、known_codes と照合して有効コードのみ返す。
    - run_news_collection: 複数 RSS ソースからの収集・保存・銘柄紐付けを統合。各ソースは独立してエラーハンドリング（1ソース失敗しても他は継続）。

- リサーチ／特徴量（kabusys.research）
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日基準で各ホライズン（デフォルト [1,5,21] 営業日）先の将来リターンを一括で計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算するユーティリティ。欠損や ties に配慮。
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を算出。
    - rank: 同ランクは平均ランクを割り当てるランク付け関数（丸め誤差対策で round を利用）。
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）を計算。データ不足銘柄は None。
    - calc_volatility: atr_20（20日 ATR）・atr_pct、avg_turnover、volume_ratio を計算。true_range の NULL 伝播を明示的に扱う。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を算出（EPS 0/欠損は None）。target_date 以前の最新レコードを ROW_NUMBER で選択。
  - すべてのリサーチ関数は DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみを参照し、本番 API にはアクセスしない設計。

- 公開 API 整合
  - kabusys.research.__init__ にて主要ユーティリティをエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Security
- defusedxml を使用して XML パース攻撃を緩和。
- RSS ダウンロードでのサイズ上限、gzip 展開後のサイズチェック、Content-Length の事前検証を実装し DoS 攻撃に対処。
- SSRF 対策を多数実装（スキーム検証、プライベート IP 検査、リダイレクト検査）。
- J-Quants クライアントでの認証情報の自動リフレッシュとキャッシュ管理により、秘密情報の扱いを慎重に実装。

### Other notes / Usage hints
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- .env 自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後に自動ロードさせたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB への保存関数は冪等性を考慮して実装されているため、定期収集ジョブ等で安全に何度でも実行可能。

### Fixed
- 該当なし（初回リリース）

---

（終）