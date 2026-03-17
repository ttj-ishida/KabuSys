CHANGELOG
=========
All notable changes to this project will be documented in this file.

このファイルは "Keep a Changelog" の形式に準拠しています。  
各リリースでの追加、変更、修正、セキュリティ関連の項目を日本語で記載しています。

Unreleased
----------
- 既知の問題
  - run_prices_etl の実装において戻り値のタプルが不完全（末尾がカンマのみで片方の値が欠けている）ため、呼び出し元でのアンパック時に例外が発生する可能性があります。修正予定（戻り値を (fetched_count, saved_count) の形式で確実に返す）。
- 今後予定
  - ETL パイプラインの追加ジョブ（financials/calendar の差分ETL等）の完成と統合テスト強化。
  - より詳細な品質チェックルールの追加とレポーティング強化。

0.1.0 - 2026-03-17
-----------------

Added
- 基本パッケージ構成
  - kabusys パッケージ初期構成を追加。__version__ を 0.1.0 に設定。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を起点）を実装。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装: export プレフィックス対応、クォートされた値のバックスラッシュエスケープ対応、インラインコメント処理、上書き制御（override/protected）。
  - アプリ設定プロパティを提供（J-Quants トークン、kabu API、Slack、DB パス、環境種別・ログレベル判定用ユーティリティ等）。
  - env 値の妥当性検査（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API ベースクライアントを実装。/token/auth_refresh を用いた id_token 取得（get_id_token）。
  - レート制御（120 req/min 固定間隔スロットリング）を実装する RateLimiter。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）を実装。
  - 401 受信時はリフレッシュトークンで自動リフレッシュして 1 回リトライする仕組みを導入（無限再帰回避）。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）を実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データの fetched_at を UTC ISO 形式で保存（Look-ahead bias 対策）。
  - 型変換ユーティリティ (_to_float/_to_int) を実装し不正データに寛容に対応。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからのニュース収集パイプラインを実装（fetch_rss / save_raw_news / save_news_symbols / run_news_collection）。
  - セキュリティ対策:
    - defusedxml を使用して XML Bomb 等を防止。
    - SSRF 防止: リダイレクト時のスキーム検査、ホスト/IP のプライベートアドレス検査（_is_private_host）を実装。
    - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - HTTP リダイレクト前後での最終 URL 再検証。
  - 記事IDは URL 正規化後の SHA-256（先頭32文字）で決定し冪等性を確保（utm_* 等のトラッキングパラメータを除去）。
  - URL 正規化（スキーム・ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。
  - テキスト前処理（URL除去、空白正規化）と pubDate パース（RFC 2822 → UTC）を実装。
  - DuckDB への一括挿入はチャンク化してトランザクションで実行し、INSERT ... RETURNING を使って実際に挿入された件数を返す。
  - 銘柄コード抽出機能（4桁数字の抽出と known_codes に基づくフィルタ）を実装。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataPlatform.md に基づくスキーマを実装（Raw / Processed / Feature / Execution 層）。
  - 多数のテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - インデックス定義（頻出クエリ向け）を追加。
  - init_schema(db_path) でディレクトリ作成→テーブル/インデックス作成を行う初期化関数を提供。get_connection で既存 DB へ接続可能。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETL 実行結果を保持する ETLResult dataclass を追加（品質問題・エラーメッセージ保持、has_errors/has_quality_errors 判定、辞書化メソッドを提供）。
  - 差分更新用ユーティリティ（テーブル存在チェック、最大日付取得、営業日調整）を実装。
  - run_prices_etl の骨組みを実装（差分算出、backfill_days サポート、fetch→save の流れ）。※実装中の既知問題あり（上記参照）。
  - 設計方針として、差分更新・backfill による後出し修正吸収、品質チェックは収集継続（Fail-Fast ではない）などを明文化。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS 収集時の SSRF 対策、XML パースの安全化（defusedxml）、レスポンスサイズ制限、Gzip 解凍後サイズ検査など複数の安全対策を導入。
- 環境変数自動ロード時、既存 OS 環境変数を保護する protected セットを採用し、意図しない上書きを回避。

Migration Notes / Usage Notes
- DB 初期化:
  - 初回は schema.init_schema(settings.duckdb_path) でテーブルを作成してください。既存 DB がある場合は init_schema を実行しても冪等にスキーマが確保されます。
  - get_connection はスキーマ初期化を行わないため、初回は init_schema を呼ぶことを推奨します。
- 環境変数:
  - 必須キー: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings のプロパティ参照）。
  - 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストでの利用想定）。
- ニュース収集:
  - デフォルト RSS ソースは DEFAULT_RSS_SOURCES に定義（現時点では Yahoo Finance のビジネスカテゴリ）。
  - 記事挿入は raw_news.id を主キーとして冪等に保存されます。new_ids は新規に挿入された記事のみを返します。
- テスト性:
  - news_collector._urlopen をモックしてネットワーク呼び出しを差し替えることを想定した設計。

著者注（コードからの推測）
- 本 CHANGELOG はソースコードと docstring から推測して作成しています。未実装/未完成の機能（例: run_prices_etl の戻り値整備や pipeline の追加ジョブ等）は将来のリリースで補完される見込みです。必要であれば、優先的に修正・追加すべき箇所のプルリクエスト案を作成できます。