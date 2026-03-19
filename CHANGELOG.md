# Keep a Changelog
すべての変更は逆順で記載します。  
フォーマットは「Keep a Changelog」準拠です。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システムの基盤機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0、主要サブパッケージを __all__ で公開）。
  - 空のサブパッケージスケルトン: execution, strategy（将来的な発注・戦略実装用）。

- 環境設定 / 設定管理 (kabusys.config)
  - .env 自動ロード機能（プロジェクトルートの .git / pyproject.toml を基準に .env/.env.local を読み込み）。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント処理等に対応）。
  - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスにより環境変数をラップ：
    - 必須変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV。
    - env/log level の値検証（許容値を限定）。
    - ユーティリティプロパティ: is_live / is_paper / is_dev。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティ _request 実装（JSON デコード、最大リトライ、指数バックオフ、Retry-After 対応）。
  - レートリミッタ実装（120 req/min 想定、固定間隔スロットリング）。
  - ID トークンの自動取得とモジュールレベルキャッシュ（get_id_token / _get_cached_token）。
  - 401 (Unauthorized) 受信時の自動トークンリフレッシュ（1 回のみリトライ）。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション処理）
    - fetch_financial_statements（財務データ、ページネーション処理）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB へ冪等保存する保存関数:
    - save_daily_quotes（raw_prices への INSERT ... ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials への冪等保存）
    - save_market_calendar（market_calendar への冪等保存）
  - 型変換ユーティリティ: _to_float / _to_int（堅牢な変換と空値扱い）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS 収集パイプライン:
    - fetch_rss: RSS フィード取得、gzip 対応、XML パース（defusedxml 使用）、最大受信サイズチェック（10 MB）などの安全対策。
    - 記事前処理: URL 除去、空白正規化。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url）。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - SSRF 対策: URL スキーム検証（http/https のみ）、プライベートアドレス/ループバックの検出とブロック、リダイレクト先の検査。
    - RSS 内の link/guid の取り扱い、content:encoded 優先処理。
  - DuckDB への保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + INSERT RETURNING で新規挿入IDを収集。チャンク挿入・1 トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等に挿入。チャンク化とトランザクション管理。
  - 銘柄コード抽出ユーティリティ: extract_stock_codes（4桁コード抽出、known_codes によるフィルタ、重複除去）。
  - 統合ジョブ run_news_collection: 複数ソースの収集と保存、エラーハンドリング、銘柄紐付け処理を実装。
  - デフォルト RSS ソース: Yahoo Finance のビジネスカテゴリを設定。

- データスキーマ / DuckDB 初期化 (kabusys.data.schema)
  - DataSchema に基づく DDL 定義（Raw 層のテーブルを実装）:
    - raw_prices（生 OHLCV、fetched_at、(date, code) PK、型チェック）
    - raw_financials（財務データ、report_date, period_type を PK に含む）
    - raw_news（RSS 記事、id を PK に持つ）
    - raw_executions（発注/約定用テーブルのスキーマを部分実装・定義開始）
  - スキーマ定義は DuckDB 向けの制約・CHECK を含むテーブル設計。

- リサーチ / ファクター計算 (kabusys.research)
  - feature_exploration モジュール:
    - calc_forward_returns（指定日に対する将来リターン計算、複数ホライズン対応、DuckDB SQL を使用）
    - calc_ic（ファクターと将来リターンのスピアマンランク相関計算、ties 処理、最小サンプルチェック）
    - factor_summary（count/mean/std/min/max/median を標準ライブラリのみで計算）
    - rank（同順位の平均ランク、丸めによる ties 対応）
    - 設計: DuckDB の prices_daily テーブル参照のみ、外部 API にはアクセスしない、pandas 等に依存しない実装。
  - factor_research モジュール:
    - calc_momentum（mom_1m/mom_3m/mom_6m, ma200_dev を計算、ウィンドウ不足時は None）
    - calc_volatility（20日 ATR、相対 ATR、avg_turnover、volume_ratio 計算、NULL 伝播に注意した true_range 計算）
    - calc_value（raw_financials から最新の財務データを結合して PER/ROE を算出）
    - 設計: prices_daily / raw_financials のみ参照、DuckDB SQL を活用、結果は (date, code) 辞書リストで返却。
  - research パッケージ初期公開関数を __all__ でまとめてエクスポート（外部利用性向上）。
  - data.stats.zscore_normalize との連携を想定（インポート済）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector に以下のセキュリティ対策を追加:
  - defusedxml の使用による XML 攻撃対策。
  - SSRF 回避のためのスキーム/ホスト検査、リダイレクト時検査。
  - レスポンスサイズ上限のチェック（Gzip を含む）で DoS 対策。

### 既知の制限 / 注意点 (Notes)
- リサーチ用関数は外部ライブラリ（pandas 等）に依存せず標準ライブラリと DuckDB SQL のみで実装されているため、大規模データ処理時にメモリ/性能チューニングが必要な場合があります。
- get_id_token は settings.jquants_refresh_token を必須とします。CI / 実行環境では環境変数の設定が必要です。
- news_collector の extract_stock_codes は単純に 4 桁数字を抽出する実装のため、文脈解析が必要なケースでは誤抽出の可能性があります。known_codes セットでフィルタリングすることを想定しています。
- schema モジュールは Raw 層の DDL を定義しますが、Processed / Feature / Execution 層の完全な DDL は今後追加予定です。

### マイグレーション / 設定方法
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 任意（デフォルトあり）:
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)
  - KABUSYS_ENV (development/paper_trading/live、デフォルト: development)
- パッケージはプロジェクトルートの .env/.env.local を自動で読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

（今後のリリースでは Strategy / Execution の実装、Processed/Feature 層のスキーマ・ETL、パフォーマンス改善やユニットテストの追加を予定しています。）