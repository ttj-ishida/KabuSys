CHANGELOG
=========

すべての変更は Keep a Changelog に準拠して記載しています。
このプロジェクトはセマンティックバージョニングを採用しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-18
-------------------

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下の通りです。

Added
- パッケージ基礎
  - パッケージメタ情報: kabusys.__init__.py（__version__ = "0.1.0"）を追加。
  - パッケージ構成: data, strategy, execution, monitoring サブパッケージを公開。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機能を導入。
    - プロジェクトルートは .git または pyproject.toml を基準に自動探索。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - 読み込み順: OS 環境変数 > .env.local > .env（.env.local は上書き）。
  - .env のパース実装:
    - export KEY=val 形式に対応、クォートやエスケープ、インラインコメントの処理、コメントの扱いに配慮。
  - Settings クラスを提供し、アプリケーションで利用する設定値をプロパティ経由で安全に取得可能:
    - J-Quants（JQUANTS_REFRESH_TOKEN）、kabu API（KABU_API_PASSWORD, KABU_API_BASE_URL）、Slack（SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）、DB パス（DUCKDB_PATH, SQLITE_PATH）など。
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証を実装。
    - is_live / is_paper / is_dev の便利プロパティを追加。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ _request を実装:
    - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter を導入。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。リトライ対象は 408/429/5xx。
    - 401 受信時は自動で refresh（1 回のみ）して再試行。再帰を防ぐため allow_refresh オプションを実装。
    - ページネーション対応（pagination_key）のループ処理を提供。
    - JSON デコード失敗時のエラーハンドリング。
  - 認証補助: get_id_token(refresh_token=None) を実装（POST /token/auth_refresh）。
  - データ取得関数を追加:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
    - 取得時に fetched_at を記録する方針（Look-ahead Bias 対策、設計に明記）。
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes → raw_prices テーブルへ保存（PK 欠損行のスキップ・ログ出力含む）
    - save_financial_statements → raw_financials テーブルへ保存
    - save_market_calendar → market_calendar テーブルへ保存（holidayDivision の解釈を反映）
  - モジュールレベルの ID トークンキャッシュを実装し、ページネーション間で再利用。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュースを安全に収集・整形して保存する機能を実装。
    - defusedxml を用いた XML パースで XML Bomb 等の攻撃対策。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームおよびプライベート/ループバック/リンクローカルアドレスへの到達を防ぐカスタム RedirectHandler を導入。
      - 初回および最終 URL に対するホストのプライベート判定。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入し、Content-Length チェックと読み込みバイト数チェックでメモリ DoS を抑制。gzip 解凍後のサイズも検査。
    - 記事 ID は URL 正規化（トラッキングパラメータ除去、クエリソート、fragment 削除）後の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保。
    - テキスト前処理（URL 除去・空白正規化）を実装。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いたチャンク挿入（トランザクションでまとめる）により挿入された新規記事 ID を返す。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの一括保存。重複除去・チャンク処理・RETURNING による正確な挿入数カウント。
    - 銘柄コード抽出: extract_stock_codes（テキスト内の4桁数字を known_codes に照合して抽出）。
    - run_news_collection: 複数ソースの収集を一括実行。各ソースは独立してエラーハンドリング（1 ソース失敗でも他は継続）。既知銘柄が与えられた場合は新規記事に対して銘柄紐付けを行う。

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層に対応したテーブル定義（DDL）を実装。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）を定義し、頻出クエリ向けのインデックスを作成。
  - init_schema(db_path) を実装。db_path の親ディレクトリ自動作成、全テーブル／インデックスの作成（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass を導入し、ETL 実行結果（取得数・保存数・品質問題・エラー）を表現。
  - 差分更新のためのユーティリティを実装:
    - _table_exists, _get_max_date（任意テーブルの最大日付取得）
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _adjust_to_trading_day: 非営業日調整（market_calendar に基づく）
  - run_prices_etl を実装（差分取得ロジック、backfill_days による再取得、J-Quants からの取得→保存の流れ）。品質チェックモジュールへの接続ポイントを設計（quality モジュール参照、重大度フラグ処理）。

- テスト・拡張性のための設計
  - news_collector._urlopen はテストからモック可能な形で実装。
  - jquants_client の retry/refresh ロジックや token キャッシュ、pipeline の id_token 注入など、ユニットテスト容易性を考慮。

Security
- defusedxml による XML パース、SSRF 対策、レスポンスサイズ制限などセキュリティ面を考慮した実装を多数導入。

Changed
- 初回リリースのため該当なし（新機能の追加のみ）。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Notes / Caveats
- run_prices_etl の戻り値や pipeline 実装は将来的に他の ETL ジョブ（財務データ・カレンダー等）と統一される予定。
- DuckDB スキーマの制約やインデックスは実運用に合わせて調整されることを想定。
- 実際の運用では環境変数（特にトークンやパスワード）の取り扱いに注意してください（.env の管理、OS 環境変数の保護など）。

--- 

今後の予定（例）
- ETL の追加ジョブ（financials/calendar の差分 ETL の完結実装）。
- strategy / execution / monitoring パッケージの実装（発注ロジック、ポジション監視、Slack 通知等）。
- quality モジュールによる詳細な品質チェックと自動アラート機能の整備。