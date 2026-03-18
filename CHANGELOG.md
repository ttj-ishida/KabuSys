# Changelog

すべての注目すべき変更をここに記録します。  
この文書は "Keep a Changelog" の形式に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 初回リリース
最初の公開リリース。以下の主要機能群を実装しています。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ にて公開。

- 設定/環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能:
    - プロジェクトルートを __file__ を起点に .git または pyproject.toml で探索。
    - OS 環境変数 > .env.local > .env の優先順位で読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env 読み込み時に既存 OS 環境変数を保護する仕組み（protected keys）。
  - .env パーサーは export KEY=val 形式、クォートやインラインコメントを考慮したパースを実装。
  - Settings に各種必須設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）と既定値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）を提供。
  - 環境値検証:
    - KABUSYS_ENV は (development, paper_trading, live) のいずれかでなければ例外を投げる。
    - LOG_LEVEL は標準的なログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）のみ許容。

- データ取得 / 永続化 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限: 固定間隔スロットリング (_RateLimiter) により 120 req/min を制御。
  - 自動リトライ:
    - ネットワーク/一部 HTTP エラー (408, 429, 5xx) に対して指数バックオフで最大再試行。
    - 429 の場合は Retry-After ヘッダを優先。
  - 認証とトークン管理:
    - リフレッシュトークンから ID トークンを取得する get_id_token を提供。
    - モジュールレベルの ID トークンキャッシュを保持し、401 受信時に自動リフレッシュして 1 回再試行。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装。
  - DuckDB への保存関数（冪等化）:
    - save_daily_quotes, save_financial_statements, save_market_calendar。INSERT ... ON CONFLICT DO UPDATE を利用して冪等性を確保。
  - 型変換ユーティリティ: _to_float / _to_int（入力の寛容な変換と健全性チェック）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news / news_symbols に保存するモジュールを実装。
  - セキュリティと堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - SSRF 対策: リダイレクト先のスキーム検証、プライベート IP / ループバック / リンクローカルの検出・拒否。
    - カスタムリダイレクトハンドラ (_SSRFBlockRedirectHandler) を導入し、リダイレクト前に検証。
    - URL スキームは http / https のみ許可。
    - レスポンスサイズ制限 (MAX_RESPONSE_BYTES = 10MB)、gzip 解凍後のサイズチェック、受信過多を防止。
  - フィード処理:
    - URL 正規化とトラッキングパラメータ除去（_normalize_url）。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）。
    - pubDate パースと UTC 変換（失敗時は代替時刻を使用）。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を用い、挿入された新規記事 ID を返す。チャンク挿入・トランザクションを採用。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンクで実行し、新規挿入数を正確に返す。重複除去とトランザクション管理あり。
  - 銘柄コード抽出:
    - extract_stock_codes: テキスト中の 4 桁数字を抽出し、known_codes フィルタで有効な銘柄のみ返す。
  - 統合ジョブ:
    - run_news_collection: 複数 RSS ソースをループして収集→保存→銘柄紐付けを行う。ソース単位でエラーハンドリングし、1 ソース失敗でも他ソースは継続。

- リサーチ / ファクター計算 (kabusys.research)
  - feature_exploration モジュール:
    - calc_forward_returns: 指定基準日から複数ホライズン先の将来リターンを一度に計算（DuckDB の window 関数を活用）。
    - calc_ic: ファクター値と将来リターンのスピアマン順位相関（IC）を計算。少数サンプルや定数分散時に None を返す。
    - rank: 同順位は平均ランクを与えるランク関数（浮動小数の丸め考慮）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - 設計方針: DuckDB の prices_daily テーブルのみ参照、外部ライブラリに依存しない実装。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離）を計算。データ不足時は None。
    - calc_volatility: atr_20（ATR 平均）、atr_pct（ATR / close）、avg_turnover、volume_ratio を計算。NULL 伝播や cnt に基づく判定を適切に処理。
    - calc_value: raw_financials から基準日以前の最新財務を取得し PER/ROE を算出（EPS=0/NULL の場合は PER を None）。
    - 設計方針: DuckDB の prices_daily / raw_financials のみ参照、外部APIにアクセスしない。
  - research パッケージ __init__ で計算関数や zscore_normalize（kabusys.data.stats 由来）を再公開。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用の DDL を定義:
    - raw_prices, raw_financials, raw_news, raw_executions（途中まで定義）などのテーブル定義を実装。
  - スキーマ設計は Raw / Processed / Feature / Execution の多層構造を想定。

### Security
- news_collector における SSRF 対策、defusedxml の採用、レスポンスサイズ制限、URL スキーム検証など多数の防御策を導入。
- jquants_client の HTTP リクエスト処理で JSONException 等の扱いを明示し、エラー文言を含めた例外処理を実装。

### Performance
- J-Quants API 呼び出しに対する固定間隔スロットリングでレート制限を厳守。
- DuckDB へのバルク挿入はチャンク化して一括実行し、トランザクションをまとめてオーバーヘッドを削減。
- calc_forward_returns 等、複数ホライズンをまとめて一度に取得する SQL による最適化。

### Notes / Breaking changes (注意事項)
- Settings の必須プロパティは未設定だと ValueError を送出します。運用前に .env を用意してください（.env.example を参照のこと）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を環境変数で設定すると自動 .env ロードを無効化できます（テストや CI で想定）。
- research モジュールは外部ライブラリ非依存（標準ライブラリ + duckdb）で設計されています。duckdb 接続オブジェクトを引数に渡して使用します。
- news_collector の URL/ホスト検証は保守的です。内部ホストや特殊スキームのフィードを明示的に利用する場合は事前に設計を見直してください。
- raw_executions の DDL はファイル末尾で途切れており（提供コードの範囲に依存）、実運用前に完全なテーブル定義とマイグレーションが必要です。

---

今後の変更やリリースでは、Added / Changed / Fixed / Security といったカテゴリで追記します。