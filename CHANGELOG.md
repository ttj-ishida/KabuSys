Keep a Changelog に準拠した形式で、コードベースから推測できる変更履歴（日本語）を作成しました。初回リリース 0.1.0 としてまとめています。

CHANGELOG.md
=============
すべての変更は semver に従います。  
このファイルは Keep a Changelog のガイドラインに準拠します。

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報（src/kabusys/__init__.py）を追加。
  - 空のサブパッケージを用意: execution/, strategy/, monitoring/（将来の実装用スタブ）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env のパース機能を実装:
    - 空行・コメント・export KEY=val 形式対応。
    - シングル／ダブルクォート内でのバックスラッシュエスケープ対応。
    - インラインコメント扱いのルール（クォートなしの場合の '#' の扱い）。
  - .env 自動ロードの制御: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化。
  - OS 環境変数を保護する override/protected ロジック。
  - Settings クラスを提供し、以下の設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL（検証）
    - is_live / is_paper / is_dev のブールショートカット

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 基本機能:
    - 株価日足（OHLCV）、四半期財務データ、マーケットカレンダーの取得関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - ページネーション対応（pagination_key の追跡で重複取得を防止）。
  - 認証:
    - リフレッシュトークンからの ID トークン取得（get_id_token）。
    - モジュールレベルのトークンキャッシュを実装し、ページネーション間で共有。
    - 401 受信時に自動で1回トークンをリフレッシュして再試行。
  - レート制御 / リトライ:
    - 固定間隔スロットリング（120 req/min）を守る _RateLimiter 実装。
    - ネットワークエラー/HTTP 408/429/5xx に対する指数バックオフ付きリトライ（最大 3 回）。429 の場合は Retry-After を優先。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar は ON CONFLICT による更新で冪等性を確保。
    - 保存時に fetched_at を UTC ISO8601 で記録（Look-ahead bias のトレースに寄与）。
  - ユーティリティ:
    - 安全な型変換ユーティリティ _to_float / _to_int（不正な値は None に）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集と DuckDB への保存機能を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - URL スキーム検証（http/https のみ許可）とプライベートアドレス判定による SSRF 防止。
    - リダイレクト検査用のカスタムハンドラ（_SSRFBlockRedirectHandler）。
    - レスポンス受信バイト数の上限（MAX_RESPONSE_BYTES = 10MB）・gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding の扱い、Content-Length の事前チェック。
  - 正規化と前処理:
    - URL 正規化（小文字化、トラッキングパラメータ（utm_* 等）削除、フラグメント削除、クエリソート）。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）。
    - pubDate のパースと UTC への正規化（パース失敗時は現在時刻を代替）。
  - DB 保存:
    - save_raw_news：チャンク化（_INSERT_CHUNK_SIZE）して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、新規挿入IDを正確に取得。
    - save_news_symbols / _save_news_symbols_bulk：news_symbols テーブルへの紐付けをトランザクション内でチャンク挿入。
  - 銘柄コード抽出:
    - テキストから 4桁数字を抽出し、known_codes によるフィルタリング（重複除去）。
  - 統合ジョブ:
    - run_news_collection：複数 RSS ソースを独立して取得・保存し、必要に応じて銘柄紐付けを実行（個々のソースで失敗しても他ソースは継続）。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - DataSchema.md に基づく多層スキーマを追加（Raw / Processed / Feature / Execution レイヤー）。
  - 主要なテーブルを定義:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）を適用。
  - インデックス（頻出クエリに合わせたインデックス）を生成。
  - init_schema(db_path) によりディレクトリ作成、テーブル/インデックス作成を行って DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB へ接続可能。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult データクラスを提供し、ETL 実行結果（取得件数、保存件数、品質チェック、エラー等）を構造化して返却可能。
  - DB 存在／最大日付取得ユーティリティ（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダー補助: _adjust_to_trading_day（非営業日の場合に過去方向で最も近い営業日に調整）。
  - 差分更新の方針を実装:
    - run_prices_etl：差分更新ロジック（最終取得日 - backfill_days の考慮）、id_token 注入対応、jq.fetch_daily_quotes と jq.save_daily_quotes を利用して取得→保存を実行。
    - デフォルトの backfill_days は 3 日、データ開始日（_MIN_DATA_DATE）は 2017-01-01。
  - 品質チェックフローのためのフック用意（quality モジュールとの連携を想定）。

Security
- XML パースに defusedxml を使用。
- RSS フェッチでの SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト検査）。
- レスポンスサイズ上限、gzip 解凍後サイズ検査によりメモリ DoS に対処。
- URL 正規化でトラッキングパラメータ除去（プライバシー・冪等性の改善）。

Reliability / Robustness
- API クライアントでのレート制御・リトライ・トークン自動リフレッシュの導入により安定性を向上。
- DuckDB への書き込みは冪等（ON CONFLICT DO UPDATE / DO NOTHING）で結果の一貫性を維持。
- ニュース収集の保存はトランザクション化・チャンク挿入で障害時のロールバックとパフォーマンスを両立。
- ページネーション処理で pagination_key の重複チェックを行い無限ループを回避。

Notes / Known issues / TODO
- run_prices_etl の最後の return がソース内で不完全（コードの末尾が切れているように見える）。期待される戻り値は (fetched_count, saved_count) のタプルと推測されるため、呼び出し側・実装の確認が必要。
- strategy/, execution/, monitoring/ はスタブ（未実装）。実際の取引ロジックや監視・実行フローは今後追加予定。
- quality モジュール参照があるが本リポジトリ内に未提供（外部/別ファイルでの提供を想定）。
- 単体テスト用フックは一部実装済み（例: news_collector._urlopen をモック可能）だが、全面的なテストカバレッジは要整備。

Breaking Changes
- 初回リリースのため該当なし。

Changed / Fixed / Removed / Deprecated
- 初回リリースのため該当なし。

謝辞・参考
- J-Quants API（データ取得）、DuckDB（ローカルデータベース）を利用する設計。
- DataPlatform.md / DataSchema.md に基づく設計方針をコード内コメントで参照。

もしこの CHANGELOG をリリースノート用途で公開する場合、run_prices_etl の戻り値不整合や未実装モジュールの注記を README や Issue に追記することを推奨します。変更点や補足の表現を調整したい場合は指示をください。