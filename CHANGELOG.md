CHANGELOG
=========

すべての注目すべき変更はこのファイルで管理します。  
フォーマットは Keep a Changelog に準拠します。  

現在のバージョン: 0.1.0

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/tag/v0.1.0

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージ公開情報
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
    - __all__ に data, strategy, execution, monitoring を公開モジュールとして列挙。

- 環境設定・読み込み機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機構:
    - プロジェクトルートを .git または pyproject.toml を基準に検出して .env / .env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用フラグ）。
    - OS 環境変数を保護する protected パラメータを用いた上書き制御。
  - .env パーサーの実装:
    - export プレフィックス対応、クォートとバックスラッシュエスケープ処理、インラインコメントの扱いなどを考慮した堅牢なパース。
  - 必須設定取得ヘルパー (_require) と各種 property を提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）。
  - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）を実装。
  - Path を返す DB パスプロパティ（duckdb/sqlite）と環境判定ユーティリティ（is_live/is_paper/is_dev）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しの汎用ユーティリティ _request を実装:
    - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter。
    - 再試行ロジック（指数バックオフ、最大3回）を実装。HTTP 408/429/5xx を対象にリトライ。
    - 429 の Retry-After ヘッダを優先、存在しない場合は指数バックオフを使用。
    - 401 レスポンス時は自動でリフレッシュし1回だけ再試行（無限再帰を回避）。
    - JSON デコードエラー時に詳細を含む例外を送出。
  - get_id_token 関数（refresh_token から idToken を取得）を提供。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（OHLCV 日足）
    - fetch_financial_statements（四半期 BS/PL）
    - fetch_market_calendar（JPX マーケットカレンダー）
    - 取得時に fetched_at を UTC で記録して Look-ahead Bias を追跡可能にする設計方針を反映。
  - DuckDB への保存関数（冪等性を重視）:
    - save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT を用いた UPSERT 実装。
    - PK 欠損行はスキップしログ出力。
    - 型変換ユーティリティ（_to_float, _to_int）を実装して入力の堅牢性を確保。

- RSS ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得と記事抽出処理:
    - fetch_rss: RSS を取得して記事リスト（NewsArticle 型）を返す。
    - preprocess_text による URL 除去・空白正規化。
    - pubDate の解析（UTC に正規化）。パース失敗時は警告ログと現在時刻で代替。
  - セキュリティと堅牢性:
    - defusedxml を用いた XML パースで XML Bomb 等を防御。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームとホストの検査を行う独自リダイレクトハンドラ (_SSRFBlockRedirectHandler)。
      - ホストがプライベート/ループバック/リンクローカルかを判定する _is_private_host（直接 IP 判定と DNS 解決を行う）。
    - レスポンスサイズの制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検査（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding を設定して取得。
  - 記事 ID と正規化:
    - _normalize_url によるトラッキングパラメータ除去（utm_ など）、スキーム/ホストの小文字化、クエリソート、フラグメント削除。
    - _make_article_id は正規化 URL の SHA-256 ハッシュ先頭32文字で記事IDを生成（冪等性確保）。
  - DuckDB 保存関数（冪等・トランザクション処理）:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事 ID を返す。チャンク分割と1トランザクションでの挿入を実施。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの (news_id, code) 紐付けをバルクで挿入。ON CONFLICT と INSERT RETURNING を利用して実際に挿入された件数を正確に返す。
  - 銘柄抽出:
    - extract_stock_codes: テキストから4桁数字を抽出し、known_codes によってフィルタ。重複除去。
  - 統合ジョブ:
    - run_news_collection: 複数 RSS ソースから収集し raw_news に保存、既知銘柄が与えられた場合は銘柄紐付けを実行。各ソースは独立してエラーハンドリング（1ソース失敗でも継続）。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DataPlatform の3層 (Raw / Processed / Feature / Execution) を反映した DDL を実装。
  - 主なテーブル（抜粋）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY / CHECK / FOREIGN KEY）を定義。
  - パフォーマンス向けインデックスを複数定義（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) により DB フォルダの自動作成を行い、全DDLとインデックスを実行して接続を返す。get_connection は既存 DB への接続のみを返す。
  - テーブル作成順は外部キー依存を考慮して管理。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETLResult dataclass を導入して ETL 実行結果（取得数・保存数・品質問題・エラー等）を集約。
  - テーブル存在確認や最大日付取得のユーティリティ (_table_exists, _get_max_date) を実装。
  - 市場カレンダー補正ヘルパー (_adjust_to_trading_day) を実装（非営業日の調整）。
  - 差分更新ロジックとバックフィル対応:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
    - run_prices_etl 実装（差分取得、最終取得日から backfill_days 前から再取得、取得→保存のフロー）。（コード末尾での処理戻り値に関する断片的実装を含む）
  - 品質チェック基盤へのフック（quality モジュールを使用する設計。品質問題は収集を中断せず呼び出し元に報告する方針）。

Security
- defusedxml による XML パース、SSRF 対策、レスポンスサイズ制限、ホスト検査など各所でセキュリティ対策を実施。
- J-Quants クライアントは認証トークンの自動リフレッシュを実装し、無限再帰を防ぐ設計。

Notes / Other
- 多くの処理で「冪等性」を重視（DuckDB への INSERT ... ON CONFLICT / RETURNING の活用、ID のハッシュ化等）。
- ロギングを多用して処理状況・警告を明示（fetch/save の件数ログや例外時の logger.exception）。
- 一部モジュール（strategy、execution、monitoring）はパッケージ構成上にプレースホルダとして存在（将来的な拡張ポイント）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 本リリースに含まれるセキュリティ関連対策は上記「Security」セクションを参照してください。

今後の予定（想定）
- strategy / execution / monitoring モジュールの実装強化（発注ロジック、ポジション管理、監視・通知）。
- quality モジュールの実装と ETL による自動修復オプションの追加。
- テストカバレッジ拡張（ネットワーク/DB 処理のモックを含む）。