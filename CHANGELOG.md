CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョンは semantic versioning に従います。

Unreleased
----------
（未リリースの既知点・予定修正）

Added
- run_prices_etl の戻り値の扱いを見直し予定。現状の実装では
  `return len(records),` のようにタプルが不完全で返される可能性があり、
  実際には (fetched, saved) の2要素を返すことが意図されているため修正予定。

Fixed / Triage
- ETL 実行フロー上の小さな不整合（上記の戻り値）を優先的に修正予定。

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

環境設定 / 設定読み込み
- .env ファイルおよび環境変数から設定を読み込む設定モジュールを追加（src/kabusys/config.py）。
  - プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local を読み込む自動ロード機能を提供。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - export KEY=val 形式・クォートされた値・コメント行の扱いに対応した .env パーサを実装。
  - 必須環境変数取得時に未設定なら明示的に例外を投げる _require を提供。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を追加。
  - DB パス設定（DUCKDB_PATH, SQLITE_PATH）を Path 型で取得。

J-Quants API クライアント
- jquants_client モジュールを追加（src/kabusys/data/jquants_client.py）。
  - API レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter 実装。
  - 再試行ロジック（指数バックオフ、最大 3 回）を実装。対象: 408/429/5xx、429 の場合は Retry-After ヘッダを優先。
  - 401 Unauthorized 受信時はリフレッシュトークンで自動的に id_token を再取得して 1 回リトライする機能を実装（無限再帰防止済み）。
  - id_token のモジュールレベルキャッシュでページネーション間のトークン共有に対応。
  - ページネーション対応の取得関数を提供:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (四半期財務)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への保存用関数を提供（冪等性確保: ON CONFLICT DO UPDATE）:
    - save_daily_quotes (raw_prices)
    - save_financial_statements (raw_financials)
    - save_market_calendar (market_calendar)
  - データ変換ユーティリティ (_to_float, _to_int) を実装し、空値/不正値を安全に扱う。

ニュース収集（RSS）
- news_collector モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS フィードから記事を収集し raw_news テーブルへ保存する ETL 機能を実装。
  - セキュリティ・堅牢性強化:
    - defusedxml による XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカルでないかの判定、リダイレクト先検査用のカスタム HTTPRedirectHandler を実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を設け、Gzip 解凍後もサイズチェックを実施（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding の指定、および最大受信バイト数読み取りでメモリ DoS を低減。
  - URL 正規化とトラッキングパラメータ除去機能を実装（utm_*, fbclid などの削除、クエリソート、フラグメント削除）。
  - 記事IDは正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保。
  - テキスト前処理（URL 除去・空白正規化）を実装。
  - DB 保存はチャンク化したトランザクションで実行し、INSERT ... RETURNING を使って実際に挿入された ID を返す:
    - save_raw_news: raw_news へ記事を保存し新規 inserted id のリストを返す。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols へ (news_id, code) ペアを一括挿入し、実挿入数を正確に返す。
  - 銘柄コード抽出: 正規表現による 4 桁コード抽出と known_codes によるフィルタリングを提供。
  - run_news_collection により複数 RSS ソースを順次処理し、個々のソースでの失敗は他ソースに影響させない実装。

DuckDB スキーマ & 初期化
- schema モジュールを追加（src/kabusys/data/schema.py）。
  - DataSchema.md に準拠した多層スキーマを定義（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed テーブル。
  - features, ai_scores などの Feature テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance などの Execution テーブル。
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）とインデックスを定義。
  - init_schema(db_path) によりディレクトリ作成 → 接続 → テーブル・インデックスの作成（冪等）を実行。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。

ETL パイプライン
- pipeline モジュールを追加（src/kabusys/data/pipeline.py）。
  - ETLResult dataclass を定義し ETL 実行結果の集約（取得件数、保存件数、品質問題、エラーリスト等）を提供。
  - テーブルの最終日付取得ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダーに基づく営業日調整ヘルパー (_adjust_to_trading_day) の実装。
  - 差分更新ロジック: 最終取得日からの backfill（デフォルト backfill_days=3）で後出し修正を吸収する方針。
  - run_prices_etl を実装（差分取得 → jq.fetch_daily_quotes → jq.save_daily_quotes → ログ・結果集計）。（注: 返り値の整合性に関する既知の問題あり、Unreleased に記載）

Logging / Observability
- 各モジュールでログ出力を適切に追加（info/warning/exception）。ETLResult を辞書化する to_dict を提供し監査ログに利用可能。

Security
- RSS の XML 処理に defusedxml を採用。
- RSS フェッチで SSRF を防ぐスキーム・ホスト検査・リダイレクト検証を実装。
- HTTP クライアントでタイムアウトと最大読み取り長を設定しメモリ攻撃耐性を確保。
- .env 読み込みで OS 環境変数の保護機能（protected set）を実装。

Known issues / Notes
- pipeline.run_prices_etl の戻り値実装が不完全（上記 Unreleased）。テスト・修正が必要。
- パッケージの __all__ には "monitoring" が含まれているが、ソースツリーには monitoring モジュールの実装が見られない（将来追加予定または省略の可能性）。
- 単体テスト・統合テストはコード中に見当たらないため、CI/テストの追加が推奨される。

その他
- コード全体で DuckDB を主要永続層として使用する設計が採用されているため、運用時のバックアップ/スナップショット方針を整備することを推奨。

謝辞
- 初版の設計ではデータの冪等性・セキュリティ・外部APIの不安定性（レート制限・429/リトライ）への対処が重点的に盛り込まれています。今後のリリースでは監視・テスト・細かいバグ修正（上記 Known issues）を優先して改善していく予定です。