# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム "KabuSys" の基礎機能を実装しました。

### 追加 (Added)
- パッケージ基礎
  - src/kabusys/__init__.py
    - パッケージ名とバージョンを定義（__version__ = "0.1.0"）。
    - public なモジュール一覧を __all__ に定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パースロジック（コメント、exportプレフィックス、クォートとエスケープの扱い、インラインコメント判定など）を実装。
    - 環境変数の取得ラッパー Settings を提供（必須チェック _require、型変換、デフォルト値、検証: KABUSYS_ENV, LOG_LEVEL）。
    - データベースパスのデフォルト（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）や Slack / API トークンの必須設定を定義。

- Data レイヤー
  - src/kabusys/data/schema.py
    - DuckDB 用スキーマ定義（Raw Layer を含むテーブル定義: raw_prices, raw_financials, raw_news, raw_executions 等の DDL を定義）。
    - 初期化用 DDL をモジュールとして管理（DataSchema.md に準拠した3層構造を想定）。

  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。
      - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter を実装。
      - 冪等性を考慮した DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供。ON CONFLICT DO UPDATE を使用。
      - ページネーション対応の取得関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
      - リトライ（指数バックオフ、最大3回）と 401 時のトークン自動リフレッシュ処理を実装。429 の Retry-After ヘッダ尊重。
      - get_id_token によるリフレッシュトークン→IDトークン取得機能。
      - 入力データの安全な変換ユーティリティ (_to_float, _to_int)。

  - src/kabusys/data/news_collector.py
    - RSS フィードからのニュース収集モジュール。
      - RSS 取得（fetch_rss）と前処理（preprocess_text, _normalize_url）を実装。
      - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成する冪等性設計。
      - セキュリティ対策:
        - defusedxml を使った XML パース、XML Bomb や不正要素に対する防御。
        - SSRF 対策（URL スキーム検証、リダイレクト時のスキーム/ホスト検査、プライベートIP拒否）。
        - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）・gzip 解凍後サイズ検査。
        - 既知のトラッキングパラメータ（utm_ 等）の除去とクエリソートによる URL 正規化。
      - DB 保存処理:
        - save_raw_news: チャンク分割・トランザクションでの INSERT ... RETURNING による挿入（重複は ON CONFLICT DO NOTHING）。
        - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括保存（チャンク・トランザクション）。
      - 銘柄抽出ユーティリティ extract_stock_codes（4桁数字パターン、known_codes フィルタ、重複排除）。
      - run_news_collection: 複数ソースの収集を統合、各ソースは独立してエラーハンドリング。

- Research / Feature と Factor 計算
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、DuckDB を用いた一括取得）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関、欠損値処理、最小件数チェック）。
    - rank 関数（同順位は平均ランク、浮動小数点丸めで ties 検出の安定化）。
    - factor_summary（count/mean/std/min/max/median を標準ライブラリのみで計算）。
    - 設計上、DuckDB の prices_daily テーブルのみ参照し外部サービスへはアクセスしないことを明記。

  - src/kabusys/research/factor_research.py
    - モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）ファクターを実装。
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時 None を返す）。
      - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を明示的に制御。
      - calc_value: raw_financials から基準日前の最新財務情報を取得し PER, ROE を算出（EPS が 0/欠損時は None）。
    - DuckDB のウィンドウ関数を活用し、データスキャン範囲にバッファを持たせた設計。

  - src/kabusys/research/__init__.py
    - 主要な研究用関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 変更 (Changed)
- 初版のため該当なし。

### 修正 (Fixed)
- 初版のため該当なし。

### 廃止 (Deprecated)
- 初版のため該当なし。

### セキュリティ (Security)
- news_collector と RSS 処理において SSRF 対策、defusedxml による XML パース、受信サイズ制限、gzip 解凍後サイズ検査を導入。
- jquants_client では認証トークンの取り扱いに注意し、401 に対する自動リフレッシュ処理を実装。リフレッシュ処理は再帰防止で allow_refresh を制御。

---

## マイグレーション / 注意事項
- 初期設定:
  - 必須環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - 未設定の場合は Settings のプロパティアクセスで ValueError が発生します。
  - 自動 .env ロードはプロジェクトルートを .git または pyproject.toml から探索して行います。テスト環境等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DuckDB スキーマ:
  - schema.py に DDL が定義されています。初回起動時にテーブルを作成する初期化処理を呼び出してください（スクリプト化は別途実装想定）。

- J-Quants API:
  - API 呼び出しは内部でレートリミットを守るため遅延が発生します。大量データ取得時は十分な時間を見込んでください。
  - save_* 関数は冪等であり、重複レコードは更新されます。

- News Collector:
  - fetch_rss はデフォルトで UTF-8 以外のエンコーディングを含むフィードに対しても動作するよう設計されていますが、外部フィードの多様性に応じて追加のエンコーディング対応が必要となる場合があります。
  - _urlopen はテスト時にモック可能（kabusys.data.news_collector._urlopen を差し替えられる）で、外部ネットワークへの依存を排除して単体テストが行えます。

- ログレベル / 環境:
  - KABUSYS_ENV は development / paper_trading / live のいずれかである必要があります。LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれかである必要があります。

---

製品改善や不具合報告、ドキュメント追加の要望があれば Issue を作成してください。