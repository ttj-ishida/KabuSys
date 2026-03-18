CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録しています。
このファイルはプロジェクトのリリース履歴と主要な機能追加・修正・既知の問題を把握するためのものです。

[0.1.0] - 2026-03-18
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - src/kabusys/__init__.py にてバージョンを "0.1.0" として公開し、主要サブパッケージを __all__ でエクスポート。

- 環境・設定管理（src/kabusys/config.py）
  - .env / .env.local からの自動読み込み機能を実装（優先度: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探索して決定（配布後も安定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途）。
  - .env のパースは export プレフィックス、クォート文字、インラインコメント、エスケープシーケンス等に対応。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）などをプロパティ経由で提供。
  - 必須環境変数未設定時は ValueError を送出する _require を提供。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値一覧あり）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数群を実装（ページネーション対応）。
  - API レート制御: 固定間隔スロットリングによる RateLimiter を実装（デフォルト 120 req/min）。
  - リトライロジック: 指数バックオフ（base=2.0）、最大試行回数 3、ステータス 408/429/5xx に対する再試行、429 の場合は Retry-After ヘッダを優先。
  - 401 受信時は id_token を自動リフレッシュして 1 回だけ再試行（無限再帰を避けるため allow_refresh フラグ）。
  - id_token キャッシュ（モジュールレベル）を保持し、ページネーション間で共有。
  - DuckDB への保存関数 save_* を実装。ON CONFLICT DO UPDATE により冪等性を担保し fetched_at を記録。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し不正値を安全に扱う。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news へ保存する処理を実装（DEFAULT_RSS_SOURCES に Yahoo Finance のカテゴリ RSS を追加）。
  - XML パースは defusedxml を利用して XML Bomb 等の攻撃を緩和。
  - SSRF 対策:
    - fetch 時に URL スキーム検証（http/https のみ許可）。
    - リダイレクト検査用の _SSRFBlockRedirectHandler を導入し、リダイレクト先のスキームとプライベートアドレスをブロック。
    - ホスト名の DNS 解決により A/AAAA レコードをチェックし、プライベート/ループバック/リンクローカル/マルチキャストを拒否。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入し、読み込み超過や gzip 解凍後のサイズも検査（Gzip bomb 対策）。
  - URL 正規化: トラッキングパラメータ（utm_*, fbclid, gclid, ref_, _ga 等）を除去しクエリをソート。記事ID は正規化後 URL の SHA-256 の先頭32文字を使用して冪等性を保証。
  - テキスト前処理: URL 除去、空白正規化を実装。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事IDの一覧を返す（チャンク処理 & 単一トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括で保存（重複除去・チャンク・トランザクション）。
  - 銘柄コード抽出: 正規表現で 4 桁の数字を抽出し、known_codes に含まれるもののみを返すユーティリティを実装。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブルを DataSchema.md に準拠して定義。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw 層。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed 層。
  - features, ai_scores などの Feature 層。
  - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution 層。
  - 頻出クエリ向けのインデックス群を定義。
  - init_schema(db_path) で親ディレクトリの自動作成、DDL とインデックスの実行を行い初期化済み接続を返す。get_connection() で既存 DB へ接続。

- ETL パイプライン骨子（src/kabusys/data/pipeline.py）
  - ETL の設計方針と処理フロー（差分更新、保存、品質チェック）を実装。
  - ETLResult dataclass を実装し、品質問題（quality.QualityIssue）の一覧やエラー集約、辞書化を行えるようにした。
  - ヘルパー関数:
    - _table_exists, _get_max_date により DB の存在確認と最終日付取得。
    - _adjust_to_trading_day により非営業日を直近の営業日に調整（最大 30 日遡り）。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
  - run_prices_etl を実装（差分取得ロジック・backfill_days デフォルト 3、_MIN_DATA_DATE = 2017-01-01 を使用）。J-Quants クライアントを呼び出して取得→保存を行うフローを実装。

Security
- XML のパースに defusedxml を使用して外部エンティティ攻撃や XML Bomb を軽減。
- RSS フェッチ周りに多層の SSRF 対策を実装（スキーム検証、プライベートアドレスチェック、リダイレクト時の検査）。
- 外部から受信するデータのサイズ制限（10 MB）と gzip 解凍後サイズチェックを実施。

Known issues / Notes
- run_prices_etl の戻り値: 現在の実装は (fetched_count,) のように 1 要素のタプルを返してしまう箇所があり、関数注釈が期待する (int, int) と不整合です。ETL の呼び出し部分での扱いに注意が必要です（修正予定）。
- pipeline モジュールは ETLResult や個別ジョブの基礎を実装しているが、統合的な全体 ETL ワークフロー（統合実行、品質チェック呼び出し、監査ログ出力等）の完成には追加実装が必要。
- tests や CI の定義はこのリリースには含まれていません。自動テストとモックを使ったネットワークリクエストの検証を推奨します。
- news_collector の DNS 解決時に例外が発生した場合は安全側（非プライベート）とみなす挙動です。環境によっては追加の保護・設定が必要になる可能性があります。

アップグレード/移行メモ
- .env の自動ロードはデフォルトで有効です。テスト環境などで自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB 初期化は init_schema() を必ず実行してから行ってください。既存 DB に接続するだけなら get_connection() を使用してください。

今後の予定（未実装/改善予定）
- pipeline の統合実行ロジックと品質チェック（quality モジュール）連携の実装完了。
- run_prices_etl の戻り値バグ修正と単体テスト追加。
- 更なるテストカバレッジの拡充（ネットワーク/DB モックを含む）。
- Slack 通知等の監視・モニタリング連携の実装（config の Slack 設定は既に用意済み）。

--- 
この CHANGELOG はコードベースから推測して作成しています。細かな実装目的や振る舞いの追加要件がある場合は、実際の設計ドキュメントやチケットに基づいて追記してください。