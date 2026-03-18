# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、リポジトリ内の現状のコードから実装内容・設計意図を推測して作成しています。

全般的な注意
- バージョンはパッケージ定義 (src/kabusys/__init__.py の __version__) に合わせて 0.1.0 を作成しています。
- 実装上の設計方針（冪等性、セキュリティ対策、ログ・ロギング、トランザクションまとめ等）についてコード注釈を基に要約しています。
- 「既知の問題」や「今後の予定」はコードから明確に読み取れる箇所を列挙しています。

Unreleased
- 予定／検討中
  - run_prices_etl の戻り値の扱い修正（現状の実装では tuple の返却が不完全に見える箇所があるため、(fetched, saved) を確実に返すよう修正予定）。
  - 単体テスト拡充（ネットワーク周り、SSRF/リダイレクトハンドリング、.env パーサ、DuckDB トランザクション周りのモックを追加）。
  - jquants_client のレート制御・リトライ周りの統計・メトリクス（呼び出し数・待ち時間等）を追加予定。

[0.1.0] - 2026-03-18
Added
- パッケージ基盤
  - kabusys パッケージの初期化（src/kabusys/__init__.py）を追加。__version__ = "0.1.0"、公開サブパッケージの __all__ を定義。
- 環境設定
  - 環境変数／.env 読み込みユーティリティを実装（src/kabusys/config.py）。
    - プロジェクトルート判定を .git / pyproject.toml で行い、CWD に依存しない自動ロードを実装。
    - .env ファイルパーサはコメント／export プレフィックス／クォートされた値（エスケープ対応）を正しく処理。
    - .env の読み込み優先順位は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - 環境設定をラップする Settings クラスを提供（必須変数チェック、デフォルト値、値検証: KABUSYS_ENV / LOG_LEVEL）。
- データ取得クライアント（J-Quants）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - レート制限（120 req/min）に基づく固定間隔スロットリング RateLimiter。
    - HTTP リクエストラッパー _request は指数バックオフリトライ（最大 3 回）、408/429/5xx に対する再試行を実装。
    - 401 Unauthorized 受信時にリフレッシュトークンで id_token を自動更新して 1 回リトライする仕組みを実装。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
    - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE）を実装（raw_prices, raw_financials, market_calendar）。
    - 値変換ユーティリティ _to_float / _to_int で不正値や空値に対する堅牢な扱いを実現。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead bias を抑止する設計。
- ニュース収集（RSS）
  - RSS 収集・前処理・DB 保存モジュールを実装（src/kabusys/data/news_collector.py）。
    - RSS フィード取得 fetch_rss：defusedxml を利用した安全な XML パース、gzip 解凍対応、最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）、Content-Length 検証、XML パース失敗時の安全なフォールバック。
    - SSRF 対策：URL スキーム検証、ホストがプライベート/ループバック/リンクローカルでないことを確認、リダイレクト時に検証するカスタム HTTPRedirectHandler。
    - URL 正規化（utm_* 等トラッキングパラメータ除去、クエリソート、フラグメント除去）、正規化 URL からの記事ID生成（SHA-256 の先頭32文字）。
    - テキスト前処理（URL 除去、空白正規化）。
    - DuckDB への保存はトランザクションでまとめてチャンク INSERT、INSERT ... RETURNING により実際に挿入された ID/件数を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
    - 銘柄コード抽出ユーティリティ（4桁数字、既知コードに基づくフィルタ）および run_news_collection（複数ソースの収集・個別エラーハンドリング・新規記事の銘柄紐付け）。
- データベーススキーマ
  - DuckDB 用スキーマ定義モジュール（src/kabusys/data/schema.py）を追加。
    - Raw / Processed / Feature / Execution レイヤに対応したテーブル DDL を用意（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
    - 適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）とインデックスを定義。
    - init_schema(db_path) によりディレクトリ作成 → DuckDB 接続 → 全 DDL / インデックスを実行する初期化処理を提供。get_connection() で既存 DB に接続可能。
- ETL パイプライン基盤
  - ETL 関連ユーティリティ（src/kabusys/data/pipeline.py）を実装。
    - ETLResult dataclass：ETL の結果、品質問題、エラー等を構造化して格納・辞書化できる。
    - テーブル存在確認 / 最大日付取得のヘルパー（_table_exists, _get_max_date）。
    - 市場カレンダーに基づく trading day 調整ヘルパー（_adjust_to_trading_day）。
    - 差分更新ロジックのサポート関数（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - run_prices_etl の骨格実装：差分算出（最終取得日から backfill を考慮）、fetch_daily_quotes の呼び出し、save_daily_quotes による保存。backfill_days のデフォルトは 3 日、最小取得開始日は 2017-01-01。
- 型注釈・ドキュメント
  - 各モジュールに型ヒント（Typing）、詳細な docstring（設計原則・注意点）を多数追加。ログ出力ポイントが適切に設置されている。

Security
- defusedxml を用いた XML パース（XML Bomb や外部エンティティ攻撃に対する安全対策）。
- RSS フェッチ時の SSRF 対策（スキーム検証、プライベート IP / ホスト検査、リダイレクト検査）。
- .env の読み込みでは OS の既存環境変数を保護する protected 機構を実装。

Changed
- （初期実装のため該当なし）

Fixed
- （初回リリース。過去の修正履歴は今回のリリースにまとめられている想定）

Known issues / Notes
- run_prices_etl の戻り値
  - run_prices_etl の末尾が "return len(records)," で終わっており、保存件数 saved を返す意図がある場合に不完全に見える箇所があります。現状のコードでは呼び出し側で期待される (fetched_count, saved_count) の形式になっていない可能性があるため、修正予定です（Unreleased に記載）。
- テストカバレッジ
  - ネットワーク呼び出し、外部 API、リダイレクト/ホスト解決等の振る舞いはモック化しての単体テストが必要です。特に SSRF 判定、gzip 解凍サイズチェック、Retry ロジックについての検証が重要です。
- 運用上の注意
  - jquants_client が使うデフォルトのレート制限は 120 req/min に基づいているため、大量のバルク取得や並列処理を行う場合はさらに上位でのスロットリングやキュー化が必要になる場合があります。
  - .env 自動ロードはプロジェクトルートの検出に依存するため、パッケージ配布後や特殊な配置では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動ロードに切り替える必要があります。

参考: 主要な設計方針（コード内コメントより抜粋）
- 冪等性: DuckDB への INSERT は ON CONFLICT DO UPDATE / DO NOTHING を多用して再実行可能性を確保。
- セキュリティ: RSS の XML パースや URL の扱いには安全対策を優先。
- 信頼性: API 呼び出しはレート制御・リトライ・トークン自動更新・ページネーション対応を備える。
- 運用: 取得時刻（fetched_at）や ETLResult による監査可能性を確保。

もし詳細（各関数の変更差分、コミット粒度の履歴、リリース日付の調整など）を実際のコミット履歴ベースで作成したい場合は、Git のコミットログを提供してください。今回の CHANGELOG は現状ソースコードから推測して作成した要約です。