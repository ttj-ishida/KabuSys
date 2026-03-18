# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のリリース方針:
- 0.y.z: 初期公開リリース / 基本機能の提供

※ 日付はリリース日を示します。

## [Unreleased]

## [0.1.0] - 2026-03-18
初回公開リリース。日本株自動売買プラットフォームのコア機能を提供します。

### Added
- パッケージのエントリポイントを追加
  - kabusys.__init__ にバージョン情報と公開サブパッケージ一覧を定義（__version__ = "0.1.0"）。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動ロード（OS 環境変数を保護、読み込み順序: OS > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パース処理の実装（コメント、export プレフィックス、クォート内エスケープ、インラインコメント処理などに対応）。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / データベースパス等の設定をプロパティ経由で提供。
  - 必須設定の検査（_require）と env/log level の値検証（有効な環境: development/paper_trading/live、ログレベル検証）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API ベース機能を実装:
    - レート制限 (120 req/min) を守る固定間隔スロットリング (_RateLimiter)。
    - リトライ機構（指数バックオフ、最大リトライ回数 3 回、408/429/5xx を考慮）。
    - 401 発生時の自動トークンリフレッシュ（1 回まで）とモジュールレベルのトークンキャッシュ。
    - JSON レスポンスのデコード検証。
  - 認証ヘルパー get_id_token を実装（refresh token → id token）。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
    - 取得時に fetched_at を付与し look-ahead bias を抑制する運用を想定。
  - DuckDB への保存関数（冪等性）:
    - save_daily_quotes（raw_prices テーブルへ、ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials テーブルへ、ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar テーブルへ、ON CONFLICT DO UPDATE）
  - ユーティリティ: 安全な型変換関数 _to_float / _to_int（不正値を None に変換）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集と保存ワークフローを実装:
    - fetch_rss: RSS 取得、XML パース、記事抽出（title, description/content:encoded, link/guid, pubDate）。
    - preprocess_text による URL 除去・空白正規化。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - save_raw_news: DuckDB へのバルク挿入（チャンク分割、トランザクション、INSERT ... RETURNING を使用して実際に挿入された ID を返す）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルクで保存（ON CONFLICT DO NOTHING、トランザクション、INSERT ... RETURNING）。
    - extract_stock_codes: テキスト中の 4 桁数字から known_codes に基づき銘柄コードを抽出（重複除去）。
    - run_news_collection: 複数 RSS ソースの統合収集ジョブ（ソースごとに独立したエラーハンドリング、既知銘柄紐付けを一括処理）。
  - セキュリティ・堅牢化:
    - defusedxml を用いた XML パース（XML Bomb 防止）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス検出、リダイレクト時の事前検証ハンドラ (_SSRFBlockRedirectHandler)。
    - レスポンスサイズ上限を導入（MAX_RESPONSE_BYTES = 10 MB、gzip 解凍後もチェック）。
    - トラッキングパラメータ除去（utm_ 等）による URL 正規化。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層にまたがるテーブル定義を網羅的に追加:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約、チェック制約（価格 >= 0 / size > 0 等）、主キーや外部キーを定義。
  - インデックス定義（頻出クエリパターンに基づくインデックス）。
  - init_schema(db_path) による初期化（親ディレクトリ自動作成、冪等的 DDL 実行）と get_connection。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラス（処理結果、品質問題、エラーリスト、ユーティリティメソッド to_dict）を追加。
  - 差分更新ユーティリティ:
    - テーブル存在チェック、最大日付取得ヘルパー (_table_exists, _get_max_date)。
    - 市場カレンダーを参照した営業日調整 (_adjust_to_trading_day)。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date。
  - run_prices_etl の部分実装:
    - 差分更新ロジック（最終取得日の backfill を扱う）、J-Quants からの取得と保存の呼び出し。
    - デフォルトのバックフィル日数（3 日）とデータ開始日 (_MIN_DATA_DATE = 2017-01-01）。
  - 品質チェックの設計方針に対応する構成（quality モジュールとの連携を想定）。

### Security
- RSS 処理における SSRF 緩和策を導入:
  - URL スキーム検証、DNS 解決によるプライベート/ループバックアドレス検出、リダイレクト時の検査。
  - defusedxml による安全な XML パース。
  - レスポンス読み取りサイズの上限を導入（メモリ DoS / Gzip bomb 対策）。
- J-Quants クライアントでの認証トークン自動更新ロジックは allow_refresh フラグにより無限再帰を回避。

### Notes
- 自動環境変数ロードはプロジェクトルートの検出（.git または pyproject.toml）に依存しており、配布環境での動作を意識して設計されています。CLI/テストで自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB スキーマは init_schema() を用いて初期化してください。get_connection() は既存 DB へ接続するためのユーティリティで、初回作成は行いません。
- news_collector の extract_stock_codes は known_codes を引数として受け取り、未知銘柄は除外します。収集時の紐付け精度向上のために known_codes を適切に供給してください。
- ETL の品質チェックモジュール (kabusys.data.quality) の実装や更なる ETL ジョブ（財務・カレンダー等の run_*_etl）は本リリースで一部のみ実装/設計されており、今後拡張予定です。

### Breaking Changes
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

---

今後の計画（例）
- ETL の完全実装（財務・カレンダーの差分 ETL、品質チェックルールの実装とレポート化）
- strategy / execution / monitoring パッケージの実装（実稼働・ペーパー用の注文処理、監視通知）
- 単体テスト・統合テストの整備、CI ワークフローとモック可能な HTTP 層の拡張
- J-Quants API のページネーション・大規模データ取得に対するパフォーマンス改善

（リリースノートはコードベースの内容から推測して作成しています。実際の変更履歴や日付はプロジェクト管理情報に従って調整してください。）