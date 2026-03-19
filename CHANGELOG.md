# Changelog

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを用いています。

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。
主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを `0.1.0` に設定（src/kabusys/__init__.py）。
  - パッケージの公開モジュール一覧を __all__ に定義（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイル（および .env.local）または OS 環境変数から設定を自動読み込みする機能を実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出は .git / pyproject.toml を起点に行い、CWD に依存しない設計。
    - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env のパースは export 形式、クォートやエスケープ、インラインコメントを考慮。
  - 設定アクセス用クラス `Settings` を提供（例: jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）や is_live / is_paper / is_dev のブールプロパティを実装。
  - 必須環境変数未設定時は明示的なエラーを送出。

- データクライアント: J-Quants API（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティを実装（_request）。
    - レートリミット 120 req/min を固定間隔スロットリングで制御（内部 RateLimiter）。
    - リトライロジック（指数バックオフ、最大試行回数 3 回）、ステータスコード 408/429/5xx を対象。
    - 401 受信時はリフレッシュトークンで id_token を自動再取得し 1 回リトライ（無限再帰防止）。
    - ページネーション対応（pagination_key の継続取得）。
  - 認証関数 get_id_token（リフレッシュトークン -> id_token）。
  - データ取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等性確保: ON CONFLICT DO UPDATE）:
    - save_daily_quotes -> raw_prices
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - 入力データの型変換ユーティリティ: _to_float, _to_int（安全に None を返す仕様や float 文字列の扱いを定義）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集・前処理・DuckDB へ保存する機能を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス判定、リダイレクト時の検査（専用 RedirectHandler）。
    - レスポンス上限（MAX_RESPONSE_BYTES = 10MB）や gzip 解凍後の再検査（Gzip bomb 対策）。
  - URL 正規化 (_normalize_url) とトラッキングパラメータ除去（utm_* 等）。
  - 記事 ID の生成は正規化 URL の SHA-256（先頭32文字）を使用し冪等性を保証。
  - テキスト前処理（URL 除去・空白正規化）。
  - RSS 取得関数 fetch_rss:
    - content:encoded を優先、description フォールバック。
    - pubDate のパースと UTC 変換（失敗時は警告ログ）。
  - DuckDB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を使い、実際に挿入された記事IDを返す。チャンク分割 & トランザクション処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付け保存（ON CONFLICT DO NOTHING + RETURNING で挿入数を取得）。チャンク & トランザクション。
  - 銘柄コード抽出: テキスト中の 4 桁数字を抽出し、既知銘柄セットでフィルタ（extract_stock_codes）。
  - 統合ジョブ run_news_collection: 複数ソースを順次処理し、各ソースごとにエラーハンドリングして継続処理。既知銘柄が与えられれば自動で紐付けを行う。

- データスキーマ（DuckDB）初期定義（src/kabusys/data/schema.py）
  - Raw Layer 用の DDL を追加:
    - raw_prices, raw_financials, raw_news, raw_executions（途中まで定義）
  - DataSchema.md に基づく 3 層構造（Raw / Processed / Feature / Execution）を想定した設計。

- 研究用/特徴量計算モジュール（src/kabusys/research/）
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（horizons デフォルト [1,5,21]、DuckDB の prices_daily を参照）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ、ランク関数を内部実装）。
    - factor_summary（count/mean/std/min/max/median）。
    - rank（同順位は平均ランク、丸め処理で ties の検出漏れを防止）。
    - 設計上、標準ライブラリのみで実装（pandas 等に依存しない）。
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタムファクター calc_momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - ボラティリティ / 流動性 calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - バリュー calc_value（per, roe、raw_financials と prices_daily を組み合わせて算出）
    - 各関数は DuckDB 接続を受け取り prices_daily / raw_financials のみ参照、結果は (date, code) キーの dict リストで返す。
  - research パッケージの __init__ で主要関数群を再エクスポート。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 互換性に関する注意 (Compatibility)
- Settings の必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）が未設定の場合、起動時またはアクセス時に ValueError を送出します。デプロイ時は .env または OS 環境変数を適切に設定してください。
- DuckDB スキーマの初期化は本リリースでの DDL に基づきます。既存データベースがある場合はスキーマの差分に注意してください（初回リリースなので破壊的変更は想定していませんが、運用時はバックアップ推奨）。

### セキュリティ (Security)
- RSS パーサーは defusedxml と SSRF 検査を導入しており、外部からの XML 攻撃や内部ネットワークへの接続リスクを低減しています。
- J-Quants クライアントはトークン管理・自動リフレッシュを行いますが、リフレッシュトークンは秘匿して管理してください。

---

今後の予定（例）
- Strategy / Execution / Monitoring モジュールの本格実装（ポジション管理・発注周り）
- Feature Layer の永続化・更新ジョブ
- テストカバレッジ拡充・CI 設定

（注）本 CHANGELOG はコード内容から推測して作成しています。実際のリリースノートとして公開する前に必要に応じて加筆・修正してください。