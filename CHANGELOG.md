CHANGELOG
=========

すべての重要な変更履歴をここに記載します。本ファイルは "Keep a Changelog" の形式に準拠します。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-17
------------------

Added
- パッケージ基盤
  - 新規パッケージ kabusys を追加。トップレベルの __all__ に data, strategy, execution, monitoring を公開。
  - バージョンを 0.1.0 に設定。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読込する仕組みを実装（プロジェクトルートを .git / pyproject.toml で探索）。
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。
  - .env パーサを実装。export KEY=val 形式、シングル/ダブルクォートのエスケープ処理、インラインコメント処理等に対応。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き許可）。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス 等のプロパティを提供。必須キー未設定時は ValueError を送出。
  - KABUSYS_ENV / LOG_LEVEL の検証（許可値チェック）および is_live / is_paper / is_dev の判定を内蔵。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataSchema.md に基づく多層スキーマを実装（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層を定義。
  - features, ai_scores の Feature 層、signals, signal_queue, orders, trades, positions, portfolio_performance の Execution 層を定義。
  - 制約（PRIMARY KEY / CHECK / FOREIGN KEY）や典型クエリ向けのインデックスを設定。
  - init_schema(db_path) によりディレクトリ自動作成・DDL 実行で冪等に初期化可能。get_connection() を提供。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装（_request）。JSON デコード失敗・HTTP エラー・ネットワークエラーを考慮したリトライ（指数バックオフ、最大 3 回）を実装。
  - レート制限（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）。
  - 401 受信時はリフレッシュトークンによる id_token 自動更新を一度だけ行う仕組みを実装（無限再帰防止）。
  - get_id_token(refresh_token=None) を実装。
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar のページネーション対応取得を実装（pagination_key を使用）。
  - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装。fetched_at を UTC ISO 形式で記録し、ON CONFLICT DO UPDATE による冪等保存を実現。
  - 数値変換ユーティリティ _to_float / _to_int を実装。float 形式文字列や小数部の扱いを厳密に制御。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード収集・前処理・DB 保存の包括的モジュールを実装。
  - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。
  - URL 正規化（トラッキングパラメータ削除・クエリソート・フラグメント除去）と記事ID生成（正規化 URL の SHA-256 先頭32文字）を実装し、冪等性を確保。
  - defusedxml を使用した XML パース（XML Bomb 等への防御）。
  - SSRF 防御:
    - リクエスト前にホストがプライベートアドレスか検査（_is_private_host）。
    - リダイレクト時にスキーム／プライベートアドレスを検証するカスタム RedirectHandler を実装。
    - 許可スキームは http/https のみ。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズチェックを実装（Gzip bomb 対策）。
  - fetch_rss(url, source, timeout) で記事リストを取得。content:encoded を優先し、タイトルや本文は前処理（URL 除去、空白正規化）を行う。
  - raw_news へのバルク保存 save_raw_news(conn, articles) を実装。チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、新規挿入 ID リストを返す。トランザクションとロールバック処理あり。
  - news_symbols への紐付け保存 save_news_symbols / _save_news_symbols_bulk を実装（チャンク挿入・ON CONFLICT DO NOTHING）。
  - 銘柄コード抽出機能 extract_stock_codes(text, known_codes) を実装（4桁数字パターン、known_codes によりフィルタ）。
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30) により複数ソースを巡回して収集・保存・銘柄紐付けを実行。各ソースは独立してエラー処理され、1 ソース失敗でも他は継続。

- ETL パイプラインヘルパー（kabusys.data.pipeline）
  - ETLResult データクラスを実装し、ETL のメトリクス（取得数・保存数・品質問題・エラー等）を集約、辞書化する to_dict() を提供。
  - 差分更新ヘルパー：テーブル存在チェック、最大日付取得（_get_max_date）、市場カレンダーに基づく営業日調整（_adjust_to_trading_day）を実装。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
  - run_prices_etl(conn, target_date, id_token=None, date_from=None, backfill_days=3) を実装（差分取得、backfill による後だし修正吸収、J-Quants から取得して保存）。

Security
- 複数箇所でセキュリティ対策を講じています:
  - RSS パーサで defusedxml を利用（XML 攻撃対策）。
  - HTTP リダイレクト時のスキームとホスト検証、プライベートアドレス拒否（SSRF 対策）。
  - レスポンスサイズ制限と gzip 解凍後サイズチェック（DoS / Gzip bomb 対策）。
  - 環境変数読み込みで OS 環境変数を保護する protected キーの概念を導入。

Design / Operational notes
- 冪等性を重視:
  - DuckDB への保存は可能な限り ON CONFLICT による上書き/スキップで実装。
  - ニュース記事 ID のハッシュ化や news_symbols の ON CONFLICT により重複挿入を吸収。
- ロギングを重視:
  - 主要処理に logger による info/warning/exception を追加。
- テスト性:
  - RSS の _urlopen を置き換え可能にしてテストでモック可能。
  - 環境変数自動ロードの無効化フラグを用意。

Fixed
- （初期リリースのため該当なし）

Changed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Notes / Known limitations
- jquants_client の設計では 120 req/min の固定間隔スロットリングを採用（単一プロセス内での簡易制御）。分散実行時は別途レート管理が必要になる可能性があります。
- quality モジュール（品質チェック）への依存があるが、品質チェック自体の実装や完全な動作は外部モジュールに依存します。品質問題検出は ETL を中断せず収集する方針です。

---- 

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時はプロジェクト管理上の変更やマイナー修正などを反映してください。