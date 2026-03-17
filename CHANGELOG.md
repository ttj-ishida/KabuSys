CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。形式は「Keep a Changelog」に準拠しています。

0.1.0 - 2026-03-17
------------------

初回リリース。本リリースで導入された主な機能・設計方針をモジュール別に記載します。

Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージの公開 API は data, strategy, execution, monitoring を想定（__all__ に登録）。

- 環境設定管理（kabusys.config）
  - Settings クラスを導入し、環境変数経由でアプリケーション設定を提供。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を必須項目として取得するプロパティを用意。
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを提供（expanduser を使用）。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証を実装。
    - is_live / is_paper / is_dev のショートカットプロパティを提供。
  - プロジェクトルート（.git または pyproject.toml）を基準とした .env 自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
  - .env パーサを実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理、無効行の無視など。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants API との通信実装（トークン取得、株価日足・財務データ・市場カレンダーの取得）。
  - レート制御: 固定間隔スロットリングで 120 req/min を保証する RateLimiter を実装。
  - 再試行ロジック: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx を対象にリトライ。
    - 429 の場合は Retry-After ヘッダを優先利用。
  - 401 (Unauthorized) 受信時はリフレッシュトークンから id_token を自動更新して 1 回だけリトライ（無限再帰防止）。
  - id_token をモジュールレベルでキャッシュし、ページネーション間で共有。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements 等）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。
    - 保存は冪等（ON CONFLICT DO UPDATE）で重複を排除。
    - fetched_at を UTC（ISO 8601、Z 表記）で記録して Look-ahead Bias を防止。
    - PK 欠損行はスキップし、スキップ数をログ出力。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存する一連の処理を実装。
  - セキュリティ対策:
    - defusedxml を利用して XML Bomb 等を防止。
    - SSRF 対策: リダイレクト先のスキーム検証、ホストがプライベート／ループバック等かを検査。非 http/https スキームを拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - 受信サイズオーバー時に警告して処理をスキップ。
  - URL 正規化機能（_normalize_url）を実装し、utm_ 等のトラッキングパラメータ除去・クエリソート・フラグメント削除を行う。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
  - テキスト前処理（URL 除去、空白正規化）関数 preprocess_text を提供。
  - RSS 解析: content:encoded の名前空間対応や description フォールバック、pubDate の解析（タイムゾーンを UTC に正規化）。
  - DuckDB への保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を使い、実際に挿入された記事ID一覧を返す。チャンク挿入とトランザクションを採用。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING）して挿入数を正確に返す。
  - 銘柄コード抽出機能（extract_stock_codes）:
    - 4桁数字の候補を抽出し、known_codes セットに含まれるもののみ返す。重複除去。

- データスキーマ（kabusys.data.schema）
  - DuckDB の DDL を定義し、Raw / Processed / Feature / Execution 層のテーブルを整備。
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
    - features, ai_scores 等の Feature テーブル。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
  - CHECK 制約や PRIMARY KEY、FOREIGN KEY を適切に定義（データ整合性を設計）。
  - 活用想定に合わせたインデックスを作成（銘柄×日付、ステータス検索など）。
  - init_schema(db_path) を提供し、必要な親ディレクトリの作成、すべての DDL/INDEX を冪等的に実行して接続を返す。
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計方針とユーティリティを実装。
    - 差分更新のための最終取得日取得関数（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダーを用いた取引日に調整する _adjust_to_trading_day。
    - _table_exists / _get_max_date といった DB ヘルパー。
  - ETLResult dataclass を導入し、ETL 実行結果・品質問題・エラー要約を集約。品質問題のサマリを辞書化する to_dict を提供。
  - run_prices_etl を追加（差分 ETL、バックフィル default=3 日、_MIN_DATA_DATE の利用、jq.fetch_daily_quotes → jq.save_daily_quotes を実行）。
  - 設計方針として品質チェックは重大度に応じても ETL を継続し、呼び出し元に判断を委ねる（Fail-Fast しない）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集で複数の SSRF / XML / Gzip 攻撃対策を導入（_SSRFBlockRedirectHandler, defusedxml, レスポンスサイズ検査 等）。
- .env 読み込みはデフォルトで有効だが、テスト用に無効化フラグを提供（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Usage
- データベース初期化:
  - init_schema(settings.duckdb_path) を呼んで DuckDB スキーマを作成してください。":memory:" を指定するとインメモリ DB を使用可能。
- 環境変数:
  - 必須項目（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は Settings のプロパティ経由で取得され、未設定時は ValueError を送出します。.env.example を参考に .env を用意してください。
- API レート制御:
  - J-Quants API は 120 req/min を想定しています。内部で固定間隔スロットリングを実装していますが、長時間の大量取得時は考慮してください。
- ニュース収集:
  - デフォルトの RSS ソースは Yahoo Finance ビジネスカテゴリを含みますが、run_news_collection に sources を渡して上書きできます。
  - 銘柄抽出には known_codes を渡してください（渡さない場合は紐付けをスキップ）。

Compatibility / Migration
- 0.1.0 は初回リリースのため互換性問題はありません。将来のリリースでスキーマや API が変わる可能性があるため、データ保存・スキーマ定義に関してはバージョン間のマイグレーション方針を検討してください。

Acknowledgements / References
- DataPlatform.md / DataSchema.md 等の設計文書に基づく実装を行っています（リポジトリ内に設計資料がある想定）。

TODO（今後の改善候補）
- strategy / execution / monitoring モジュールの実装（現状はパッケージエントリのみ）。
- quality モジュールの詳細実装（pipeline で参照されるが、品質ルールの拡充）。
- 単体テスト・統合テストの追加（外部 API のモック化を含む）。
- ロギング設定の統合（Settings.log_level による起動時設定）。

以上。