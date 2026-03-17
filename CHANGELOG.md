# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトの初期バージョンは `0.1.0` です（パッケージバージョン: src/kabusys/__init__.py の `__version__ = "0.1.0"` に基づく）。

現在日付: 2026-03-17

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システムのコアライブラリを追加。

### Added
- パッケージの基礎
  - パッケージメタ情報を追加（src/kabusys/__init__.py、`__version__ = "0.1.0"`）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルや環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）。
  - .env パーサ（export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメント対応）。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - 必須設定を取得する `_require()`、および Settings クラスを提供。
  - サポートされる環境: `development`, `paper_trading`, `live`。ログレベル検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
  - 主要設定プロパティ（例）:
    - J-Quants: `JQUANTS_REFRESH_TOKEN`
    - kabuステーション: `KABU_API_PASSWORD`, `KABU_API_BASE_URL`（デフォルト: http://localhost:18080/kabusapi）
    - Slack: `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - DBパス: `DUCKDB_PATH`（デフォルト: data/kabusys.duckdb）、`SQLITE_PATH`（デフォルト: data/monitoring.db）
  - Settings インスタンス `settings` を公開。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得機能を追加。
  - レート制限管理（固定間隔スロットリング、デフォルト 120 req/min）を実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx）。429 の場合は Retry-After ヘッダを優先。
  - 401 が返った場合のトークン自動リフレッシュ（1回のみ）とモジュールレベルの ID トークンキャッシュ。
  - ページネーション対応（pagination_key を利用してデータを継続取得）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。冪等性のため ON CONFLICT DO UPDATE を使用。
  - データ変換ユーティリティ `_to_float`, `_to_int` を追加。
  - fetched_at に UTC タイムスタンプを記録して Look-ahead Bias のトレースを可能に。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからニュース記事を収集し、DuckDB の raw_news テーブルに保存するフローを実装。
  - セキュリティ対策:
    - defusedxml を用いた安全な XML パース（XML Bomb 等対策）。
    - SSRF 対策：URL スキーム検証（http/https のみ許可）、リダイレクト先の事前検証、プライベート/ループバック/リンクローカル IP 判定によるブロック。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック。
  - URL 正規化: トラッキングパラメータ（utm_*, fbclid, gclid など）を削除し、クエリをキーでソート、フラグメント削除。
  - 記事IDは正規化 URL の SHA-256 (先頭32文字) により生成し冪等性を確保。
  - RSS の pubDate を UTC に正規化して保存（パース失敗時は現在時刻で代替し警告）。
  - DB 保存はチャンク化と1トランザクション単位で実行（INSERT ... RETURNING を使用して実際に挿入されたIDを取得）。
  - news_symbols による記事と銘柄コードの紐付け処理とバルク挿入機能を実装。
  - デフォルト RSS ソースを定義（例: Yahoo Finance のビジネスカテゴリ）。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の各レイヤーに対応したテーブルを網羅的に定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）。
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY）を設定。
  - 頻出クエリ向けのインデックスを定義。
  - init_schema(db_path) による初期化関数を提供（親ディレクトリを自動作成、冪等的にテーブルを作成）。
  - get_connection(db_path) で既存DB接続を返すユーティリティを提供。

- パイプライン（ETL）モジュール（src/kabusys/data/pipeline.py）
  - 差分更新（差分取得）を行う ETL フレームワークの基礎を実装。
  - ETL 結果を表す dataclass ETLResult を定義（品質チェック問題、エラーリスト、fetched/saved カウントなど）。
  - テーブル存在確認、最大日付取得ユーティリティを実装。
  - 市場カレンダーに応じた営業日調整ヘルパーを追加。
  - last date からの差分取得ロジック（backfill_days により後出し修正を吸収）を実装。
  - run_prices_etl の骨組みを実装（J-Quants から日足取得 → DuckDB へ保存 → ログ出力）。

- パッケージモジュール構成（src/kabusys/data/__init__.py、execution、strategy 初期化ファイルを追加）。

### Security
- ニュース収集に関して SSRF、防止策を多数導入（スキーム検証、プライベートIP判定、リダイレクト検査）。
- XML パースに defusedxml を使用して XML 関連の脆弱性へ対処。
- 外部API呼び出しではタイムアウト/リトライ/レート制限を設け、過負荷やサービス拒否のリスクを低減。

### Changed
- 初回リリースのため「変更」は該当なし。

### Fixed
- 初回リリースのため「修正」は該当なし。

### Known issues / Notes（注意点）
- run_prices_etl の最終行（返却値の部分）が現状のソース表示では不完全に見えます（`return len(records),` のようにタプルの第二要素が欠けている記述が確認できるため、実行時に SyntaxError または想定の戻り値タプルが得られない可能性があります）。意図としては (fetched_count, saved_count) を返す設計のため、実装の確認・修正を推奨します。
- ETL の品質チェック（quality モジュール参照）はコード内で参照されているが、ここに示されたソースツリーでは quality モジュールの詳細実装が存在しない可能性があります。品質チェックの統合時は該当モジュールの提供を確認してください。
- NewsCollector の DNS 解決失敗は「非プライベートとみなす」設計になっており、テスト環境や特殊ネットワーク構成では運用上の注意が必要です（失敗時に安全側に倒す方針を採るかは要検討）。
- デフォルトの DB パス（data/kabusys.duckdb）や .env の読み込み位置はプロジェクトルート検出に依存するため、配布やコンテナ化時は適切に配置・環境変数を設定してください。

### Migration / Breaking changes
- 初回リリースのため破壊的変更は無し。

---

今後の予定（提案）
- run_prices_etl の戻り値修正と単体テスト追加。
- quality モジュールの実装/統合と品質チェック結果の自動エスカレーションポリシーの追加。
- execution/strategy モジュールの具備（現状は __init__ のみ）。
- CI での静的解析・セキュリティチェック（bandit, mypy 等）導入。