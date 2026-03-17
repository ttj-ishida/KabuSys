# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに準拠して記載しています。  
このファイルは日本語で記述されています。

全般:
- 初期リリース v0.1.0 を公開。
- パッケージのバージョンは `src/kabusys/__init__.py` の `__version__ = "0.1.0"` に合わせています。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-17
初期リリース。本リリースでは日本株自動売買基盤のコア機能（設定管理、データ取得・保存、ニュース収集、DuckDB スキーマ、ETL パイプラインの骨格など）を実装しました。

### 追加（Added）
- パッケージ骨格
  - kabusys パッケージを追加し、サブモジュール（data, strategy, execution, monitoring）をエクスポート。

- 設定管理（src/kabusys/config.py）
  - .env ファイルや環境変数から設定を自動ロードする機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env 構文パーサ実装（コメント対応、export プレフィックス対応、クォートとエスケープ処理）。
  - 自動ロードを無効にする環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供（テスト用途）。
  - 必須設定取得ヘルパー `_require()` と Settings クラスを提供。主要な設定プロパティ：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV (development/paper_trading/live), LOG_LEVEL
  - settings インスタンスを公開。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を対象）。
  - 401 Unauthorized を受けた際の自動トークンリフレッシュ（1回のみ）とリトライ処理。
  - ID トークンのモジュールレベルキャッシュ（ページネーション間で共有）。
  - DuckDB への冪等な保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT DO UPDATE）。
  - 型変換ユーティリティ `_to_float`, `_to_int` を実装（不正値は None）。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集する fetch_rss、記事を DuckDB に保存する save_raw_news、記事と銘柄を紐付ける機能を実装。
  - セキュリティ・堅牢化:
    - defusedxml を用いた XML パース。
    - SSRF 対策（スキーム検証、プライベートアドレス判定、リダイレクト時検査用ハンドラ）。
    - 受信バイト数上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の検査（Gzip bomb 対策）。
    - 許可された URL スキームは http/https のみ。
  - URL 正規化（トラッキングパラメータ除去、フラグメント除去、クエリソート）と記事ID生成（正規化 URL の SHA-256 の先頭32文字）。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 挿入はチャンク化してトランザクションで実行、INSERT ... RETURNING を使用して実際に挿入された件数を返却。重複は ON CONFLICT でスキップ。
  - 銘柄コード抽出関数（4 桁数字、known_codes によるフィルタリング）を実装。
  - run_news_collection により複数ソースを順次処理し、ソース単位で独立したエラーハンドリングを行う。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の多層スキーマを定義する DDL を実装。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を設定。
  - 運用上の検索に合わせたインデックス群を定義（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) による DB 初期化関数と get_connection() を提供。init_schema は親ディレクトリの自動作成や冪等的テーブル作成を行う。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新の方針に基づく ETL の骨格を実装（差分取得、保存、品質チェックフック）。
  - ETLResult データクラスを実装し、実行結果（取得件数、保存件数、品質問題リスト、エラーリスト）を格納・辞書化可能。
  - 市場カレンダーの先読み（デフォルト lookahead 90 日）、バックフィルのデフォルト設定（backfill_days=3）。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date 等のユーティリティ関数を実装。
  - run_prices_etl により差分ETL（date_from の自動算出、最小データ日 2017-01-01 をサポート）を実現。id_token 注入によりテストしやすい設計。

- テスト・デバッグ向けの差し替えポイント
  - news_collector._urlopen をモック可能（テストでの差し替えを想定）。
  - jquants_client の各取得関数は id_token を注入可能。

### 修正（Changed）
- （初版のためなし）

### 修正（Fixed）
- （初版のためなし）

### 削除（Removed）
- （初版のためなし）

### セキュリティ（Security）
- RSS/HTTP 関連で以下のセキュリティ対策を実装:
  - defusedxml を用いて XML ベースの攻撃を軽減。
  - SSRF を防ぐためのスキーム検証、DNS 解決時のプライベートIP検査、リダイレクト検査ハンドラを実装。
  - レスポンスサイズ上限と gzip 解凍後のサイズチェック（メモリ DoS / zip bomb 対策）。
- 環境変数の自動読み込み時に OS 環境変数を保護する仕組みを導入（.env.local の上書き挙動を制御）。

### 既知の制約 / 注意点（Notes）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - これらが未設定の場合、Settings の各プロパティは ValueError を送出します。
- 自動 .env ロードはプロジェクトルート検出に依存するため、配布後に動作させる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的に環境をセットアップすることを推奨します。
- DuckDB 初期化は init_schema を使用してください。既存 DB を利用する場合は get_connection を使用し、スキーマ初期化は行われません。
- J-Quants API のレート制限は 120 req/min に固定してあり、長時間にわたる大量リクエストを実行する際は注意が必要です。
- news_collector の記事 ID は URL 正規化に依存するため、トラッキングパラメータの有無で同一記事の判別が行われます（utm_* 等は除去されます）。

### 使い始め（Quick start）
- DuckDB スキーマ初期化例:
  - init_schema("data/kabusys.duckdb") を呼んでから ETL / ニュース収集を実行してください。
- 環境変数サンプル:
  - .env に JQUANTS_REFRESH_TOKEN=..., SLACK_BOT_TOKEN=..., SLACK_CHANNEL_ID=..., KABU_API_PASSWORD=... を設定。

---

貢献・報告:
- バグ報告や改善提案は issue を作成してください。セキュリティ脆弱性の報告はプライベートにお願いします。