# Changelog

すべての変更は Keep a Changelog のフォーマットに従います。  
安定版リリースはセマンティックバージョニングを使用します。

※ このファイルはソースコード内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」の基盤となる以下の機能を実装・提供します。

### Added
- パッケージ初期化
  - パッケージメタ情報を公開（kabusys.__version__ = 0.1.0）。
  - 公開サブパッケージ: data, strategy, execution, monitoring。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動ロード。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサを実装（export プレフィックス・クォート・インラインコメント対応、エスケープ処理）。
  - 環境変数取得ユーティリティ Settings を提供し、必須変数取得時のバリデーションを実装。
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等の必須チェック。
  - 環境種別（development/paper_trading/live）とログレベル（DEBUG/INFO/…）の検証ロジック。
  - duckdb/sqlite のデフォルトパスを設定するプロパティを提供。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制御（固定間隔スロットリング、120 req/min）を実装する RateLimiter。
  - 再試行ロジック（指数バックオフ、最大 3 回）を実装（408/429/5xx を対象）。
  - 401 受信時のリフレッシュトークンからの id_token 自動更新（1 回のみ）を実装。
  - ページネーション対応の fetch_* 関数を提供:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務四半期データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB へ冪等保存する save_* 関数を実装（ON CONFLICT DO UPDATE/DO NOTHING 利用）:
    - save_daily_quotes → raw_prices テーブル
    - save_financial_statements → raw_financials テーブル
    - save_market_calendar → market_calendar テーブル
  - 型変換ユーティリティ (_to_float, _to_int) を実装して不正データに頑健な処理を行う。
  - データ取得時の fetched_at を UTC で記録し、look-ahead bias のトレースを可能に。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集パイプラインを実装。
    - fetch_rss: RSS 取得・XML パース（defusedxml 使用）・記事整形・記事リスト返却。
    - save_raw_news: raw_news テーブルへバルク挿入（チャンク、トランザクション、INSERT ... RETURNING を使用）し新規挿入IDを返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT で重複を除外）。
    - run_news_collection: 複数ソースの収集を統合するジョブを実装。
  - セキュリティ／堅牢性のための実装:
    - SSRF 対策: リダイレクトハンドラでスキームとホスト検査、開始時にホストがプライベートかをチェック。
    - URL スキーム検証（http/https のみ許可）。
    - 最大受信バイト数制限（10 MB）・gzip の安全な展開（Gzip bomb 対策）。
    - XML パースエラーは安全にログ出力して空リストでフォールバック。
  - ニュース前処理:
    - URL 正規化（tracking パラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - 記事ID は正規化 URL の SHA-256 の先頭 32 文字で生成（冪等性確保）。
    - テキスト前処理（URL 除去、空白正規化）。
    - 銘柄コード抽出（4 桁数字パターン、known_codes によるフィルタ、重複除去）。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataSchema.md に基づく Raw / Processed / Feature / Execution 層のスキーマ定義のうち Raw 層の DDL を実装:
    - raw_prices, raw_financials, raw_news 等の CREATE TABLE 文を定義。
  - スキーマ初期化用モジュールの雛形を整備（DDL 定義をモジュールで管理）。

- リサーチ／特徴量探索（kabusys.research）
  - feature_exploration:
    - calc_forward_returns: 指定日から各ホライズン先の将来リターンを DuckDB の prices_daily テーブルから一括取得して計算。
    - calc_ic: factor_records と forward_records を code で結合し、Spearman のランク相関（IC）を計算。rank ユーティリティを併設。
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を計算。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を計算。
    - calc_volatility: 20 日 ATR、atr_pct、avg_turnover、volume_ratio を計算（true range の NULL 伝播を明示的に扱う）。
    - calc_value: raw_financials から最新財務を結合して PER（EPS が 0/欠損時は None）、ROE を計算。
  - 研究モジュールのエクスポートを提供（zscore_normalize は kabusys.data.stats から参照）。

### Security
- news_collector にて SSRF や XML 関連攻撃（XML Bomb）への対策を実装。
- RSS レスポンス長の上限を設けメモリ DoS を軽減。

### Notes / Implementation details
- 環境変数読み込み順序: OS 環境変数 > .env.local > .env。既定では OS 環境変数を保護しつつ .env を上書きする動作を採用。
- J-Quants クライアントはページネーションをサポートし、モジュールレベルで id_token キャッシュを共有してリクエスト効率を図る。
- DuckDB への保存は可能な限り冪等に設計（UNIQUE / PRIMARY KEY に対する ON CONFLICT 処理）。
- research モジュールは本番 API（発注等）にアクセスしない設計。DuckDB の prices_daily / raw_financials だけを参照する前提。
- 一部ソースは外部モジュール（例: defusedxml、duckdb）への依存があるため、本リリースではそれらの導入が必要。

### Known limitations / TODO
- schema.py の Execution 層 DDL 定義が一部ファイル切れで末尾が未完（raw_executions の定義が途中）に見えるため、Execution 層の完全実装が必要。
- strategy, execution, monitoring パッケージはパッケージ宣言があるが具象実装が未配置（今後の追加予定）。
- zscore_normalize の実装は本差分中では参照のみ（kabusys.data.stats の実装を整備する必要あり）。
- 単体テスト、例外時のリトライ境界やレート制御の詳細検証は今後強化の余地あり。

---

脚注:
- 本 CHANGELOG は提示されたソースコードからの推測で作成しています。実際のリリースノートや履歴とは差異がある可能性があります。必要であれば、日付や項目を実プロジェクトの履歴に合わせて調整してください。