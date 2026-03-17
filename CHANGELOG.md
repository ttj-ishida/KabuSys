CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。セマンティック バージョニングを使用します。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-03-17
--------------------

Added
- 初回リリース。KabuSys パッケージの基本機能を追加。
- パッケージメタ情報
  - __version__ = "0.1.0" を定義し、パッケージ API として data/strategy/execution/monitoring を公開。
- 設定管理 (kabusys.config)
  - .env / .env.local /OS 環境変数からの設定ロード機能を実装（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索して行う（配布後も安定して動作）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - 環境変数の保護（既存の OS 環境変数を上書きしない / .env.local による上書き可）をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス /環境（development/paper_trading/live）/ログレベルの取得と検証を行う。
  - 必須設定が未設定の場合は _require によって明示的な ValueError を送出。

- J-Quants クライアント (kabusys.data.jquants_client)
  - API クライアントを実装。以下の特徴を持つ:
    - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を導入。
    - リトライ: 指数バックオフで最大 3 回リトライ（対象: ネットワークエラー、HTTP 408/429/5xx）。
    - 401 時の自動トークンリフレッシュ（1 回だけ）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応で fetch_daily_quotes, fetch_financial_statements を実装。
    - fetch_market_calendar により JPX マーケットカレンダーを取得。
    - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を提供し、ON CONFLICT DO UPDATE による冪等保存を実現。
    - レスポンス JSON デコード時の例外・エラーハンドリングとログ出力を実装。
  - データ型変換ユーティリティ (_to_float / _to_int) を追加し、不正値に対して安全に None を返す設計。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を取得・整形・DuckDB に保存する一連の機能を実装。
  - セキュリティと堅牢性:
    - defusedxml を使用して XML Bomb 等の攻撃を防止。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカル/マルチキャストかを検査、リダイレクト時も検証するカスタム RedirectHandler を導入。
    - レスポンスサイズ上限（10 MB）のチェックと gzip 解凍後の再チェック（Gzip bomb 対策）。
    - User-Agent / Accept-Encoding を設定して HTTP リクエストを行う。
  - データ整形:
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）とそれに基づく SHA-256（先頭32文字）による記事ID生成。
    - テキスト前処理（URL 除去、空白正規化）。
    - pubDate のパースを行い、UTC に正規化。パース失敗時は警告ログを出して現在時刻で代替。
  - DB 保存:
    - save_raw_news: チャンク化された INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて挿入し、新規挿入された記事IDのリストを返す。1 トランザクションで処理し、失敗時はロールバック。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存。重複排除、チャンク化、トランザクション処理を実装。
  - 銘柄抽出:
    - 4桁数字パターンに基づく extract_stock_codes を提供し、known_codes に基づき有効コードのみ抽出。

- スキーマ管理 (kabusys.data.schema)
  - DuckDB 用の総合スキーマ DDL を定義（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw 層テーブル定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed 層定義。
  - features / ai_scores（Feature 層）および signals, signal_queue, orders, trades, positions, portfolio_performance（Execution 層）を定義。
  - 頻出クエリに対する索引群を定義。
  - init_schema(db_path) でディレクトリ自動作成 → DuckDB 接続 → 全 DDL / インデックス実行 → 接続返却を行う。get_connection() で既存 DB への接続を返す（初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラスを導入し、fetch/save の統計・品質問題・エラーを集約。to_dict() でシリアライズ可能。
  - 差分更新ユーティリティ:
    - テーブルが存在しない/空の場合のフォールバック。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date による最終取得日の取得。
    - _adjust_to_trading_day により非営業日を直近の営業日に調整（market_calendar が存在する場合）。
  - run_prices_etl: 差分更新ロジック（最終取得日から backfill_days 前を date_from とする挙動）を実装。デフォルト backfill_days=3。jquants_client の fetch/save を利用して取得・保存を行う。
  - 設計方針として品質チェックモジュール（quality）と連携する想定（品質問題は収集を止めずに集約する方針）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- defusedxml 導入、SSRF 対策、レスポンスサイズ上限、リダイレクト時の検証などにより外部入力を扱う箇所の安全性を強化。

Notes / 開発者向け補足
- デフォルトの DuckDB パス: data/kabusys.duckdb、SQLite パス: data/monitoring.db。
- デフォルト RSS ソースは Yahoo Finance の business カテゴリ RSS を含む。
- 環境変数の必須チェックに失敗すると ValueError を発生させる設計（早期検出）。
- jquants_client のリトライ対象や間隔は定数で定義されており、将来の調整が容易。
- news_collector._urlopen はテストで置き換え可能（モックしやすい設計）。
- 現状で strategy/execution/monitoring パッケージはパッケージ公開のみ（実装ファイルは空または未実装）。今後の機能追加対象。

署名
- この CHANGELOG はリポジトリ内ソースコードの構造・コメント・実装から推測して作成した初期リリース記録です。