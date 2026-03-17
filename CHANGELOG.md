# Changelog

すべての変更点はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、重要な変更のみを列挙します。

最新: Unreleased

## [Unreleased]

- 今後の変更のためのプレースホルダ。

## [0.1.0] - 2026-03-17

初回リリース — KabuSys 日本株自動売買システムのコアモジュール群を実装しました。

### 追加 (Added)
- パッケージ基礎
  - パッケージエントリポイント `kabusys` を追加。公開モジュール: data, strategy, execution, monitoring。
  - バージョン情報 `__version__ = "0.1.0"` を設定。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出は .git または pyproject.toml を基準）。
  - .env のパース機能を実装（コメント、export プレフィックス、クォート内エスケープ、インラインコメント取り扱い等に対応）。
  - 自動読み込みを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 必須環境変数取得ヘルパー `_require()` と `Settings` クラスを追加。設定項目（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV (development/paper_trading/live 検証)、LOG_LEVEL（許容値検証）
  - 設定クラス経由の便利プロパティ（is_live, is_paper, is_dev）を追加。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足、財務データ、JPX マーケットカレンダー取得のためのクライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx の再試行）を実装。
  - 401 受信時の自動トークンリフレッシュ（1回）を実装。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への冪等的保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ変換ユーティリティ (_to_float, _to_int) と fetched_at UTC 記録。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得から raw_news への保存までの一連処理を実装。
  - 記事IDを URL 正規化（トラッキングパラメータ除去）→ SHA-256（先頭32文字）で生成し冪等性を保証。
  - defusedxml を用いた安全な XML パース（XML Bomb 対策）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）
    - リダイレクト先スキーム＆プライベートIP 検査（カスタム RedirectHandler）
    - ホストのプライベート判定（IP 直接判定／DNS 解決した A/AAAA 全検査）
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
  - テキスト前処理（URL 除去、空白正規化）と記事抽出ロジック。
  - DuckDB へのバルク挿入（チャンク化、トランザクション、INSERT ... RETURNING）を実装:
    - save_raw_news（新規挿入ID リストを返す）
    - save_news_symbols（単一記事の銘柄紐付け）
    - _save_news_symbols_bulk（複数記事の一括紐付け）
  - 銘柄コード抽出ユーティリティ extract_stock_codes（4桁数字、既知コードセットでフィルタ）。
  - 統合収集ジョブ run_news_collection を実装（各ソースの独立エラーハンドリング、紐付け処理）。

- データベーススキーマ (src/kabusys/data/schema.py)
  - DuckDB 用スキーマ定義（DataPlatform.md 準拠）。三層（Raw / Processed / Feature）および Execution 層を含む主要テーブルを作成:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PK/FOREIGN KEY/CHECK）を定義。
  - 検索パフォーマンスを考慮したインデックス群を定義。
  - init_schema(db_path) によりファイル作成／DDL 実行を行い、接続を返す。get_connection() で既存 DB へ接続可能。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計方針に沿ったパイプライン基礎を実装。
  - ETLResult dataclass により ETL 実行結果（フェッチ数、保存数、品質問題、エラー）を表現。
  - スキーマ存在チェック、最大日付取得ユーティリティ（_table_exists, _get_max_date, get_last_price_date 等）を実装。
  - 市場カレンダーに基づく営業日調整ヘルパー _adjust_to_trading_day を実装。
  - 差分更新ロジック（最終取得日 - backfill_days から再取得）を備えた run_prices_etl を実装（差分取得→保存→ログ）。

### 変更 (Changed)
- 設計方針やログメッセージにおいて「冪等性」「Look-ahead Bias 防止」「セキュリティ（SSRF・XML Bomb）」を明示的に反映。

### 修正 (Fixed)
- 初期実装段階につき既知のバグ修正履歴なし。

### セキュリティ (Security)
- ニュース収集における複数のセキュリティ対策を導入:
  - defusedxml による XML パース
  - SSRF ブロッキング（スキーム検証、プライベートIP 判定、リダイレクト時検査）
  - レスポンスサイズの制限（メモリ DoS 対策）
  - URL 正規化でトラッキングパラメータ除去（外部呼び出しの一貫性向上）
- J-Quants クライアントはトークン管理と自動リフレッシュを実装し、不正な再帰を回避（allow_refresh フラグ）。

### 既知の注意点 / 既知の制限
- pipeline.run_prices_etl は差分ロジック・保存処理を実装済みだが、品質チェック（quality モジュールの評価呼び出し）やその他 ETL ジョブ（財務・カレンダーの全体的な自動化）は引き続き統合が必要。
- strategy、execution、monitoring パッケージの初期モジュールは用意されているが、本コードベースには具体的な戦略ロジックや実注文明細の実装は含まれていません（骨組み）。
- ユニットテスト・統合テストは本実装からの追加が推奨されます。特にネットワーク I/O、DB トランザクション、SSRF 判定ロジックについてはモック/フェイクを用いたテストが必要です。

---

配布・運用メモ:
- 必要な環境変数を .env/.env.local に設定してください（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
- デフォルトの DuckDB パスは data/kabusys.duckdb、SQLite（監視用）は data/monitoring.db。
- 自動 .env ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。