# CHANGELOG

このプロジェクトは Keep a Changelog 準拠で管理しています。  
各リリースはセマンティックバージョニングに従います。

すべての変更履歴はソースコードから推測して作成しています（実装のコメント／定数・関数名等に基づく）。

## [0.1.0] - 2026-03-17

最初の公開リリース。日本株自動売買システム「KabuSys」のコア機能を含む初期実装を追加。

### 追加
- パッケージ構成
  - kabusys パッケージを追加。公開 API（__all__）として data、strategy、execution、monitoring をエクスポート。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env 読み込み（プロジェクトルート検出：.git または pyproject.toml を基準）。自動読み込みを無効にするための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パースの強化（export プレフィックス対応、クォート内エスケープ、インラインコメント処理）。
  - 必須環境変数チェック用の _require()。設定プロパティ：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
  - settings = Settings() をモジュール単位で提供。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - 認証トークン取得 get_id_token（リフレッシュトークン → idToken）。
  - HTTP リクエストの共通実装（_request）：
    - レート制限（120 req/min）を守る固定間隔スロットリング実装。
    - リトライ（指数バックオフ）と HTTP ステータスによる再試行（408, 429, 5xx 等）。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）。
  - DuckDB への冪等保存関数 save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT DO UPDATE を利用）。
  - 型変換ユーティリティ (_to_float / _to_int) を実装し、データ整合性を維持。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news テーブルへ保存する一連の実装。
  - 設計／安全対策:
    - defusedxml を使った XML パース（XML Bomb 等への対策）。
    - SSRF 対策（URL スキーム検証、プライベートアドレス判定、リダイレクト時の検証）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後の検査（Gzip bomb 対策）。
    - 記事ID は URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を確保。トラッキングパラメータ（utm_* 等）を除去。
    - content:encoded を優先、description を代替として処理。
    - URL 正規化、テキスト前処理（URL除去・空白正規化）。
  - DB 保存:
    - save_raw_news: チャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し新規挿入 ID を返す。トランザクションでまとめて実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンクINSERTで行い、挿入件数を正確に返す。
  - 銘柄コード抽出（extract_stock_codes）:
    - 4桁の数字パターンを検出し、known_codes（有効銘柄セット）との突合で有効コードのみ返す。重複除去。

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層を含むテーブル定義とインデックスを追加。
  - テーブル例: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等。
  - init_schema(db_path) によりディレクトリ自動作成→テーブル・インデックス作成（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラスで ETL の結果・品質問題・エラーを集約できるように実装。
  - 差分更新ヘルパー（最終取得日の取得、テーブル存在確認、営業日調整）を実装。
  - run_prices_etl：差分更新ロジック（最終取得日に基づく date_from 自動算出、backfill_days による再取得）を実装。fetch → save の流れを実現。
  - pipeline は品質チェック（quality モジュール）と連携する設計を反映（品質問題は収集するが ETL を中断しない方針）。

### セキュリティと堅牢性
- ネットワークと外部入力に対する複数の保護
  - RSS 周りで defusedxml、SSRF 対策、プライベート IP 判定、レスポンス長チェック、gzip 解凍後チェックを実装。
  - J-Quants クライアント側でタイムアウト、リトライ、レート制御、401 自動リフレッシュを実装。

### ドキュメント（コード内）
- 各モジュールに実装方針・設計原則・処理フローの説明コメントを追加。DataPlatform.md / DataSchema.md 等に対応する実装方針を反映。

### 既知の問題 / TODO
- run_prices_etl の戻り値がコード断片のまま（ソース末尾が途中で切れているため、戻り値のタプル (fetched_count, saved_count) を正しく返す実装が未完と思われる）。本リリース前に確認・修正が必要。
- strategy, execution, monitoring パッケージは __init__.py が空であり、具体的な実装は今後追加予定。

### 必要な環境変数（起動に必須／推奨）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 任意（デフォルト値あり）:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL — デフォルト: INFO
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 値を設定すると自動 .env 読み込みを無効化
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
  - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）

### マイグレーション / 利用時の注意
- 初回は必ず schema.init_schema(db_path) を実行して DuckDB スキーマを作成してください。
- news_collector の run_news_collection を使う場合、extract_stock_codes に渡す known_codes を用意しておくと銘柄紐付けが有効になります。
- 自動 .env 読み込みはプロジェクトルートを基準に行われるため、配布後やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自前の環境変数注入を行ってください。

---

このリリースは初期機能の集合であり、今後以下を予定しています：
- strategy / execution / monitoring の具体的な実装（発注ロジック、ポジション管理、Slack 通知等）
- 品質チェック（quality モジュール）との統合強化と詳細チェック項目の追加
- テストカバレッジの整備およびエンドツーエンドの CI ワークフロー

ご要望や重大バグを見つけられた場合は issue を作成してください。