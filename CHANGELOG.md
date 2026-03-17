# Changelog

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠します。

## [0.1.0] - 2026-03-17

### 追加 (Added)
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報とエクスポート定義（src/kabusys/__init__.py）。
- 環境設定管理モジュール（src/kabusys/config.py）
  - プロジェクトルートを .git または pyproject.toml で検出して .env/.env.local を自動読み込みする仕組みを実装。
  - .env ファイルの堅牢なパーサ（コメント行、export プレフィックス、クォート／エスケープ、インラインコメント処理に対応）。
  - OS 環境変数の保護（.env.local は override、デフォルトで既存の OS 環境変数は上書きしない）。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスにより、J-Quants / kabu API / Slack / DB パス / 実行環境等の設定取得 API を提供。環境変数検証（KABUSYS_ENV, LOG_LEVEL）を行う。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日次株価（OHLCV）、四半期財務データ、マーケットカレンダーの取得機能（ページネーション対応）。
  - API レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
  - ネットワーク・HTTP エラーに対するリトライ（指数バックオフ、最大 3 回。408/429/5xx を対象）。429 の場合は Retry-After を尊重。
  - 401 受信時はリフレッシュトークンで自動的に id_token を更新して 1 回だけリトライ。
  - モジュールレベルのトークンキャッシュをページネーション間で共有。
  - DuckDB へ保存する関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等性を考慮し ON CONFLICT DO UPDATE を使用。
  - レスポンスの JSON デコード失敗や例外に対する詳細なエラーメッセージ。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得 → 前処理 → raw_news へ冪等保存 → 銘柄紐付け の ETL を実装。
  - セキュリティ対策: defusedxml による XML パース（XML Bomb 等の防御）、SSRF 対策（スキーム検証、ホストがプライベート/ループバックかを検査）、リダイレクト時の検査ハンドラ実装。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検査によるメモリ DoS 対策。
  - URL 正規化（クエリのトラッキングパラメータ除去、ソート、フラグメント削除）と記事ID生成（SHA-256 の先頭32文字）による冪等性保証。
  - テキスト前処理（URL除去・空白正規化）関数と、記事本文から銘柄コード（4桁）を抽出するユーティリティを提供。
  - DuckDB へのバルク挿入はチャンク化してトランザクションで実行。INSERT ... RETURNING を使い実際に挿入された件数/IDを返す。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加。
- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DataPlatform 設計に基づく多層スキーマ（Raw / Processed / Feature / Execution）を定義。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル、prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル、features, ai_scores の Feature テーブル、signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブルを含む。
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックスを作成し、init_schema(db_path) で初期化可能（冪等）。
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新を行う ETL フローの基盤を実装（最終取得日検出、バックフィル、取得→保存→品質チェックの枠組み）。
  - ETLResult データクラスを導入し、取得件数・保存件数・品質問題・エラー情報を集約する API を提供。
  - 市場カレンダー未取得時のフォールバックと、非営業日の調整（_adjust_to_trading_day）。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date 等のユーティリティ。
  - run_prices_etl により差分取得（date_from 自動算出、backfill_days による再取得）と保存を行う仕組みを実装。
- 型ヒントとログ出力を広範に追加し、運用での可観測性を向上。

### セキュリティ (Security)
- ニュース収集に関する SSRF 対策を複数実装:
  - URL スキーム検証（http/https のみ許可）。
  - DNS 解決して得られた IP のプライベート/ループバック/リンクローカル判定。
  - リダイレクト先でもスキーム・ホスト検査を行うカスタム RedirectHandler。
- XML パーサに defusedxml を採用して XML 関連の脆弱性対策。
- レスポンスサイズ上限および gzip 解凍後のサイズ検査でメモリ消費攻撃を軽減。

### 変更 (Changed)
- なし（初回リリース）。

### 修正 (Fixed)
- なし（初回リリース）。

### 既知の問題 (Known issues)
- run_prices_etl の戻り値が本来 (fetched_count, saved_count) のタプルを返す設計である一方、ソーススニペット末尾において return 文が途中で切れているため（return len(records),）実行時にタプルの要素不足や TypeError を引き起こす可能性があります。リリース後の実装確認および修正を推奨します。
- その他、品質チェックモジュール（quality）は参照されているがこのスニペット内に実装がないため、ETL の完全な動作には追加コンポーネントが必要です。

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）。

### マイグレーション / 移行手順
- 初回セットアップ:
  - settings を参照して必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定してください。
  - DuckDB スキーマを初期化するには:
    - from kabusys.data.schema import init_schema
    - conn = init_schema(settings.duckdb_path)
- ニュース収集等で外部 URL にアクセスするため、実行環境のネットワークポリシーが http(s) アクセスを許可していることを確認してください。

---

貢献者: 初期実装チーム（自動生成ドキュメントに基づく推測情報を含む）  

注: 上記は提供されたコードベースから推測して記載した CHANGELOG です。実際のプロジェクト運用上のリリースノートとして使用する前に、動作確認・追加実装（未実装モジュールやテストの有無の確認）を行ってください。