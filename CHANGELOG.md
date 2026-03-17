# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog に準拠しています。  

※日付はコードベースから推測して付与しています。

## [0.1.0] - 2026-03-17
初回リリース

### Added
- パッケージ基礎
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - モジュール分割: data, strategy, execution, monitoring を __all__ に公開。

- 設定管理 (kabusys.config)
  - .env ファイルと環境変数からの設定自動読み込み機能を実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）を導入し、CWD に依存しない自動ロードを実現。
  - .env 行パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、コメント処理対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - 必須環境変数取得ヘルパ (_require) と Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などをプロパティ経由で取得。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルトを設定。
    - KABUSYS_ENV と LOG_LEVEL の許容値チェック（検証エラー時は ValueError を投げる）。
    - is_live / is_paper / is_dev のブールプロパティを提供。

- J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API からのデータ取得機能を実装:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - 認証補助: get_id_token（リフレッシュトークンから id_token を取得）。
  - 安全で実運用向けの HTTP/再試行/レート制御:
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
    - 401 の場合はトークン自動リフレッシュを 1 回だけ行い再試行。
    - ページネーション中はモジュールレベルで id_token をキャッシュして共有。
    - pagination_key の再帰ループ防止（既出キー検出で停止）。
  - DuckDB への保存用関数（冪等保存を実現する ON CONFLICT を使用）:
    - save_daily_quotes（raw_prices テーブルへ保存）
    - save_financial_statements（raw_financials テーブルへ保存）
    - save_market_calendar（market_calendar テーブルへ保存）
  - データ変換ユーティリティ:
    - _to_float / _to_int（安全な変換。小数部を持つ数を int に落とす誤動作を防止）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュース記事を取得して DuckDB に保存する機能を実装。
  - 主な機能:
    - fetch_rss: RSS の取得および解析（defusedxml による安全な XML パース）。
    - preprocess_text: URL 除去・空白正規化などの前処理。
    - _normalize_url / _make_article_id: トラッキングパラメータ除去および正規化後の SHA-256（先頭32文字）で記事 ID を生成し冪等性を確保。
    - save_raw_news: INSERT ... RETURNING を用いたチャンク単位の挿入（重複は ON CONFLICT でスキップ）。トランザクションでまとめてコミット/ロールバック。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを効率的に保存（チャンク/トランザクション、RETURNING を利用）。
    - extract_stock_codes: テキスト中の 4 桁銘柄コード抽出（重複除去、known_codes による検証）。
    - run_news_collection: 複数 RSS ソースを巡回し、取得→保存→銘柄紐付けを実行。各ソースは独立してエラーハンドリング（1ソース失敗で残り継続）。
  - セキュリティ・堅牢性対策:
    - SSRF 対策: URL スキーム検証（http/https のみ）、プライベートIP/ループバック/リンクローカル/マルチキャストのブロック、リダイレクト時の事前検査を行うカスタム RedirectHandler を導入。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）および Gzip 解凍後のサイズチェックでメモリ DoS / Gzip bomb を防止。
    - 不正スキームや不正レスポンスはログ出力してスキップ。
    - defusedxml を使用して XML ベースの攻撃（XML Bomb 等）を緩和。
    - HTTP User-Agent と Accept-Encoding を設定し、gzip を処理。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用の完全なスキーマ定義と初期化ユーティリティを追加:
    - Raw / Processed / Feature / Execution 層に対応するテーブル群を定義（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）。
    - 制約（PRIMARY KEY、CHECK、FOREIGN KEY）を多数設定しデータ整合性を担保。
    - 頻出クエリ向けのインデックスを定義（code/date や status 等）。
    - init_schema(db_path) でディレクトリ自動作成や DDL 実行を行い接続を返す。get_connection() で既存 DB に接続。
    - テーブル作成は IF NOT EXISTS による冪等実行。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分 ETL の基盤を実装:
    - ETLResult データクラスで ETL の結果・品質問題・エラーを集約。
    - 差分取得支援: DB 側の最終取得日を調べるヘルパ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダー未取得時のフォールバックや、非営業日の調整を行う _adjust_to_trading_day を実装。
    - run_prices_etl（株価日足差分 ETL）の骨格を実装（差分算出、バックフィル日数サポート、fetch/保存の呼び出し）。backfill_days により最終取得日の数日前から再取得して API の後出し修正を吸収する設計。
    - ETL の品質チェックは別モジュール（quality）に委ね、重大度に基づく判定が可能（pipeline 側は継続的に収集する方針）。

### Security
- ニュース収集での複数のセキュリティ対策を導入:
  - defusedxml を利用した安全な XML パース。
  - URL スキーム検証とプライベートアドレス検査で SSRF を防止。
  - レスポンスサイズ制限・Gzip 解凍後チェックでメモリ攻撃を緩和。
  - .env ファイル読み込み時に OS 環境変数を保護する protected 機構を導入。

### Performance
- J-Quants クライアントでの固定間隔レートリミッタ（120 req/min）により API レート制限を遵守。
- ページネーション中の id_token キャッシュで余分なトークン取得を抑制。
- DuckDB への保存で ON CONFLICT を使った冪等化により差分保存を効率化。
- ニュース保存はチャンク Insert（_INSERT_CHUNK_SIZE）とトランザクションでバルク性能を改善。
- スキーマに頻出クエリ用インデックスを追加。

### Notes / Migration
- 初回利用時は .env.example を参照して必須環境変数（JQUANTS_REFRESH_TOKEN 等）を設定してください。未設定の場合は Settings のプロパティが ValueError を投げます。
- DuckDB 初期化は kabusys.data.schema.init_schema(db_path) を呼び出してください（":memory:" も可）。
- 自動 .env 読み込みを無効にしたいテスト等は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector._urlopen はテストでモック差替え可能な設計になっています。

### Breaking Changes
- 初回リリースのため破壊的変更はありません。

---

今後のリリース推奨:
- pipeline の残りジョブ（財務・カレンダー ETL 完了）、quality モジュール統合、monitoring/strategy/execution モジュールの実装とドキュメント化。
- 単体テスト、統合テストの整備（特にネットワーク・DB 周りのモック）。