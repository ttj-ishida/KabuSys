CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

0.1.0 - 2026-03-17
------------------

Added
- 初回リリース: KabuSys パッケージの基本実装を追加。
  - パッケージ構成:
    - kabusys (パッケージルート)
      - config: 環境変数/設定管理
      - data: データ取得・保存・ETL 関連
        - jquants_client: J-Quants API クライアント（価格・財務・市場カレンダー取得、DuckDB 保存ユーティリティ）
        - news_collector: RSS ベースのニュース収集・前処理・DuckDB 保存・銘柄紐付け
        - schema: DuckDB スキーマ定義と初期化
        - pipeline: ETL パイプライン（差分取得、バックフィル、品質チェックフック）
      - strategy, execution, monitoring: パッケージプレースホルダ（__all__ に含むが現時点では空モジュール）
  - バージョン: __version__ = "0.1.0"

- 環境設定 (kabusys.config.Settings)
  - .env/.env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml で検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理等をサポート
  - 必須設定の検証を提供（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）
  - デフォルト値:
    - KABU_API_BASE_URL = "http://localhost:18080/kabusapi"
    - DUCKDB_PATH = "data/kabusys.duckdb"
    - SQLITE_PATH = "data/monitoring.db"
    - KABUSYS_ENV の許容値 = {"development","paper_trading","live"}（不正な場合は ValueError）
    - LOG_LEVEL の許容値 = {"DEBUG","INFO","WARNING","ERROR","CRITICAL"}（不正な場合は ValueError）
  - is_live / is_paper / is_dev プロパティを提供

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 取得機能:
    - fetch_daily_quotes: 株価日足（ページネーション対応）
    - fetch_financial_statements: 四半期財務データ（ページネーション対応）
    - fetch_market_calendar: JPX マーケットカレンダー取得
  - 認証:
    - get_id_token: リフレッシュトークンから idToken を取得
    - モジュールレベルで ID トークンをキャッシュしてページネーション間で共有
    - 401 受信時は自動でトークンをリフレッシュし1回だけリトライ
  - レート制御:
    - 固定間隔スロットリングで 120 req/min（_RateLimiter）
  - リトライ:
    - 指数バックオフ（base=2.0秒）、最大リトライ回数 3（408,429,5xx を対象）
    - 429 の場合は Retry-After ヘッダを優先
  - DuckDB 保存ユーティリティ（冪等性）:
    - save_daily_quotes: raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials に冪等保存
    - save_market_calendar: market_calendar に冪等保存
  - データ整形 / 型変換ユーティリティ: _to_float, _to_int（float文字列からの安全なint変換を考慮）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード取得と記事保存ワークフローを実装:
    - fetch_rss: RSS フィード取得、XML パース、記事整形（title/content/url/datetime）
    - save_raw_news: raw_news テーブルへチャンク挿入（INSERT ... ON CONFLICT DO NOTHING RETURNING を用い新規挿入IDを返す）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括で保存（重複排除、チャンク挿入、RETURNING による実挿入数取得）
    - run_news_collection: 複数ソースからの統合収集ジョブ（ソース単位で独立したエラーハンドリング）
  - セキュリティ・堅牢性:
    - defusedxml を利用して XML Bomb などを防止
    - リダイレクト時に _SSRFBlockRedirectHandler でスキーム検証・プライベートIPブロック（SSRF 対策）
    - フェッチ前にホストがプライベートか検証、URL スキームは http/https のみ許可
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検査（Gzip bomb 対策）
    - User-Agent と Accept-Encoding ヘッダの設定
  - 正規化・前処理:
    - _normalize_url でトラッキングパラメータ（utm_ 等）除去、クエリソート、フラグメント除去
    - _make_article_id: 正規化 URL の SHA-256（先頭32文字）を記事IDに使用し冪等性を保証
    - preprocess_text: URL 除去と空白正規化
    - extract_stock_codes: 4桁数字パターンで銘柄コードを抽出し known_codes でフィルタ（重複除去）
  - 実装上のパフォーマンス配慮:
    - バルク INSERT のチャンクサイズ制御（_INSERT_CHUNK_SIZE）
    - DB 操作をトランザクションでまとめてオーバーヘッド削減

- DuckDB スキーマ (kabusys.data.schema)
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義を追加:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY 等）を追加
  - パフォーマンス用インデックスを複数定義（銘柄×日付、ステータス検索等）
  - init_schema(db_path) でディレクトリ自動作成・テーブル作成（冪等）を行い接続を返す
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラスによる実行結果表現（品質問題リスト・エラーメッセージ等を含む）
  - 差分更新ヘルパー:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _get_max_date / _table_exists ユーティリティ
  - 市場カレンダー補助: _adjust_to_trading_day（非営業日を直近営業日に調整）
  - run_prices_etl（差分取得／バックフィル／保存）を実装（backfill_days デフォルト 3、最小データ日付は 2017-01-01）
  - 品質チェックとの統合ポイント（quality モジュールへの依存を想定）

Security
- news_collector における SSRF 対策、XML パース防御、レスポンスサイズ検査、URL 正規化により安全性を意識した実装。
- jquants_client は認証トークンの自動リフレッシュとレート制御、リトライ戦略を実装して API 利用の堅牢性を向上。

Compatibility
- DuckDB を利用（依存ライブラリとして duckdb が必要）。
- defusedxml を利用（XML パースに必須）。
- Python 型ヒント（| 構文など）を使用しているため Python 3.10+ を想定。

Notes / Migration
- 初期化手順:
  - init_schema(settings.duckdb_path) でデータベースとスキーマを初期化してください。
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定してください。
- .env 自動ロードはプロジェクトルート検出に依存します（.git または pyproject.toml）。CI／テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector.run_news_collection に銘柄抽出を行わせる場合、known_codes に有効銘柄コードセットを渡してください。

Acknowledgements / Design
- 複数のモジュールで「冪等性」「Look-ahead Bias 防止」「API レート制御」「トランザクションによる DB 操作の原子性」を設計方針として採用しています。

今後の予定（例）
- strategy / execution / monitoring の具象実装
- quality モジュールによる詳細なデータ品質チェック結果の ETL 統合
- CI / テストの追加（ネットワーク依存部はモック可能な設計を継続）

---
この CHANGELOG はリポジトリ内のコード内容から推測して作成しています。実際のリリースノートとして使用する場合は必要に応じて調整してください。