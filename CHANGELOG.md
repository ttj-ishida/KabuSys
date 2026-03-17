KEEP A CHANGELOG
=================

すべての重要な変更を時系列で記録します。フォーマットは "Keep a Changelog" に準拠します。

[unreleased]: https://example.com/kabusys/compare/0.1.0...HEAD

リリース
-------

### [0.1.0] - 2026-03-17

初回リリース。日本株自動売買基盤「KabuSys」のコアモジュール群を追加しました。主な追加点・設計方針は以下のとおりです。

Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージのバージョンと公開モジュール（data, strategy, execution, monitoring）を定義。
- 環境・設定管理
  - src/kabusys/config.py
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みする仕組みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - OS環境変数を保護する protected 機能と override 挙動を提供。
    - Settings クラスを追加し、J-Quants / kabu / Slack / DB パスなどの設定取得プロパティ（バリデーション付き）を提供。
    - KABUSYS_ENV と LOG_LEVEL の検証を行い、不正値は例外を投げる。
- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - API 呼び出しのための共通 _request を実装（JSON デコード検査、最大リトライ、指数バックオフ、Retry-After 優先）。
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回だけリトライする仕組み。
    - ページネーション対応（pagination_key）の fetch_* 系関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（四半期財務）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB へ冪等に保存する save_* 関数:
      - save_daily_quotes / save_financial_statements / save_market_calendar
      - INSERT ... ON CONFLICT DO UPDATE を用いて重複を排除し、fetched_at を UTC で記録（Look-ahead bias 対策）。
    - 型変換ユーティリティ _to_float / _to_int（堅牢な空値・不正値処理）。
- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィード収集（DEFAULT_RSS_SOURCES に Yahoo 等を追加）と記事整形ロジックを実装。
    - defusedxml を用いた安全な XML パース（XML Bomb 対策）。
    - SSRF 対策:
      - fetch 前のホスト/IP の事前検査、
      - リダイレクト時のスキーム・ホスト検証を行うカスタムハンドラ（_SSRFBlockRedirectHandler）。
      - private/loopback/リンクローカル/マルチキャスト宛のアクセスを拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検査（Gzip bomb 対策）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事ID生成（正規化 URL の SHA-256 先頭32文字）で冪等性を確保。
    - テキスト前処理（URL 除去・空白正規化）。
    - extract_stock_codes による本文からの銘柄コード抽出（4桁数字、既知コードセットフィルタ）。
    - DB 保存機能（DuckDB）:
      - save_raw_news: INSERT ... RETURNING id を用いて実際に挿入された記事IDを返す。チャンク挿入・1トランザクションで処理。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄紐付けを一括で挿入（ON CONFLICT DO NOTHING、INSERT ... RETURNING で正確に挿入数を算出）。
- DuckDB スキーマ定義・初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution の多層スキーマを DDL で定義。
    - raw_prices, raw_financials, raw_news, raw_executions を含む Raw 層。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層。
    - features, ai_scores などの Feature 層。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層。
    - 頻出クエリ向けのインデックスを定義。
    - init_schema(db_path) によりファイルパスの親ディレクトリ自動作成と DDL 実行を行い、接続を返す（冪等化）。
    - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）。
- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py
    - ETLResult データクラス（品質検査結果・エラー等を集約）を追加。
    - テーブル存在チェック・最大日付取得ユーティリティ（_table_exists, _get_max_date）。
    - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）。
    - 差分更新ヘルパー: get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - run_prices_etl: 差分ロジック（最終取得日からの backfill_days による再取得）、J-Quants からの取得と保存の呼び出し、ログ出力。バックフィルのデフォルトは 3 日。

Changed
- 設計上の方針・注意点をモジュール上の docstring と関数 docstring に明記（API レート制限、リトライ方針、Look-ahead bias 対策、冪等性など）。これにより実運用・監査向けのトレーサビリティを強化。

Security
- ニュース収集周りで SSRF/XXE/XML Bomb/メモリ DoS 対策を導入:
  - defusedxml の使用、リダイレクト時の事前検査、private IP 判定、レスポンス上限の導入、gzip 解凍後サイズ検査等。

Notes / Implementation details
- HTTP リトライ:
  - 対象ステータスは 408, 429, および 5xx。429 の場合は Retry-After ヘッダを優先して待機時間を決定。
  - 最大リトライ回数は 3 回（指数バックオフ基数 2.0）。
  - 401 は id_token リフレッシュを試みて 1 回だけ再試行（無限再帰防止のため allow_refresh フラグあり）。
- レート制限:
  - 120 req/min を想定し、最小間隔を 60/120 秒で固定スロットリング。
- DB 保存は可能な限り冪等化（ON CONFLICT DO UPDATE / DO NOTHING、RETURNING を活用）して再実行や二重実行に強く設計。

今後の TODO / 想定追加
- strategy / execution / monitoring の具体的実装（現在はパッケージエントリのみ）。
- quality モジュールの実装呼び出し（pipeline.py で参照されるが詳細ロジックは外部）。
- ETL の単体・統合テスト、そして CI ワークフローへの組み込み。
- 操作性向上のための CLI や cron/スケジューラ統合。

Authors
- KabuSys 開発チーム（コードベースから推測して自動生成）。

[0.1.0]: https://example.com/kabusys/releases/tag/v0.1.0