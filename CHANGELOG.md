# CHANGELOG

すべての重要な変更点を保持するために Keep a Changelog の形式に準拠しています。  
初期リリースに相当する内容をコードベースから推測して記載しています。

全般的な注意:
- 本リリースはパッケージバージョン 0.1.0（src/kabusys/__init__.py の __version__）に対応します。
- 日付: 2026-03-17（推定リリース日）

## [0.1.0] - 2026-03-17

Added
- パッケージ初期構成
  - kabusys パッケージの基本モジュールを追加（data, strategy, execution, monitoring を __all__ に公開）。
- 環境設定管理
  - .env ファイルおよび環境変数から設定を読み込む settings オブジェクトを追加（kabusys.config.Settings）。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml により探索して .env/.env.local を自動読み込み。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env 読み込み時の上書き制御（override, protected）と読み込み失敗時の警告出力を実装。
  - .env 行パーサーは export プレフィックス、クォート内のエスケープ、インラインコメント（クォートなし）を考慮。
  - 必須環境変数取得時に未設定だと ValueError を送出する _require() を提供。
  - 主要な設定項目（例）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（省略時デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパーも提供

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する API クライアントを実装。
  - レート制限対応:
    - 固定間隔スロットリングによる 120 req/min 制御（_RateLimiter）。
  - 再試行・回復ロジック:
    - ネットワーク／HTTP エラーに対する指数バックオフによる最大 3 回のリトライ。
    - HTTP 401 受信時は自動的にリフレッシュトークンで id_token を更新して 1 回リトライ（無限再帰防止）。
    - 429 の場合は Retry-After ヘッダを優先して待機。
  - 認証:
    - refresh token から id_token を取得する get_id_token() を提供。
    - モジュールレベルで id_token をキャッシュし（ページネーション間で共有）、必要時に更新。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes, fetch_financial_statements（pagination_key の追跡）
    - fetch_market_calendar
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
    - 保存時に fetched_at を UTC ISO 秒精度で記録
  - 型変換ユーティリティ:
    - _to_float, _to_int：空値や不正値を適切に None に変換（例: "1.0" は整数変換対応、"1.9" のような小数は int 変換を拒否）

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからニュース記事を安全に収集する実装を追加。
  - セキュリティ/堅牢性設計:
    - defusedxml を用いた XML パースで XML Bomb 等を防御。
    - SSRF 対策: リダイレクト時にスキームとホスト/IP を検証するカスタム HTTPRedirectHandler を導入（内部アドレスや非 http/https スキームを拒否）。
    - 初回および最終 URL に対するプライベート IP チェック（_is_private_host）。
    - 最大応答ボディサイズ制限（MAX_RESPONSE_BYTES = 10 MiB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - URL スキーム検証（http/https のみ許可）。
  - データ整形／識別子:
    - URL 正規化（小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）を行う _normalize_url。
    - 記事 ID は正規化 URL の SHA-256 の先頭32文字（_make_article_id）。
    - 本文前処理（URL除去・空白正規化）を行う preprocess_text。
    - pubDate パース（RFC 2822 対応）で UTC に正規化、失敗時には現在時刻でフォールバック。
  - RSS 取得関数 fetch_rss を実装（gzip 対応、XML パース、title/description/content:encoded の優先判定など）。
  - DuckDB への保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用いて新規挿入 ID を返却。チャンク化して 1 トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク単位で安全に挿入し、挿入件数を返却。
  - 銘柄コード抽出:
    - テキストから 4 桁の候補を抽出し、known_codes の集合と照合して重複を除去して返す extract_stock_codes。
  - 統合収集ジョブ run_news_collection:
    - 複数 RSS ソースを独立して処理し、個々のソース失敗を他に影響させない実行設計。
    - 新規挿入記事に対して銘柄紐付けを一括挿入。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataPlatform に基づく 3 層 + 実行レイヤーのテーブル定義を追加（Raw / Processed / Feature / Execution）。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（PRIMARY KEY / FOREIGN KEY / CHECK）を定義。
  - インデックス定義（頻出クエリ向け）。
  - init_schema(db_path) によりディレクトリ自動作成と全テーブル・インデックスの冪等作成を行う（":memory:" 対応）。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ベースの ETL 実装（差分計算、backfill を考慮した再取得）。
  - 市場カレンダー先読み、デフォルト backfill_days = 3 を採用して「後出し修正」を吸収。
  - ETL 出力を表現する ETLResult データクラス（取得数・保存数・品質問題・エラー一覧を保持）。
  - テーブル存在チェック、最大日付取得ユーティリティ、取引日調整ヘルパーなどを提供。
  - run_prices_etl: 差分取得→保存の操作フローを実装（fetch/save を呼び出す）。（注: コード断片では戻り値タプルの最後の要素が未完となっているため、実装の続きがある想定）

Changed
- なし（初期リリースのため過去バージョンとの比較は無し）

Fixed
- なし（初期リリース）

Security
- ニュース収集時の SSRF 対策、defusedxml 使用、レスポンスサイズ制限、gzip 解凍後のサイズ検査等、セキュリティ考慮を充実させた実装を追加。
- RSS URL 正規化とトラッキングパラメータ除去により、ID 再現性と冪等性を確保。

Notes / Migration
- DB 初期化: 初回は必ず init_schema(settings.duckdb_path) を実行してテーブルを作成してください。get_connection は既存 DB のみ接続します。
- 必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定しないと Settings プロパティアクセス時に ValueError が発生します。
- .env の自動読み込みをテスト等で無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants API のレート制限（120 req/min）に準拠しています。大量取得時はレートやリトライ挙動（最大 3 回）を考慮してください。
- ニュース収集の既知銘柄リスト（known_codes）を提供しない場合は銘柄紐付け処理がスキップされます。
- pipeline.run_prices_etl のコードは差分更新ロジックを含むが、ソースコード断片の末尾が未完（戻り値タプルが途中で終わっている）ため、実運用前にその続き（戻り値の完全な組み立て）を確認してください。

開発者向け補足
- テスト容易性のため、news_collector._urlopen や jquants_client の id_token 注入など、内部 API をモック可能に設計しています。
- DuckDB に対する大量 INSERT はチャンク化してトランザクションで実行しており、ON CONFLICT または DO NOTHING を利用して冪等性を担保しています。

--- 

この CHANGELOG はコードベースの内容から推測してまとめたものです。実リリースではコミット履歴やリリースノートに基づいて必要に応じて加筆・修正してください。