Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

記載方針:
- 変更は利用者に有益な観点（新機能、修正、セキュリティ、互換性等）でまとめています。
- 実装内容はソースコードから推測して記載しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-17
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのベース実装を追加。
  - パッケージエントリポイント: kabusys.__version__ = "0.1.0"、公開サブパッケージ: data, strategy, execution, monitoring をエクスポート。
- 環境設定管理 (kabusys.config)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは以下をサポート:
    - 行頭の "export " プレフィックス
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - インラインコメント（クォート外で、直前が空白/タブの '#' をコメントとみなす）
  - 環境変数の必須チェック（_require）と Settings クラスを提供。既定値とバリデーション:
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト
    - KABUSYS_ENV 値検証 (development/paper_trading/live)
    - LOG_LEVEL 値検証 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - settings オブジェクトを公開（アプリから直接利用可能）。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装（_request）。
    - レート制御: 固定間隔スロットリングで 120 req/min を遵守（_RateLimiter）。
    - 再試行ロジック: 指数バックオフ、最大試行回数 3 回、HTTP 408/429 と 5xx を対象。
    - 401 Unauthorized を検出した場合、リフレッシュトークンで id_token を自動更新して 1 回だけリトライ。
    - ページネーション対応（pagination_key を利用）。
    - JSON デコードエラーの検出と明確な例外メッセージ。
  - id_token のキャッシュ（モジュールレベル）を導入しページネーション間で共有。
  - 提供 API:
    - get_id_token(refresh_token=None)
    - fetch_daily_quotes(...): OHLCV をページングで取得
    - fetch_financial_statements(...): 四半期 BS/PL をページングで取得
    - fetch_market_calendar(...): JPX マーケットカレンダー取得
    - save_daily_quotes(conn, records): DuckDB raw_prices に冪等保存（ON CONFLICT DO UPDATE）
    - save_financial_statements(conn, records): raw_financials に冪等保存
    - save_market_calendar(conn, records): market_calendar に冪等保存
  - データ保存時に fetched_at を UTC ISO フォーマットで記録（Look-ahead Bias 対策）。
  - 値変換ユーティリティ: _to_float/_to_int（不正値は None、int 変換の端数処理を安全に実装）。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して DuckDB の raw_news に保存する処理を実装。
  - 設計/実装の特徴:
    - デフォルトソース: Yahoo Finance のビジネス RSS。
    - defusedxml を使用して XML 関連の脆弱性を軽減。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - リダイレクト時にスキームとホストを検査するカスタムハンドラ (_SSRFBlockRedirectHandler)
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストなら拒否（DNS 解決後に A/AAAA を検査）
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - URL 正規化（小文字化、トラッキングクエリパラメータの除去、フラグメント除去、クエリのソート）。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成 → 冪等性確保。
    - テキスト前処理: URL 除去、空白正規化、先頭末尾トリム。
    - DB 保存はチャンク化して 1 トランザクションで実行、INSERT ... RETURNING により挿入された ID を正確に返す。
    - 銘柄抽出: 正規表現で 4 桁数字を抽出し known_codes に存在するものだけを返す。
  - 提供 API:
    - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
    - save_raw_news(conn, articles) -> list[str]（新規挿入された記事ID）
    - save_news_symbols(conn, news_id, codes) -> int
    - run_news_collection(conn, sources=None, known_codes=None, timeout=30) -> dict[source_name, new_count]
- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataSchema.md に基づくデータベーススキーマを定義・初期化するモジュールを追加。
  - 3 層構造（Raw / Processed / Feature）＋ Execution レイヤーのテーブルを定義:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK、外部キー）やインデックスを定義。
  - init_schema(db_path) でディレクトリ作成を含めてテーブル/インデックスを冪等に作成して DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。
- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新ベースの ETL パイプライン基盤を追加。
  - 設計/機能:
    - 差分更新のための最終取得日取得ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - 営業日調整ヘルパー: 非営業日の場合に直近の営業日に調整するロジック（_adjust_to_trading_day）。
    - ETLResult データクラス: ETL 実行結果、品質問題、エラー一覧を保持。品質問題の重大度判定や辞書化 to_dict をサポート。
    - run_prices_etl の差分更新ロジック（backfill_days による再取得、デフォルトバックフィル 3 日、最小データ開始日あり）。
    - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）などの定数。
    - 品質チェックモジュール（kabusys.data.quality を利用する想定）との統合点を設ける設計。
  - ETL は id_token を注入可能にしてテスト容易性を確保。

Security
- RSS / XML パースに defusedxml を採用し XML ベースの攻撃（XML Bomb 等）に対処。
- HTTP レスポンスサイズ上限・gzip 解凍後のサイズ検査によりメモリ DoS を防止。
- SSRF 対策を多層で実装（スキーム検査、プライベート IP 検査、リダイレクト時の再検査）。
- J-Quants API クライアントでタイムアウトやリトライ制御を実装し、DoS/レート超過を軽減。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Notes / 開発者向け補足
- DuckDB への INSERT 文は ON CONFLICT を利用して冪等性を担保しているため、再実行しても重複が蓄積されない設計です（raw_prices, raw_financials, market_calendar, raw_news / news_symbols 等）。
- settings.jquants_refresh_token 等は必須項目として _require により未設定時に ValueError を投げます。CI/運用環境では必ず環境変数を設定してください。
- news_collector の run_news_collection は各ソースを独立して処理し、1 ソースの失敗が他へ波及しないようにしています。known_codes を渡すことで記事と銘柄の紐付けを自動実行します。
- jquants_client の再試行/トークンリフレッシュはデフォルト設定だと最大 3 回まで行います。429 応答時は Retry-After ヘッダを優先して待機します。
- init_schema は ":memory:" をサポートし、ファイル DB の場合は親ディレクトリを自動作成します。

今後の予定（予定機能）
- strategy / execution / monitoring パッケージ内のアルゴリズム・発注実装の追加
- quality モジュールの具体的なチェック実装と ETL の統合強化
- 単体テスト・統合テストの追加（ネットワーク依存箇所のモック化等）
- メトリクス / モニタリング向けのログ拡張と Slack 通知等の導入

注記: 本 CHANGELOG は提供されたソースコードに基づき推測して作成しています。実際のリリースノートとして公開する場合は、さらにレビュー・追記してください。