CHANGELOG
=========
このファイルは Keep a Changelog の形式に準拠します。  
バージョニングは SemVer に従います。

[Unreleased]
-------------

- 特になし。

[0.1.0] - 2026-03-17
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの初期実装を追加。
  - パッケージ公開情報
    - バージョン: 0.1.0
    - パッケージルートでエクスポートされるモジュール: data, strategy, execution, monitoring

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を起点に探索）。
  - .env パーサーの実装:
    - 空行／コメント行の扱い、export プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理をサポート。
  - .env の読み込み順序と上書きルール:
    - OS 環境 > .env.local > .env（.env.local は上書き許可）。
    - OS 環境変数を保護する protected セットを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト向け）。
  - Settings クラスを実装。主要プロパティ（必須チェック・デフォルト値・バリデーション）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（Path 型で展開）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev の補助プロパティ

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出し基盤を実装:
    - レートリミッタ (_RateLimiter): 固定間隔スロットリングで 120 req/min を遵守。
    - リトライロジック: 指数バックオフ、最大試行回数、408/429/5xx の再試行、429 の Retry-After 優先処理。
    - トークン管理: get_id_token、モジュールレベルの ID トークンキャッシュ、自動リフレッシュ（401 を検知して1回のみ再取得）を実装。
    - JSON デコード例外の扱い・タイムアウトの指定。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes（OHLCV）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
    - 各関数は fetched レコード数のログ出力を行う。
  - DuckDB への保存関数（冪等性確保）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE による上書きと重複排除
    - PK 欠損行のスキップ・警告ログ
  - ユーティリティ変換関数:
    - _to_float / _to_int（空値や不正フォーマットの耐性、"1.0" のようなケース処理）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集の実装（既定のソース: Yahoo Finance ビジネスカテゴリ）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベートアドレス判定、リダイレクトハンドラでの事前検査。
    - レスポンス最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック。
    - 不正なスキーム／サイズ超過時は安全にスキップ。
  - テキスト前処理・URL 正規化:
    - トラッキングパラメータ（utm_*, fbclid 等）の除去、クエリソート、フラグメント削除。
    - 記事ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成（冪等性）。
    - preprocess_text（URL 除去、空白正規化）。
  - DB 保存の実装:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDのみを返却。トランザクションでまとめて実行。
    - save_news_symbols / _save_news_symbols_bulk: (news_id, code) ペアをチャンク化・トランザクションで挿入し、実際に挿入された件数を返す。
  - 銘柄コード抽出:
    - 4桁数字パターンを検出し、与えられた known_codes セットでフィルタして重複除去。
  - 統合収集ジョブ run_news_collection を実装:
    - 各ソース独立にエラーハンドリングし、取得成功分のみ保存・紐付けを行う。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataPlatform の三層（Raw / Processed / Feature / Execution）に基づくテーブル DDL を定義。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリ向け）を追加。
  - init_schema(db_path): ディレクトリ自動作成、全テーブル・インデックスを冪等的に作成して DuckDB 接続を返却。
  - get_connection(db_path): 既存 DB へ接続するヘルパ。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult データクラス: ETL 実行結果、品質問題、エラーの集約と辞書化メソッド。
  - テーブル存在チェック、最大日付取得ユーティリティ (_table_exists, _get_max_date)。
  - 市場カレンダー補助: _adjust_to_trading_day（非営業日の補正）。
  - 差分更新ヘルパ: get_last_price_date / get_last_financial_date / get_last_calendar_date。
  - run_prices_etl: 差分取得ロジック（最終取得日からの backfill を考慮）、jquants_client を用いた fetch と保存の呼び出し。取得範囲の自動計算などをサポート。

Security
- 複数箇所でセキュリティ考慮を導入:
  - RSS: defusedxml、SSRF 防御、レスポンス上限、gzip 解凍上限
  - HTTP リトライ・タイムアウトとトークンリフレッシュにより認証・可用性に配慮
  - .env 読み込み時の保護（OS 環境を上書きしない仕組み）

Performance & Reliability
- API レート制御（固定間隔）と指数バックオフによる安定したリクエスト実行
- トークンキャッシュでページネーション間のオーバーヘッドを削減
- DB 操作はチャンク化・トランザクションで実行し、INSERT ... RETURNING により実際の影響件数を正確に把握
- スキーマに対するインデックス作成で読み取りパフォーマンスを向上

Documentation
- 各モジュールに設計思想や処理フロー、使用例を含む docstring を多数追加（自動生成ドキュメントの下地）。

Breaking Changes
- 初回リリースのため該当なし。

Known limitations / Notes
- strategy, execution, monitoring モジュールはパッケージインターフェースに含まれているが、このリリースでは具体的な戦略ロジックや発注フローの実装は最小限または別途の実装を想定。
- run_prices_etl の実装は差分ロジックを含むが、品質チェックモジュール（kabusys.data.quality）の実行結果ハンドリングや追加の ETL ジョブ（財務・カレンダーの完全なワークフロー）は継続的に拡張予定。
- 将来的に API 仕様変更や J-Quants のレート制限変更に合わせてレート制御やリトライ挙動を調整する必要あり。

Authors and acknowledgements
- 初回実装（設計/実装ドキュメント化を含む）。

----- End of CHANGELOG -----