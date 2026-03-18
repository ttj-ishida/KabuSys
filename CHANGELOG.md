# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-18
初回リリース。日本株の自動売買システム KabuSys の基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - モジュール構成 (data, strategy, execution, monitoring) の公開。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルート検出: .git / pyproject.toml を探索）。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パース機能を強化（export 形式、シングル／ダブルクォート、インラインコメント、エスケープ処理に対応）。
  - Settings クラスを提供し、J-Quants リフレッシュトークン、kabu ステーション API 設定、Slack 設定、DB パスなどのプロパティを取得可能。
  - KABUSYS_ENV と LOG_LEVEL の検証（有効値チェック）と利便性プロパティ（is_live 等）を追加。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本的な HTTP リクエストユーティリティと JSON デコード処理を実装。
  - レート制御（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 受信時にリフレッシュトークンで自動的に id_token を再取得して 1 回だけリトライ。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足・OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、空値や不整合に耐性を持たせる。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias 対策を考慮。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し、raw_news / news_symbols に保存する ETL を実装。
  - 収集ワークフロー:
    - fetch_rss: HTTP(S) のみ許可、Content-Length および受信バイト数上限（10 MB）で保護、gzip 解凍対応、XML パース（defusedxml）による安全化。
    - preprocess_text: URL 除去・空白正規化。
    - 記事 ID を正規化した URL の SHA-256 ハッシュ（先頭32文字）で生成して冪等性を確保（UTM 等トラッキングパラメータを除去）。
    - save_raw_news: チャンク分割・トランザクション・INSERT ... RETURNING を用いて実際に挿入された ID を返却。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを効率的かつ冪等に保存。
    - extract_stock_codes: テキストから 4 桁銘柄コードを抽出（known_codes に基づくフィルタリング、重複除去）。
    - run_news_collection: 複数ソースを巡回して収集・保存・銘柄紐付けを一括実行（ソース単位でエラーハンドリング）。
  - SSRF 対策:
    - リダイレクト時にスキーム検証とホストのプライベートアドレス検査を行う専用ハンドラを導入（_SSRFBlockRedirectHandler）。
    - 最終 URL の追加検証、DNS 解決で取得したアドレスに対するプライベート判定実装。
  - 大規模/悪意あるペイロード対策:
    - MAX_RESPONSE_BYTES による読み取り上限、gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - defusedxml を使用して XML ベースの攻撃を緩和。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataPlatform 設計に基づく多層スキーマを定義（Raw / Processed / Feature / Execution）。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（PRIMARY KEY / FOREIGN KEY / CHECK）を多数付与。
  - クエリ対象のパフォーマンスを改善するためのインデックス群を定義。
  - init_schema(db_path) によりディレクトリ作成・DDL 実行・インデックス作成を行い、初期化済み接続を返す。
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラス（取得数・保存数・品質問題・エラーなどを集約）を提供。
  - 差分更新用ユーティリティ:
    - テーブル存在チェック、最大日付取得（_get_max_date）、市場営業日調整ヘルパー（_adjust_to_trading_day）。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
  - run_prices_etl: 差分更新ロジック（最終取得日 - backfill_days を開始日とする）に基づいて jquants_client を使って取得→保存を行う実装（backfill デフォルトは 3 日）。
  - 全体設計方針として、品質チェックを実行しても ETL を継続する（Fail-Fast ではない）、id_token の注入でテスト容易性を確保。

### Security
- 外部データ取込部（RSS, HTTP）のセキュリティ対策を実装:
  - defusedxml による XML パース、SSRF 対策（スキーム/プライベートIP 検査）、受信サイズ上限、gzip 解凍後のサイズ検査を導入。
  - 環境変数読み込みは OS 環境変数を保護する仕組み（.env.local の上書き挙動制御）を用意。

### Known issues / Notes
- run_prices_etl のモジュール末尾に戻り値の記述が途切れている箇所が見られます（ソースが途中で切れている可能性）。実行時の戻り値の扱いについては確認・修正が必要です。
- 初期バージョンのため、運用上の細かいケース（大規模同時アクセス、非常に大きな RSS フィードの取り扱い、外部 API の挙動差異など）は実運用で追加の調整・監視が必要です。

### Migration / Upgrade notes
- 初回リリースのため、既存データ移行は想定していません。init_schema() により新しい DuckDB ファイルを作成して使用してください。
- .env.example 等を参照して必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）を設定してください。

---

今後の予定（例）
- pipeline 健全性チェック（quality モジュール）との連携強化。
- strategy / execution / monitoring モジュールの実装と CI テストの追加。
- run_prices_etl 等の追加 ETL ジョブの完成と統合テスト。

（この CHANGELOG はソースコードの内容から推測して作成しています。運用用の正式なリリースノートには実際のリリース手順・変更履歴を反映してください。）