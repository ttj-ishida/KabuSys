CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
このプロジェクトは Keep a Changelog のガイドラインに従い、セマンティックバージョニングを採用します。
最新の変更は常に一番上に記載します。

[Unreleased]
------------

- （現時点のコードベースでは未リリースの変更はありません）

0.1.0 - 2026-03-18
-----------------

Added
- 初期リリース。日本株自動売買システムの基礎モジュールを追加。
  - パッケージ: kabusys（__version__ = 0.1.0）
  - サブパッケージのスケルトンを用意:
    - kabusys.data
    - kabusys.strategy（初期プレースホルダ）
    - kabusys.execution（初期プレースホルダ）
    - kabusys.monitoring が __all__ に含まれる（今後の拡張意図）

- 環境設定管理（kabusys.config）
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
  - .env のパースはシェル形式の export KEY=val、クォート文字列（エスケープ処理含む）、インラインコメント処理などに対応。
  - OS 環境変数を保護するための protected キー概念と .env.local による上書き処理を実装。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（validation: development / paper_trading / live）
    - LOG_LEVEL（validation: DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev

- J-Quants クライアント（kabusys.data.jquants_client）
  - API レート制御（120 req/min）を満たす固定間隔スロットリング実装（内部 RateLimiter）。
  - HTTP リクエストの再試行（指数バックオフ、最大 3 回）。対象ステータス: 408, 429, 5xx。
  - 401 Unauthorized 受信時はリフレッシュトークンで自動的に id_token を更新して 1 回リトライ（無限再帰防止ロジックあり）。
  - モジュールレベルの id_token キャッシュを提供（ページネーション間で共有）。
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar: ページネーション対応のデータ取得関数を実装。
  - save_daily_quotes / save_financial_statements / save_market_calendar: DuckDB への冪等保存（ON CONFLICT DO UPDATE）を実装。fetched_at の記録による取得時点のトレーサビリティ確保。
  - データ変換ユーティリティ: _to_float / _to_int（不正値や空文字列の安全ハンドリング、"1.0" 形式の扱いなど）。
  - エラーハンドリングとログ出力を充実（失敗時は詳細な警告/例外を出力）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を取得し raw_news テーブルに保存する収集パイプラインを実装。
  - 主な機能:
    - URL正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）
    - 記事IDを正規化 URL の SHA-256 ハッシュ先頭32文字で生成して冪等性を担保
    - defusedxml による XML パース（XML Bomb 等への対策）
    - SSRF 対策: 不正スキーム拒否、ホストがプライベート/ループバック/リンクローカルの場合は拒否、リダイレクト時も検査（カスタム HTTPRedirectHandler）
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後の検査（Gzip Bomb 対策）
    - テキスト前処理（URL除去、空白正規化）
    - extract_stock_codes による本文から銘柄コード抽出（4桁数字、known_codes によるフィルタ）
    - save_raw_news: チャンク化 + トランザクション + INSERT ... RETURNING による正確な挿入確認
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けを一括で安全に保存
    - fetch_rss / run_news_collection: ソースごとに独立してエラーハンドリングし、1ソースの失敗が全体処理を止めない設計
  - デフォルト RSS ソースとして Yahoo Finance を設定（news.yahoo.co.jp のビジネスカテゴリ RSS）

- DuckDB スキーマ（kabusys.data.schema）
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）＋ Execution レイヤのテーブル定義を追加:
    - Raw レイヤ: raw_prices, raw_financials, raw_news, raw_executions
    - Processed レイヤ: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature レイヤ: features, ai_scores
    - Execution レイヤ: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）およびクエリ性能向上のためのインデックスを定義
  - init_schema(db_path) により DB ファイル親ディレクトリ自動作成、DDL を冪等に適用して接続を返す（":memory:" サポート）
  - get_connection(db_path) による既存 DB への接続ユーティリティ

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass による ETL 実行結果の構造化（品質問題、エラー一覧、取得/保存カウント等）
  - 差分更新ロジックのためのヘルパー:
    - _table_exists, _get_max_date
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
    - _adjust_to_trading_day: 非営業日を直近の営業日に調整するロジック（market_calendar を使用）
  - run_prices_etl の骨組みを実装:
    - 最終取得日からの backfill_days による再取得（デフォルト 3 日）で API の後出し修正を吸収
    - jquants_client の fetch/save を利用して差分取得・保存を行う
    - （ETL の設計方針: 品質チェックで重大度の問題が出ても処理を継続し、呼び出し元で判断させる）

Changed
- （初回リリースのため対象なし）

Fixed
- （初回リリースのため対象なし）

Security
- RSS 収集での SSRF 対策を強化:
  - URL スキーム検証、ホストのプライベートアドレス判定、リダイレクト先の事前検証
  - defusedxml による XML パース、防御的なレスポンスサイズチェック（Gzip 解凍後も検査）
- 環境変数の保護: OS 環境変数が .env によって意図せず上書きされないよう protected 機構を導入

Notes / Migration
- 既存プロジェクトに本パッケージを導入する場合:
  - プロジェクトルート判定は __file__ を起点に親ディレクトリを辿るため、パッケージがインストールされた環境では自動 .env ロードがスキップされる場合があります。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して明示的に管理してください。
  - DuckDB 初期化は init_schema() を呼び出してから ETL / ニュース収集機能を利用してください。":memory:" を渡すことでメモリ DB が使えます。
  - J-Quants API 利用には JQUANTS_REFRESH_TOKEN の設定が必須です。
  - news_collector.fetch_rss はネットワークリクエストを行います。テスト時は kabusys.data.news_collector._urlopen をモックして差し替え可能です。

Future
- strategy / execution / monitoring 向けの具象実装（シグナル生成、発注ロジック、監視アラート等）を今後追加予定。