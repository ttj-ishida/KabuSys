# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを採用します。
このプロジェクトの初期バージョンは 0.1.0 です。

## [Unreleased]

## [0.1.0] - 2026-03-17
初期リリース。

### Added
- パッケージの基本構成を追加
  - パッケージ名: kabusys、公開モジュール: data, strategy, execution, monitoring（src/kabusys/__init__.py）。
  - パッケージバージョンを 0.1.0 に設定。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定値を読み込む自動ローダを実装。
  - プロジェクトルート判定ロジック: .git または pyproject.toml を辿って自動検出（カレントワーキングディレクトリに依存しない）。
  - .env, .env.local の読み込み順 (OS 環境変数 > .env.local > .env) を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env 行パーサ: export プレフィックス、クォート内のバックスラッシュエスケープ、コメント処理などをサポート。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル検証などのプロパティを実装。
  - 必須環境変数未設定時は ValueError を送出するヘルパーを追加。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する機能を追加。
  - API レート制限（120 req/min）を固定間隔スロットリングで守る RateLimiter を実装。
  - 再試行ロジック（指数バックオフ、最大3回）を実装。408/429/5xx をリトライ対象に含める。
  - 429 に対しては HTTP ヘッダ Retry-After を優先利用。
  - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回だけリトライする自動リフレッシュ機構を追加。
  - ページネーション対応（pagination_key）を実装。
  - DuckDB への保存用ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を追加。いずれも冪等性を保つため ON CONFLICT DO UPDATE を利用。
  - データ取り込み時点の fetched_at を UTC ISO8601 形式で付与し、Look-ahead Bias を防止するトレーサビリティを提供。
  - 型変換ユーティリティ _to_float / _to_int を実装（空値や不正値に対する堅牢な振る舞いを提供）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得して raw_news テーブルへ保存する機能を実装（DEFAULT_RSS_SOURCES に既定のフィードを設定）。
  - セキュリティ対策:
    - defusedxml を使った XML パースで XML Bomb 等に対する防御。
    - SSRF 対策: URL スキーム検証 (http/https 限定)、ホストがプライベート/ループバック/リンクローカルでないことを検査、リダイレクト時にも検証するカスタムリダイレクトハンドラを実装。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) を厳格にチェックし、gzip 圧縮の解凍後も検査してメモリ DoS を防止。
    - URL 正規化でトラッキングパラメータ（utm_* など）を削除。
  - 記事IDは正規化 URL の SHA-256 の先頭32文字で生成し冪等性を確保。
  - テキスト前処理（URL除去・空白正規化）を実装。
  - DuckDB への保存はトランザクションでまとめ、INSERT ... ON CONFLICT DO NOTHING と RETURNING を使って実際に挿入された ID を返す実装（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 銘柄コード抽出ユーティリティ extract_stock_codes を実装（4桁数字、known_codes に基づくフィルタ、重複除去）。
  - run_news_collection で複数ソースを独立して処理し、個別ソースの失敗が他に影響しないフェールオーバー動作を実装。

- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - DataSchema.md に基づいた 3 層（Raw / Processed / Feature / Execution）を含むスキーマを定義。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw Layer。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols を含む Processed Layer。
  - features, ai_scores を含む Feature Layer。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance を含む Execution Layer。
  - 頻出クエリに対応するインデックスを作成。
  - init_schema(db_path) により親ディレクトリの自動作成・DDL 実行・インデックス作成を行い、初期化済みの DuckDB 接続を返す。get_connection() で既存 DB へ接続可能。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult データクラスを導入し、ETL 実行結果（取得件数、保存件数、品質問題、エラー等）を一元管理。
  - 差分更新（最終取得日からの差分取得）をサポートするユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダーを参照して非営業日調整を行う _adjust_to_trading_day。
  - run_prices_etl を実装（差分取得の date_from 自動算出、バックフィル日数の設定、jq.fetch_daily_quotes と jq.save_daily_quotes を利用）。バックフィルのデフォルトは 3 日。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- ニュース収集:
  - SSRF/内部IP への到達防止、XML パースの安全化、受信サイズ制限、gzip 解凍後サイズチェック等の防御策を導入。
- 環境変数読み込み:
  - OS 環境変数を保護する protected 機能を用いて .env 上書きの管理を実装。

### Notes / Design highlights
- API クライアント設計:
  - レートリミットおよび再試行・トークン自動更新を組み合わせ、API 呼び出しの堅牢性を高める。
  - fetched_at に UTC タイムスタンプを記録してデータの可追跡性を確保。
- DB 保存:
  - DuckDB を一次データストアに採用し、DDL をコードで管理。ほとんどの挿入処理は冪等性を考慮して実装。
- テスト容易性:
  - _urlopen や id_token 注入等、テストで差し替え可能なポイントを考慮して設計。

---

開発・運用上の補足や既知の制限・将来の改善候補はドキュメントに別途まとめる予定です。必要であればこの CHANGELOG に追記します。