CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。
なお、このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初期リリース: KabuSys 日本株自動売買システムの骨組みを実装。
  - パッケージ初期化:
    - src/kabusys/__init__.py にバージョン (0.1.0) とエクスポートモジュール一覧を追加。

- 環境設定管理:
  - src/kabusys/config.py
    - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - .env パーサ実装: export プレフィックス、クォート処理、インラインコメント判定などに対応。
    - 環境変数保護（既存 OS 環境変数を上書きしない・protect set）をサポート。
    - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / システム設定をプロパティ経由で取得。
    - 値検証: KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装。
    - duckdb/sqlite のデフォルトパスを設定し Path.expanduser に対応。

- データ取得クライアント（J-Quants）:
  - src/kabusys/data/jquants_client.py
    - J-Quants API からの日次株価（OHLCV）、財務（四半期 BS/PL）、市場カレンダー取得を実装。
    - レート制御: 固定間隔スロットリング (_RateLimiter) による 120 req/min 制限を実装。
    - リトライ: 指数バックオフによるリトライ（最大 3 回）、対象ステータス (408, 429, 5xx) をサポート。
    - 401 応答時はトークン自動リフレッシュ（1 回のみ）して再試行するロジックを実装。
    - ページネーション対応: pagination_key を用いたページ取得の繰り返し処理を実装。
    - 取得時刻（fetched_at）を UTC で記録し Look-ahead bias のトレースを容易に。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT DO UPDATE による冪等保存を実現。
    - データ型変換ユーティリティ (_to_float, _to_int) を実装し空値・不正値に対して安全に None を返す処理を導入。
    - get_id_token によるリフレッシュトークン→IDトークン取得（POST）を実装。モジュールレベルのトークンキャッシュを保持。

- ニュース収集（RSS）:
  - src/kabusys/data/news_collector.py
    - RSS フィードからの記事収集および DuckDB への保存機能を実装。
    - セキュリティ対策:
      - defusedxml を用いた XML パースで XML Bomb 等に対処。
      - URL スキーム検証（http/https のみ許可）と、ホストがプライベート/ループバック/リンクローカルでないことの検査による SSRF 防止。
      - リダイレクト時にもスキームとホストを検査する専用 RedirectHandler を導入。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定し、受信サイズ超過や gzip 解凍後のサイズチェックを実装。
      - トラッキングパラメータ（utm_* など）を除去して URL 正規化・SHA-256（先頭32文字）で記事IDを生成し冪等性を保証。
    - 信頼性:
      - gzip 圧縮対応、Content-Length の事前チェック、XML パース失敗時は警告ログでスキップ。
      - _urlopen を分離してテスト時にモック可能に設計。
    - DB 保存:
      - save_raw_news: チャンク化（_INSERT_CHUNK_SIZE）して INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、新規挿入された記事IDのみを返す。
      - save_news_symbols / _save_news_symbols_bulk: 記事–銘柄の紐付けをチャンクINSERTかつ RETURNING により正確にカウントして保存。
      - トランザクション管理（begin/commit/rollback）と例外ログ出力を実装。
    - 文章処理:
      - preprocess_text による URL 除去・空白正規化。
      - 公開日時パース（_parse_rss_datetime）は RFC 2822 を想定し、失敗時は代替で現在時刻を使用。
      - 銘柄抽出: 4 桁数字パターンから既知コードセットと照合して重複排除したリストを返す extract_stock_codes。
    - デフォルト RSS ソース定義（Yahoo Finance のビジネスカテゴリ）を提供。

- スキーマ管理（DuckDB）:
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution の 3 層+実行レイヤを含む一連の DDL を定義。
    - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤ。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed レイヤ。
    - features, ai_scores など Feature レイヤ。
    - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution レイヤ。
    - 各テーブルに適切な型・制約（CHECK / PRIMARY KEY / FOREIGN KEY）を付与。
    - インデックス定義（頻出クエリ想定）を追加。
    - init_schema(db_path) によりディレクトリ作成、全テーブル・インデックスの作成を行う冪等な初期化関数を実装。
    - get_connection(db_path) による接続取得関数を提供（初期化は行わない旨をドキュメント化）。

- ETL パイプライン:
  - src/kabusys/data/pipeline.py
    - ETL の設計に沿った差分取得・保存のヘルパとジョブを実装する土台を追加。
    - ETLResult データクラスを導入し、取得数・保存数・品質問題・エラーを集約して返却。
    - テーブル存在チェック・最大日付取得ユーティリティ (_table_exists / _get_max_date) を実装。
    - 市場カレンダーに基づく営業日調整ヘルパ (_adjust_to_trading_day) を実装。
    - 差分更新ヘルパ: get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
    - run_prices_etl: 差分ロジック（最終取得日から backfill_days を遡る、初回は _MIN_DATA_DATE から）に基づき jquants_client を呼び出して取得・保存を行う。id_token を注入可能にしてテスト容易性を確保。
    - ETL は品質チェックモジュール（quality）と連携する想定の設計を組み込み（品質チェックはエラーでも ETL を継続する方針）。

Logging / Observability
- 主要処理箇所に logger を設置し、フェッチ件数・保存件数・警告・例外の情報を出力するように実装。

Security
- RSS パーサで defusedxml を使用、SSRF や XML Bomb、巨大レスポンスへ対策を盛り込んでいる点を強調。
- 環境変数の読み込みにおいて OS 既存の値を保護する挙動を実装。

Notes / Design decisions
- 冪等性を重視:
  - DuckDB への挿入は ON CONFLICT を多用して上書きもしくはスキップにより冪等化。
  - ニュースは URL 正規化＋SHA-256 ハッシュで記事IDを生成して重複挿入を防止。
- API リクエストは固定間隔スロットリングで簡潔にレート制御（120 req/min）を実装。
- id_token のキャッシュと自動リフレッシュでページネーションや継続取得に対応。
- テストしやすさ:
  - _urlopen の差し替え、id_token 注入、公開ユーティリティの設計により単体テストが容易。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Security
- RSS 関連の SSRF / XML Bomb / Gzip bomb 対策を実装。

参考
- 実装箇所の主要モジュール:
  - kabusys.config
  - kabusys.data.jquants_client
  - kabusys.data.news_collector
  - kabusys.data.schema
  - kabusys.data.pipeline

今後の見込み（例）
- quality モジュールの実装強化（欠損・スパイク検出ルールの具体化）。
- execution モジュール（kabu ステーションとの発注連携・約定処理）の実装。
- strategy 層・monitoring 層の具体的なロジック実装。