# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」規約に準拠しています。

## [0.1.0] - 2026-03-17

初回リリース — KabuSys の基本機能を実装しました。日本株自動売買プラットフォームのコアとなるモジュール群（データ収集・スキーマ定義・ETL・設定管理・ニュース収集など）を提供します。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - モジュール構成（data, strategy, execution, monitoring）を定義。strategy/execution/monitoring は初期スタブを用意。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local または OS 環境変数から設定を自動読み込みする仕組みを実装。プロジェクトルート判定は .git または pyproject.toml を基準に探索するためパッケージ配布後も安定して動作。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env の堅牢なパース機能を実装（export形式対応、クォートとエスケープの処理、インラインコメントの取り扱い）。
  - Settings クラスを提供し、各種必須環境変数の取得とバリデーションを実装（J-Quants / kabu / Slack / DB パス / 環境・ログレベルの検証等）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、四半期財務データ、マーケットカレンダー等の取得関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。ページネーション対応。
  - レート制限対応（固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装）。
  - リトライロジック（指数バックオフ、最大 3 回、対象ステータスコード: 408, 429, 5xx）。
  - 401 受信時にリフレッシュトークンで自動的に id_token を再取得して1回リトライする処理を実装。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。SQL 側は ON CONFLICT DO UPDATE を用いて重複を排除。
  - データ取得時に fetched_at を UTC で記録し、いつデータを取得したかをトレース可能にする方針を採用。
  - 型変換ユーティリティ（_to_float, _to_int）で不正値・空値の扱いを明確化。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからニュース記事を収集して DuckDB の raw_news に保存する機能を実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection 等）。
  - セキュリティ・堅牢性対策:
    - defusedxml による XML パース（XML Bomb 等への対策）。
    - SSRF 対策: リダイレクト許可前にスキーム検証、ホストがプライベートアドレスかのチェック、カスタムリダイレクトハンドラで都度検証。
    - URL スキームは http/https のみ許可。
    - レスポンス受信サイズを上限（MAX_RESPONSE_BYTES = 10MB）で制限し、gzip 解凍後もサイズチェック。
    - トラッキングパラメータ（utm_*, fbclid 等）を除去する URL 正規化、SHA-256 ハッシュ先頭32文字を記事IDとして生成し冪等性を確保。
  - DB 書き込みはチャンク/トランザクションで実施、INSERT ... RETURNING を使い実際に挿入された行のみをカウントする実装。
  - 銘柄コード抽出機能（4桁の銘柄コード）と既知コードフィルタリングを実装。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 必要なインデックスを定義（銘柄×日付スキャンやステータス検索を高速化）。
  - init_schema(db_path) によりディレクトリ作成（必要時）→ テーブル/インデックス作成を行い、DuckDB 接続を返す。get_connection で既存 DB へ接続可能。

- ETL パイプライン骨子（src/kabusys/data/pipeline.py）
  - ETLResult データクラスで ETL 実行結果や品質問題・エラーを集約。
  - 差分取得のヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）を実装。
  - 市場カレンダーを考慮して非営業日を直近営業日に調整する _adjust_to_trading_day を実装。
  - run_prices_etl（株価差分 ETL）を導入し、差分計算（最終取得日と backfill）→ fetch → save のワークフローを実現する基盤を実装。

### Changed
- 初期リリースなので過去バージョンからの変更はありません（新規実装）。

### Fixed
- （なし：初回リリース）

### Security
- ニュース収集周りで以下のセキュリティ対策を導入:
  - defusedxml を使用した XML パース（XML 攻撃対策）。
  - SSRF 対策（リダイレクト検査、プライベートアドレス拒否、スキーム制限）。
  - レスポンスサイズ制限・gzip 解凍後検査（DoS/Bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去により同一記事の正確な同定を実現。

### Known Issues / Notes
- run_prices_etl の戻り値に関する実装上の不整合:
  - 関数シグネチャは (int, int) を返すことを想定していますが、ソースの末尾に "return len(records)," のような単一値のタプル（saved 値が返されていない）となっており、取得件数と保存件数の両方を返す意図と異なる可能性があります。リリース後に saved 値を正しく返す修正が必要です。
- strategy / execution / monitoring モジュールはインターフェースやスタブのみで、実際の売買ロジック・注文管理・監視機能は今後の実装フェーズ。
- settings により必須環境変数が未設定の場合は ValueError を投げるため、運用前に .env サンプルを基に環境を整備してください。
- DuckDB のスキーマは包括的に定義済みですが、運用前に init_schema を実行して DB を初期化してください（:memory: オプションでインメモリ DB が利用可能）。

### Migration / Usage notes
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト DB パス:
  - duckdb: data/kabusys.duckdb
  - sqlite (監視用): data/monitoring.db
- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml で検出して行われます。CI などで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

開発・運用にあたって不明点や追加で記載してほしい変更点があれば教えてください。必要に応じて既知のバグを修正したパッチリリースノートも作成します。