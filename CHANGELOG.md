# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-19

初回リリース。以下の主要機能と実装が含まれます。

### 追加 (Added)
- パッケージ基盤
  - パッケージバージョンを定義（kabusys.__version__ = 0.1.0）。
  - モジュール公開インターフェースを定義（data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env/.env.local 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサを実装（コメント、export 形式、シングル/ダブルクォート、エスケープ対応）。
  - 自動読み込みを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須設定取得メソッド _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等を取得）。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の値検証を実装（有効値のバリデーション）。
  - データベースパス設定（DUCKDB_PATH / SQLITE_PATH）、環境判定ユーティリティ（is_live / is_paper / is_dev）。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 応答で自動トークンリフレッシュ（1 回のみ）を行い再試行する仕組み。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT DO UPDATE）。
  - 型安全な変換ユーティリティ (_to_float, _to_int) を実装。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード取得・前処理・DB 保存の一連処理を実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML bomb 対策）。
    - SSRF 対策（アクセス先・リダイレクト先のスキーム検証、プライベートアドレス拒否）。
    - URL スキーム検証は http/https のみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を実装（Content-Length と実際の読み込みの両方で検査）。
    - gzip 圧縮の取り扱いと解凍後サイズ検査（Gzip bomb 対策）。
  - URL 正規化（tracking パラメータ除去、ソート、フラグメント除去、小文字化）と SHA-256 ベースの記事 ID 生成（先頭32文字）。
  - テキスト前処理（URL 除去、空白正規化）。
  - raw_news への冪等保存（INSERT ... ON CONFLICT DO NOTHING + RETURNING id）とチャンク挿入、トランザクション管理。
  - news_symbols（記事と銘柄の紐付け）保存ロジック（INSERT ... RETURNING を使用）とバルク保存内部実装。
  - テキストからの銘柄コード抽出ユーティリティ（4桁数字、重複除去、既知コードフィルタ）。
  - 複数 RSS ソースを巡回して収集する run_news_collection 関数（ソース単位で耐障害性あり）。

- 研究用モジュール (kabusys.research)
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、1クエリで取得、欠損時は None）。
    - IC（スピアマンのランク相関）計算 calc_ic（欠損や ties を考慮、有効レコード < 3 の場合 None）。
    - ランク計算ユーティリティ rank（同順位は平均ランク、丸めで ties 判定漏れを防止）。
    - factor_summary（count/mean/std/min/max/median を算出）。
    - 実装は pandas 等に依存せず標準ライブラリ + duckdb を想定。
  - factor_research:
    - Momentum ファクター calc_momentum（mom_1m / mom_3m / mom_6m / ma200_dev、必要データ不足時は None）。
    - Volatility / Liquidity ファクター calc_volatility（20日 ATR/相対ATR/20日平均出来高/出来高比率）。
    - Value ファクター calc_value（raw_financials と価格を結合して PER / ROE を算出、EPS=0/欠損時は None）。
    - 各関数は prices_daily / raw_financials のみ参照し、本番 API 等にはアクセスしない設計。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw レイヤーの DDL を定義・初期化する SQL 定義を提供。
  - raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義を含む（Primary Key / 型チェックを含む）。
  - スキーマは DataSchema.md に基づく3層構造を想定。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 破壊的変更 (Breaking Changes)
- 初期リリースのため該当なし。ただし以下点に注意ください:
  - Settings._require は必須環境変数が未設定の場合 ValueError を投げます。デプロイ前に必要な環境変数を設定してください:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - KABUSYS_ENV と LOG_LEVEL は許可値以外を指定すると ValueError を投げます（有効値は config モジュール内定義を参照）。

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector: SSRF 対策、XML パースの安全化、レスポンスサイズ制限、gzip 解凍後サイズ検査を導入。
- jquants_client: 401 での自動トークンリフレッシュ処理を実装し、認証トークンの取り扱いを改善。
- .env の自動ロードはプロジェクトルート判定に依存するため、外部環境からの意図しない読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能。

### 既知の制限 / 今後の作業
- strategy / execution / monitoring パッケージは __init__ のみで実装は未完（将来の戦略、発注ロジック、監視機能の実装予定）。
- calc_value では現時点で PBR / 配当利回りは未実装。
- テストスイート・CI の設定は本リリースに含まれていない（別途整備予定）。
- DuckDB スキーマ定義の一部（execution 関連テーブル定義の続きなど）はファイル内で継続して定義される想定（抜粋のため断片的に見える箇所があります）。

もし本 CHANGELOG に関して補足や特に詳述してほしい項目（例: 各関数の使用例、設定手順、移行手順など）があれば教えてください。