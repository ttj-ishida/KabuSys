CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠しています。
このファイルはコードベース（src/kabusys 以下）の内容から推測して作成しています。

[Unreleased]
-------------
- Known issues:
  - data.pipeline.run_prices_etl の戻り値処理に不整合があり（len(records), のように保存済み件数 saved を含めないまま関数が終わっている箇所が見受けられます）。実際の利用時は戻り値の修正（取得件数と保存件数を返す）が必要です。
- Notes:
  - strategy/ と execution/ のパッケージ初期化ファイルはプレースホルダ（空）です。戦略ロジックや発注実装は今後追加される想定です。

[0.1.0] - 2026-03-18
--------------------
Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
    - __all__ に data, strategy, execution, monitoring を公開。
- 設定管理:
  - src/kabusys/config.py
    - .env ファイルおよび環境変数からの設定読み込みを自動化（優先順位: OS 環境変数 > .env.local > .env）。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）によりカレントディレクトリに依存しない読み込み。
    - .env パース実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグ（テスト向け）。
    - Settings クラスを提供し、必須環境変数のチェック（_require）、値検証（KABUSYS_ENV, LOG_LEVEL）とデフォルト値（KABU_API_BASE_URL, DB パス等）を実装。
    - duckdb_path / sqlite_path の Path 正規化をサポート。
- J-Quants API クライアント:
  - src/kabusys/data/jquants_client.py
    - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得用 API ラッパーを実装。
    - レート制限制御（_RateLimiter）: デフォルト 120 req/min、固定間隔スロットリング。
    - 再試行ロジック: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx をリトライ対象に設定。429 の Retry-After を尊重。
    - 401 Unauthorized 受信時はリフレッシュトークンから id_token を自動更新して最大 1 回リトライ。
    - ページネーション対応（pagination_key を用いた繰り返し取得）。
    - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を提供。いずれも冪等（ON CONFLICT DO UPDATE）での保存を実現。
    - データ取得時に fetched_at を UTC（ISO8601, Z）で記録して Look-ahead Bias のトレースを可能に。
    - 型変換ユーティリティ (_to_float, _to_int) を追加。
    - id_token のキャッシュとテスト容易性のため id_token を注入可能に設計。
- ニュース収集モジュール:
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュース記事を収集し raw_news / news_symbols テーブルに保存する一連の機能を実装。
    - セキュリティ対策:
      - defusedxml を利用して XML BOM / XML Bomb を防止。
      - SSRF 対策: リダイレクト時にスキームとホストの検証を行う _SSRFBlockRedirectHandler、初回ホスト事前検証、プライベートアドレス（ループバック/プライベート/リンクローカル/マルチキャスト）拒否。
      - URL スキーム検証（http/https のみ許可）。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - データ整形:
      - _normalize_url による URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
      - 記事ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成（冪等性確保）。
      - テキスト前処理（URL 除去・空白正規化）。
      - pubDate の RFC2822 パースおよび UTC 変換（パース失敗時は現在時刻で代替）。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用いて新規挿入 ID を返す。チャンク処理と単一トランザクションでのコミット。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols の一括保存（ON CONFLICT DO NOTHING + RETURNING 1）とトランザクション管理。
    - 銘柄抽出:
      - extract_stock_codes: テキスト中の 4 桁数字候補を正規表現で抽出し、known_codes に含まれるもののみ返す（重複除去）。
    - fetch_rss: リダイレクト後の最終 URL 再検証、Content-Length の事前チェック、gzip 解凍処理、XML パースと item 解析を行う。
    - DEFAULT_RSS_SOURCES に Yahoo Finance のビジネスカテゴリ RSS を初期値として定義。
    - HTTP オープン処理 (_urlopen) を差し替え可能にしてテスト時にモック可能。
- DuckDB スキーマ定義:
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution 各レイヤーのテーブル定義を作成（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
    - カラム制約（NOT NULL、CHECK 制約、外部キー）を設定してデータ整合性を担保。
    - 頻出クエリ向けのインデックスを用意（code×date 検索や status 検索など）。
    - init_schema(db_path) を提供: 親ディレクトリ自動作成、DDL の冪等実行、インデックス作成。
    - get_connection(db_path) を提供（スキーマ初期化は行わない）。
- ETL パイプライン:
  - src/kabusys/data/pipeline.py
    - 差分更新とバックフィル（backfill_days デフォルト 3 日）に基づく ETL ワークフローの土台を実装。
    - ETLResult dataclass を定義し、取得件数、保存件数、品質問題（quality.QualityIssue を想定）、発生エラーを収集して返却可能。
    - DB 上の最終日取得ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）を実装。
    - 市場カレンダーを用いた営業日調整機能 (_adjust_to_trading_day) を提供（最長 30 日遡りで直近営業日へ調整）。
    - run_prices_etl: 差分取得ロジック（date_from 未指定時は最終取得日 - backfill_days + 1 から再取得、最小取得日 MIN_DATA_DATE=2017-01-01）と jquants_client 経由での取得・保存の流れを実装。id_token を注入可能にしてテスト容易性を確保。
- テスト/開発支援:
  - _urlopen や id_token の注入ポイントなど、外部依存をモックしやすい設計を一部に導入。
- ロギング:
  - 各モジュールで logger を使用し、重要な操作（取得件数、保存件数、スキップ件数、警告）を出力。

Changed
- N/A（初回リリースのため変更履歴なし）

Fixed
- N/A（初回リリースのため修正履歴なし）

Removed
- N/A

Security
- ニュース収集部で以下のセキュリティ対策を導入:
  - defusedxml による XML パース（XML ベース攻撃対策）
  - SSRF 対策（プライベートアドレス拒否、リダイレクト検査）
  - レスポンスサイズ制限と gzip 解凍後の検査（リソース枯渇攻撃対策）
  - URL スキーム制限（http/https のみ許可）

Notes / TODO
- run_prices_etl の戻り値周りの不整合を修正する必要があります（現在は取得件数のみを返すように見える）。
- strategy/ と execution/ は未実装（パッケージプレースホルダ）。実運用のためには戦略算出ロジック、シグナル生成、注文送信・状態管理を実装してください。
- quality モジュールに関する参照は pipeline で行われていますが、quality の実装が本コードからは見えないため、品質チェックルールの実装・統合が必要です。
- DuckDB の型・制約は厳密に定義しているため、外部データの整形・バリデーションを注意深く行うこと（例: _to_int/_to_float の挙動を理解して使うこと）。

References
- 実装に言及しているドキュメント/設計（コードコメント内）:
  - DataPlatform.md, DataSchema.md（コードコメント参照）

--- End of CHANGELOG ---