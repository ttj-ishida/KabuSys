# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載します。  
このプロジェクトはセマンティックバージョニングを採用します。

次のリリースノートは、リポジトリ内のソースコードから推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買プラットフォームのコアコンポーネント（設定管理、データ取得・保存、ニュース収集、ETLパイプライン、DuckDBスキーマ）が実装されました。

### Added

- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開モジュール一覧を定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - .env パーサを実装（export 形式・クォート・インラインコメントの考慮、エスケープ処理対応）。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）等の設定をプロパティとして取得。
  - 設定値のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェックなど）を追加。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API ベース機能を実装（id_token 取得、ページネーション対応のデータ取得関数）。
  - 取得対象:
    - 株価日足（fetch_daily_quotes）
    - 財務データ（fetch_financial_statements）
    - JPX マーケットカレンダー（fetch_market_calendar）
  - レート制御: 固定間隔スロットリングによるレート制限（120 req/min）を実装（内部 RateLimiter）。
  - リトライロジック: 指数バックオフ、最大試行回数 3 回、408/429/5xx などを対象にリトライ。
  - 401 Unauthorized 発生時のトークン自動リフレッシュ機能（1 回のみリトライ）。
  - データ保存関数（DuckDB 用）を実装し、冪等性を確保:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE で保存
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE で保存
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE で保存
  - データ取り込み時の fetched_at（UTC）記録による取得時刻トレースを実装。
  - 型安全な数値変換ユーティリティ (_to_float / _to_int) を実装。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集・前処理・保存する機能を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先の事前検証、プライベート IP/ループバック/リンクローカルの検出と拒否。
    - レスポンス読み取り上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - 記事ID作成: URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）後に SHA-256（先頭32文字）で生成し冪等性を担保。
  - テキスト前処理: URL 除去、空白正規化。
  - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し、known_codes フィルタで有効銘柄のみを採用（重複除去）。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を用いて新規挿入された記事IDリストを返す（チャンク挿入、トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けを一括挿入（ON CONFLICT DO NOTHING、INSERT ... RETURNING で挿入数を算出）。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataPlatform 設計に基づく 3 層（Raw / Processed / Feature）＋Execution 層のテーブル定義を実装。
  - raw_prices, raw_financials, raw_news, raw_executions など Raw レイヤ
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed レイヤ
  - features, ai_scores など Feature レイヤ
  - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution レイヤ
  - 主キー・制約・CHECK 制約を多数定義し、データ整合性を強化。
  - 頻出クエリを想定したインデックス群を追加（例: idx_prices_daily_code_date）。
  - init_schema(db_path) でディレクトリ自動作成 → テーブル作成を行うユーティリティを提供。
  - get_connection(db_path) で既存 DB への接続を返す。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計に基づく差分取得・保存・品質チェック連携の基礎を実装。
  - ETLResult データクラスで実行結果・品質問題・エラー一覧を表現（to_dict により監査ログ用に整形）。
  - 差分判定ユーティリティ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _get_max_date: 汎用最大日付取得
    - _table_exists: テーブル存在チェック
  - 市場カレンダーを参照して営業日に調整する _adjust_to_trading_day を実装（30 日遡り検索）。
  - run_prices_etl を実装（差分の自動算出、backfill_days による再取得、fetch→save の流れ）。
  - ETL の設計方針として、品質チェックは Fail-Fast にせず結果を集約して呼び出し元に委ねる方針を明記。

### Security

- RSS/XML 関連:
  - defusedxml の採用により XML インジェクション／XML Bomb のリスクを軽減。
  - SSRF 対策を実装（スキーム制限、プライベートアドレス拒否、リダイレクト検査）。
  - 外部リソース取得時に User-Agent を設定（KabuSys-NewsCollector/1.0）。

- 環境変数読み込み:
  - OS 環境変数はデフォルトで優先され、.env.local は override=True で上書き可（但し既存の OS 環境は protected）。

### Known issues / Notes

- run_prices_etl の戻り値に小さなバグあり:
  - 現在の実装の最後が `return len(records), ` のように 2 要素タプルの 2 番目が欠ける形になっており、実行時に SyntaxError/TypeError を引き起こす可能性があります。2 番目は saved（保存した件数）を返す意図のため、修正が必要です。
- 一部モジュール（strategy, execution, monitoring）は __init__ のみで実装が空のため、実際の戦略ロジック・発注ロジックは未実装。
- テストカバレッジ・例外ケースの詳細なユニットテストは未提供（今後の追加推奨）。
- J-Quants API の仕様変更やレート制限の変更時は jquants_client の定数調整が必要。

### Configuration / Environment variables

このリリースで利用される主な環境変数（Settings 参照）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略時: data/kabusys.duckdb)
- SQLITE_PATH (省略時: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) (省略時: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (省略時: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動ロードを無効化)

### Migration / Upgrade notes

- 初回は init_schema(...) を呼び出して DuckDB のスキーマを作成してください。
- 既存の DuckDB に対しては get_connection(...) を利用し、必要に応じて init_schema を再実行すると冪等的にテーブルが作成されます。
- .env/.env.local の読み込みはプロジェクトルートの検出に依存するため、配布後は適切に .env ファイルを設置してください（または KABUSYS_DISABLE_AUTO_ENV_LOAD で読み込みを制御）。

---

（注）本 CHANGELOG はソースコードからの逆推定に基づいて作成しています。実際のリポジトリ履歴やコミットメッセージに基づくものではありません。必要であれば、各機能ごとにより詳細な変更点や使用例・サンプルを追記できます。