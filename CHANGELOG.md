# Changelog

すべての重要な変更をここに記録します。フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-03-17

初回公開リリース（ベース機能の実装）。

### 追加
- パッケージ基盤
  - kabusys パッケージの初期化（__version__ = 0.1.0、公開モジュール一覧 __all__ を定義）。
  - 空のサブパッケージ雛形を追加: execution, strategy, monitoring（今後の拡張ポイント）。

- 設定・環境変数管理 (kabusys.config)
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を探索してルートを特定）。
  - .env ファイルのパース実装（export プレフィックス、シングル/ダブルクォート対応、インラインコメント処理）。
  - .env の読み込み順序と優先度を実装（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - 読み込み時の既存 OS 環境変数保護（protected set）を実装。
  - Settings クラスを公開し、必要な設定値をプロパティで取得（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）。
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL の有効値チェック）と利便性プロパティ（is_live/is_paper/is_dev）。

- J-Quants クライアント (kabusys.data.jquants_client)
  - API クライアント実装（ベース URL、認証、各種エンドポイント呼び出し）。
  - レート制御実装: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter。
  - リトライロジック: 指数バックオフ（最大 3 回）、408/429/5xx を対象。429 の Retry-After ヘッダ優先処理。
  - 401 発生時の ID トークン自動リフレッシュ（1 回のみ）とトークンキャッシュ共有（ページネーション間で使用）。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes（OHLCV、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - fetched_at に UTC ISO (Z) を記録し、Look-ahead bias を防止。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、入力の不正値に対して安全に None を返す。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集の完全実装（デフォルトソースに Yahoo Finance を追加）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等への防御）。
    - URL スキーム検証（http/https のみ許可）とプライベートアドレス検査（SSRF 対策）。
    - リダイレクト時にスキームとホストを事前検証するカスタムハンドラを実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_ 等を削除）。
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）。
  - RSS 取得とパース（fetch_rss）を実装し、記事一覧を NewsArticle 型で返却。
  - DuckDB への保存機能:
    - save_raw_news: チャンク分割・トランザクションで INSERT ... ON CONFLICT DO NOTHING RETURNING id により実際に挿入された ID を返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンクで挿入、INSERT RETURNING により新規挿入数を返す。
  - 銘柄コード抽出ユーティリティ（4桁数字パターンと known_codes に基づくフィルタリング）。
  - run_news_collection: 複数ソースのループ処理、個別ソースのエラーハンドリング、新規記事に対する銘柄紐付け処理の一括化。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataSchema.md に基づくスキーマ（Raw / Processed / Feature / Execution 層）の DDL 定義を実装。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, orders, trades, positions, portfolio_targets, portfolio_performance
  - 主なインデックスを定義（銘柄×日付や status 検索などに対応）。
  - init_schema(db_path) を実装: DB ファイル親ディレクトリの自動作成、DDL 実行（冪等）、接続返却。
  - get_connection(db_path): 既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult dataclass を実装（取得数、保存数、品質問題、エラー一覧などを保持）。
  - テーブル存在チェック、最大日付取得のユーティリティを実装（_table_exists, _get_max_date）。
  - 市場カレンダーに基づく営業日調整ヘルパー (_adjust_to_trading_day) を実装。
  - 差分更新に関するユーティリティ（最終取得日の取得関数: get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - run_prices_etl を実装（差分取得ロジック、バックフィル days による再取得、J-Quants クライアント経由の取得と保存の呼び出し）。品質チェックモジュール呼び出し箇所の設計を想定。

### セキュリティ
- RSS/HTTP 周りや XML パースに関して複数のセキュリティ対策を追加:
  - defusedxml の採用により XML ベース攻撃を防止。
  - SSRF 対策: URL スキームの制限（http/https のみ）、ホストがプライベートアドレスでないことの検査、リダイレクト先の検査。
  - レスポンス長の上限チェック、gzip 解凍後の再チェックによりメモリ DoS / Gzip bomb に対処。
  - .env の読み込み時に OS 環境変数を保護する仕組みを追加。

### 変更
- なし（初回リリース）。

### 既知の制限 / TODO
- strategy, execution, monitoring サブパッケージは雛形のみ（機能実装は今後）。
- pipeline.run_prices_etl の続き（品質チェック結果の反映やその他 ETL ジョブの統合）は今後の実装が想定される（現状は差分取得→保存の主要ロジックが実装済み）。
- テスト用フックは一部（例: news_collector._urlopen のモック可能化など）を用意しているが、ユニットテストは別途追加予定。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして配布する際は、差分の確定／追加情報（実際のリリース日、既知のバグ修正の詳細、互換性の注意点など）を反映してください。