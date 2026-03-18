CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- 次期リリース向けの変更はここに記載します。

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ構成: data, strategy, execution, monitoring を公開する基本構成を追加。
- 環境設定管理 (kabusys.config)
  - .env/.env.local からの自動読み込みをプロジェクトルート（.git または pyproject.toml）から行う仕組みを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装:
    - export KEY=val 形式対応、クォート付き値のバックスラッシュエスケープ処理、インラインコメントの扱い（クォート有無での挙動差）。
    - override フラグと protected セットにより OS 環境変数の保護を実現。
  - Settings クラスを提供し、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等の取得メソッドと入力値検証（KABUSYS_ENV, LOG_LEVEL の検証）を実装。
  - デフォルトの DB パス (DUCKDB_PATH, SQLITE_PATH) を指定。

- J-Quants クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得関数を実装（ページネーション対応）。
  - 認証: refresh token から id_token を取得する get_id_token を実装。
  - HTTP ユーティリティ:
    - 固定間隔スロットリング（120 req/min）を守る RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大3回、対象: 408/429/5xx）を実装。429 の場合は Retry-After を優先。
    - 401 受信時は id_token を自動リフレッシュして 1 回だけリトライ（無限再帰を防ぐフラグを採用）。
  - データ保存関数:
    - DuckDB に対する save_daily_quotes, save_financial_statements, save_market_calendar を実装。いずれも冪等性のため ON CONFLICT DO UPDATE を使用。
    - fetched_at を UTC タイムスタンプで記録し、Look-ahead Bias を追跡可能に。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を取得し raw_news に保存する機能を実装（DEFAULT_RSS_SOURCES にサンプル追加）。
  - セキュリティ・堅牢性:
    - defusedxml による XML パース（XML Bomb 等対策）。
    - URL 正規化・トラッキングパラメータ除去（utm_ 等）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証。
    - HTTP リダイレクト時にスキームとホストの検査を行う専用ハンドラで SSRF を防止。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合はアクセスを拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の再検査でメモリ DoS を軽減。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事IDを返す。チャンク・トランザクション単位で挿入してロールバック処理を整備。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへ紐付けを一括挿入（ON CONFLICT DO NOTHING、INSERT ... RETURNING を使用）。
  - 銘柄コード抽出: 正規表現で 4 桁数字を候補とし、既知コードセットでフィルタリングする extract_stock_codes を提供。
  - run_news_collection: 複数 RSS ソースの収集を統合し、エラー分離（1 ソース失敗でも続行）しつつ新規件数を返却。既知コードが与えられれば新規記事について銘柄紐付けも行う。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataPlatform 設計に沿った 3 層（Raw / Processed / Feature / Execution）テーブル群の DDL を追加。
  - テーブルに対する制約（PRIMARY KEY, CHECK, FOREIGN KEY）や頻用クエリを意識したインデックスを定義。
  - init_schema(db_path) でディレクトリ自動作成・全テーブル作成（冪等）を行い DuckDB 接続を返す。get_connection() で既存 DB への接続を取得可能。

- ETL パイプライン基礎 (kabusys.data.pipeline)
  - ETLResult データクラスを導入し ETL 実行結果（取得数・保存数・品質問題・エラー）を集約。
  - 差分更新のためのユーティリティ:
    - テーブル存在チェック、最大日付取得関数（get_last_price_date 等）を追加。
    - _adjust_to_trading_day：非営業日の調整ロジック（market_calendar を利用）を実装。
  - run_prices_etl: 差分更新ロジック（最終取得日 - backfill_days の再取得、デフォルト backfill_days=3）を実装し、fetch→save を呼び出す仕組みを実装（idempotent、id_token 注入可能でテスト容易性に配慮）。
  - 品質チェックモジュール（quality）との連携を想定する設計（品質チェックは重大度を管理しつつ ETL を継続する方針）。

Security
- 複数の箇所でセキュリティ対策を実装:
  - defusedxml による XML パース防御。
  - SSRF 対策: リダイレクト時のスキーム・ホスト検証、事前のホストプライベートチェック。
  - レスポンスサイズ制限、gzip 解凍後の再チェック（Gzip bomb 対策）。
  - 環境変数読み込み時の保護（protected set）と自動ロード無効化フラグ。

Performance / Reliability
- API 呼び出しのレートリミット（120 req/min）を固定間隔スロットリングで厳守。
- 再試行（指数バックオフ）と 429 Retry-After の優先利用で堅牢な通信を実現。
- DuckDB 側はチャンクインサートとトランザクションで効率と整合性を向上。
- save_* 系は ON CONFLICT により冪等性を担保。

Developer notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト:
  - KABUSYS_ENV=development（有効値: development, paper_trading, live）
  - LOG_LEVEL=INFO（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - DUCKDB_PATH デフォルト: data/kabusys.duckdb、SQLITE_PATH デフォルト: data/monitoring.db
- テスト支援:
  - id_token を注入できる設計（jquants_client の呼び出しや pipeline）や、news_collector._urlopen をモック差し替え可能。

Known limitations / Notes
- 一部の処理（品質チェック quality モジュールや pipeline の全ジョブ）については本実装で参照・呼び出しを想定しているが、quality モジュール本体や全ての ETL ジョブの実装は別ファイル/今後のリリース対象。
- run_prices_etl の末尾がコード断片で終了している（トランスクリプトの末端のため、実装の続きが存在する可能性があります）。必要に応じて戻り値やログの整合性を確認してください。

免責事項
- 本 CHANGELOG は与えられたコードベースから推測して作成しています。実際の変更履歴（コミットログ等）と差異がある場合があります。