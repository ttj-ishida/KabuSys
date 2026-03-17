CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。
このファイルは日本語で記載しています。

Unreleased
----------

（なし）

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージエントリポイントとバージョン管理（src/kabusys/__init__.py）
- 設定・環境変数管理（src/kabusys/config.py）
  - .env と .env.local を自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロードの無効化対応
  - .env パーサの強化:
    - コメント、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ対応
    - インラインコメント判定ルール（クォートあり/なしの違い）を実装
  - Settings クラスでアプリケーション設定をプロパティ経由で取得:
    - J-Quants / kabuAPI / Slack / DB パスなど（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーション
    - Path 型での DuckDB/SQLite パス管理（expanduser 対応）
- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティ（_request）実装:
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対象）
    - 401 受信時にリフレッシュトークンで自動リフレッシュして 1 回リトライ
    - ページネーション対応（pagination_key を使用）
    - JSON デコード失敗時の明示的なエラー報告
  - id_token キャッシュと get_id_token 実装（ページネーション間でトークン共有）
  - データ取得関数:
    - fetch_daily_quotes（株価日足のページネーション取得）
    - fetch_financial_statements（四半期財務データのページネーション取得）
    - fetch_market_calendar（JPX カレンダー取得）
  - DuckDB への保存関数（冪等性を重視）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - ON CONFLICT DO UPDATE を使用した重複排除と更新
    - fetched_at を UTC タイムスタンプで記録（Look-ahead bias 対策）
  - 値変換ユーティリティ: _to_float / _to_int（安全な数値変換）
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得と記事整形パイプライン実装:
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証
    - コンテンツ前処理（URL 除去、空白正規化）
  - セキュリティと堅牢性の強化:
    - defusedxml を用いた XML パース（XML Bomb 対策）
    - SSRF 対策: リダイレクト時のスキーム検証とホストのプライベートアドレス判定（_SSRFBlockRedirectHandler / _is_private_host）
    - レスポンス受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）
    - http/https スキームのみ許可、その他スキームの URL を除外
  - DuckDB への保存:
    - save_raw_news: チャンクごとのバルク INSERT と INSERT ... RETURNING により実際に挿入された記事 ID を返す
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING、トランザクション管理）
    - トランザクション失敗時のロールバックとログ
  - 銘柄コード抽出ユーティリティ:
    - 4桁数字パターン抽出と known_codes によるフィルタ（重複除去）
  - run_news_collection: 複数 RSS ソースを順次取得し DB 保存、銘柄紐付けまで行う統合ジョブ（ソース単位でのエラーハンドリング）
- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DataPlatform の設計に基づく多層スキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）とインデックスを定義
  - init_schema(db_path) による初期化（親ディレクトリ自動作成、冪等的にテーブル作成）
  - get_connection(db_path) を提供（既存 DB 接続用）
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新・バックフィル方針の実装（最終取得日から backfill_days 日分を再取得）
  - ETLResult データクラス（品質チェック結果やエラー情報を保持）
  - テーブル存在チェック、最大日付取得ユーティリティ
  - 市場カレンダー調整ヘルパー（非営業日の場合に直近営業日に調整）
  - 差分取得ヘルパー: get_last_price_date / get_last_financial_date / get_last_calendar_date
  - run_prices_etl の骨組み（date_from 自動算出、fetch + save のフロー）
- パッケージ構成
  - data, strategy, execution, monitoring モジュールのトップレベルを公開（strategy/, execution/ は当時空の __init__.py ）

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS 処理における XML パース安全化（defusedxml の採用）
- HTTP リダイレクト・ホスト検査で SSRF を抑止
- レスポンスサイズチェック・gzip 解凍後の検査でメモリ DoS を軽減

Notes / Implementation details
- API レート制限: 120 req/min を遵守する設計（_min_interval = 60 / 120 秒）
- J-Quants リトライポリシー: 最大3回、429 の場合は Retry-After ヘッダを優先
- DuckDB 側の保存は可能な限り冪等（ON CONFLICT）に実装
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後や CWD に依存しないことを意図して実装
- run_prices_etl など ETL 部分は品質チェックモジュール（quality）と連携する前提で設計（quality モジュールは別途実装を想定）

Acknowledgements
- 初期実装では外部サービス（J-Quants, RSS ソース, kabuステーション, Slack 等）に依存するため、ユニットテストでは環境変数制御と外部呼び出しのモック化を推奨します。