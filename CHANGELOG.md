# Changelog

すべての主要な変更は「Keep a Changelog」形式に準拠して記載しています。  
このファイルはコードベースからの推測に基づき初期リリースの変更点をまとめたものです。

全般的な注意
- 日付や一部の実装詳細はソースコードのコメント・定数から推測して記載しています。
- strategy/execution パッケージは現時点では公開モジュールのみ（雛形）で、個別実装はこれからの想定です。
- 一部関数が継続実装を想定した状態（雛形）になっている箇所があります。

## [0.1.0] - 初回リリース
リリース日: 未設定

### 追加
- パッケージ全体
  - kabusys パッケージの初期構成を追加。__version__ = 0.1.0、公開サブモジュール（data, strategy, execution, monitoring）を定義。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（OS環境変数 > .env.local > .env の優先順位）。プロジェクトルートは .git または pyproject.toml で検出。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - .env ファイルの行パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープに対応）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベース パス等の設定取得を簡易化。
  - KABUSYS_ENV（development|paper_trading|live）と LOG_LEVEL（DEBUG/INFO/...） のバリデーションを実装。
  - duckdb/sqlite のデフォルトパスを設定し Path を展開して返すユーティリティを提供。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限コントロール（120 req/min 固定間隔スロットリング）を実装（_RateLimiter）。
  - 冪等性を考慮した保存ロジック（DuckDB への INSERT ... ON CONFLICT DO UPDATE）を実装。
  - リトライロジック（指数バックオフ、最大3回。HTTP 408/429/5xx を再試行対象）を実装。
  - 401 Unauthorized を検知した場合、リフレッシュトークンにより id_token を自動更新して 1 回だけリトライする処理を実装。
  - ページネーション対応（pagination_key による繰返しフェッチ）。
  - データ取得時に取得時刻（fetched_at）を UTC ISO8601 形式で記録。
  - fetch/save 関連:
    - fetch_daily_quotes / save_daily_quotes（raw_prices に保存）
    - fetch_financial_statements / save_financial_statements（raw_financials に保存）
    - fetch_market_calendar / save_market_calendar（market_calendar に保存）
  - 型変換ユーティリティ（_to_float / _to_int）を実装し入力の堅牢性を確保。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからのニュース収集機能を実装。
  - セキュリティ・堅牢性対策を実装:
    - defusedxml を使用して XML 関連の脆弱性対策。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス判定（DNS 解決して A/AAAA を検査）、リダイレクト時の事前検証用ハンドラを実装。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - 受信ヘッダ Content-Length の事前チェックと、超過した場合のスキップ。
  - URL 正規化とトラッキングパラメータ除去（utm_* 等）、SHA-256 (先頭32文字) による記事ID生成で冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - RSS パースのフォールバック（名前空間や非標準レイアウトへの対応）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を使い、実際に挿入された記事IDのリストを返却。チャンク挿入 + トランザクションで実装。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク単位でトランザクション保存（ON CONFLICT DO NOTHING + RETURNING）。
  - 銘柄コード抽出ロジック（4桁数字）と既知銘柄フィルタリング（extract_stock_codes）。
  - デフォルトRSSソースを定義（例: Yahoo Finance ビジネスカテゴリ）。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層のテーブル定義を追加:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 運用のためのインデックス定義を追加（頻出クエリ向け）。
  - init_schema(db_path) を実装: 親ディレクトリを自動作成し、全テーブル・インデックスを作成して DuckDB 接続を返す（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の骨格を実装:
    - ETLResult dataclass（品質問題・エラー・各種取得/保存カウントを保持）。
    - 差分更新用ヘルパー: get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - 市場カレンダーを考慮した trading-day 調整関数 _adjust_to_trading_day。
    - run_prices_etl の骨組みを実装（差分算出、バックフィル日数の扱い、J-Quants fetch/save 呼び出し）。デフォルト backfill_days=3、最低データ日付 _MIN_DATA_DATE = 2017-01-01 を使用。
  - 品質チェックの設計を統合（quality モジュールと連携する想定）。品質チェックは重大度を持ち、呼び出し元が判断する方式（Fail-Fast ではない）。

### セキュリティ
- XML パーシングに defusedxml を採用し XML ボム等を防止。
- RSS フェッチで SSRF 対策を多層的に実施（スキーム検証、ホストのプライベート判定、リダイレクト時検証）。
- レスポンスサイズ制限と Gzip 解凍後の上限検査（メモリ DoS 対策）。

### 変更（設計上・挙動）
- 環境変数ロードの仕様を定義（OS 環境変数は保護され .env の値で上書きされない / .env.local は上書き可）。
- J-Quants クライアントは内部トークンキャッシュを持ち、ページネーション処理間でトークンを共有することで API 呼び出し効率を高める。
- DuckDB の init_schema は :memory: をサポートし、ローカルファイル使用時は親ディレクトリを自動作成。

### 既知の制約・未実装（今後の作業想定）
- strategy と execution パッケージは現時点でモジュールの雛形のみ（実運用向け戦略や発注ロジックは未実装）。
- pipeline.run_prices_etl 以降の ETL ジョブ（財務・カレンダー・品質チェックの統合フロー等）の完全な上位実装は継続実装予定。
- 一部 API ドキュメントや例外ハンドリングの細かなエッジケース検証を今後強化する予定。

### 破壊的変更
- 初回リリースのため該当なし。

### 脆弱性対応履歴
- 初期版で defusedxml と複数の SSRF / DoS 対策を導入（上記参照）。

---

（補足）
この CHANGELOG はコード内コメント、定数、関数名・挙動から推測して作成しています。実際のリリース日、リリースノートの正式文言や追加の変更点がある場合は、本ファイルを更新してください。