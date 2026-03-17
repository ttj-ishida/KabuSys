# Changelog

すべての注目すべき変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

なお、この CHANGELOG は与えられたコードベースから推測して作成したものであり、実際のコミット履歴ではありません。

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買システム「KabuSys」のコアモジュールを追加しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開対象モジュールを __all__ に定義（data, strategy, execution, monitoring）。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を起点に探索）。
  - .env と .env.local の自動読み込み機構を実装（OS 環境変数を保護しつつ .env.local は上書き可能）。
  - .env 行パーサー（コメント、export 形式、クォートとエスケープ対応）を実装。
  - 自動ロードを無効にするための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 必須環境変数チェック（_require）と、環境値検証（KABUSYS_ENV, LOG_LEVEL）を実装。
  - Settings で以下のプロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - env / log_level / is_live / is_paper / is_dev

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants から株価日足、財務データ（四半期 BS/PL）、マーケットカレンダーを取得するクライアントを追加。
  - レート制限遵守のための固定間隔スロットリング実装（120 req/min）。
  - リトライ機構（指数バックオフ、最大3回、408/429/5xx を再試行対象）。
  - 401 受信時はリフレッシュトークンで自動再取得して1回リトライ。
  - ページネーション対応（pagination_key の利用）。モジュールレベルのトークンキャッシュを共有。
  - データ取得関数:
    - fetch_daily_quotes
    - fetch_financial_statements
    - fetch_market_calendar
  - DuckDB へ冪等保存する save_* 関数を追加（ON CONFLICT DO UPDATE を利用）:
    - save_daily_quotes: raw_prices への保存、fetched_at の記録
    - save_financial_statements: raw_financials への保存
    - save_market_calendar: market_calendar への保存（holidayDivision を解釈して is_trading_day/is_half_day/is_sq_day を格納）
  - 値変換ユーティリティ (_to_float, _to_int) を実装（不正値は None）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集し raw_news テーブルへ保存する処理を実装。
  - セキュリティ・堅牢性対策を多数導入:
    - defusedxml を使用して XML Bomb 等を防止
    - SSRF 防止: URL スキーム検証（http/https のみ）、ホストがプライベートアドレスでないことをチェック、リダイレクト時も検査
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の検査（Gzip bomb 対策）
    - User-Agent と Accept-Encoding の指定
  - 記事ID は URL を正規化して SHA-256（先頭32文字）で生成し冪等性を保証（utm_* 等のトラッキングパラメータを除去）。
  - fetch_rss によるフェッチ処理。XML パース失敗時は警告ログを出力して空リストを返却。
  - DB 保存機能:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDのみを返す（チャンク・トランザクション化）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けをバルク挿入（ON CONFLICT DO NOTHING、RETURNING を利用）。
  - 銘柄抽出機能:
    - extract_stock_codes: テキストから4桁数字の銘柄コードを抽出し、既知コードセットでフィルタリング。
  - run_news_collection: 複数 RSS ソースの統合収集ジョブを実装（各ソースは独立してエラーハンドリング、既知コードが渡されれば自動で銘柄紐付けを実行）。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層のテーブル定義を追加（DataSchema.md に準拠した設計）。
  - テーブルは冪等的に作成（CREATE TABLE IF NOT EXISTS）。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 頻出クエリのためのインデックスを追加（idx_*）。
  - init_schema(db_path) でディレクトリ自動作成と全DDL適用を実装。
  - get_connection(db_path) で既存 DB への接続を取得するユーティリティを提供。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新・バックフィル・品質チェックを想定した ETL レイヤを追加。
  - ETLResult データクラスを追加（取得数・保存数・品質問題・エラー等を記録）。
  - テーブル存在チェック、最大日付取得ユーティリティを追加。
  - 市場カレンダーに基づく取引日の調整ヘルパーを実装（_adjust_to_trading_day）。
  - 差分更新用ユーティリティ:
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
  - run_prices_etl: 株価差分 ETL の骨格を実装（差分算出、バックフィル考慮、jquants_client 経由で取得・保存）。  

### 変更 (Changed)
- 設定読み込みの優先順位を明確化:
  - OS 環境変数 > .env.local > .env
  - .env.local は override=True によって既存 OS 環境変数を上書きしないが、.env と比較して優先される。

### 修正 (Fixed)
- （初期リリースのため、過去のバグ修正履歴はありません）

### セキュリティ (Security)
- XML パーシングに defusedxml を採用して外部からの XML ベース攻撃を軽減。
- RSS フェッチ周りで SSRF 対策を多数実施（スキーム検証、プライベート IP の検査、リダイレクト時の検査）。
- ネットワーク読み込みにサイズ上限を設定してメモリ DoS を防止。

### 既知の問題 (Known Issues)
- run_prices_etl の戻り値に不整合の可能性:
  - 現在の実装は run_prices_etl の末尾が "return len(records)," のように見え、(len(records),) の単一要素タプルを返す/または保存件数を返していないように見えます。呼び出し側では (fetched, saved) のような 2 要素タプルを期待する設計のため、実装の続き（saved を含めた適切な戻り値）を追加する必要があります。
- pipeline モジュールは ETL の骨格を提供しているが、品質チェック（quality モジュール）や一部の細かなエラーハンドリングは呼び出し側・別モジュールの実装に依存しているため、統合テスト・運用検証が必要です。

### マイグレーション / 注意事項
- 初回実行時は schema.init_schema(settings.duckdb_path) を呼び出して DuckDB スキーマを作成してください（既に存在する場合はスキップされます）。
- .env の自動読み込みはデフォルトで有効です。テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化できます。
- J-Quants API の利用には JQUANTS_REFRESH_TOKEN の設定が必須です。Settings.jquants_refresh_token を通じて取得されます。
- NewsCollector の RSS フェッチは外部ネットワークに依存するため、プロキシやネットワーク制限下での動作確認を行ってください。

---

このリリースはコードベースから推測して作成した CHANGELOG です。実際のコミットメッセージや追加リソースが存在する場合は、そちらに基づいて内容を更新してください。