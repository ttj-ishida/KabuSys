# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に従います。

履歴
====

[0.1.0] - 2026-03-17
--------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
- パッケージメタ:
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - パッケージ公開用 __all__ に data/strategy/execution/monitoring を定義。
- 設定管理 (src/kabusys/config.py):
  - Settings クラスを導入し、環境変数からアプリ設定を取得。
  - J-Quants、kabuステーション、Slack、DBパスなどのプロパティ（例: jquants_refresh_token, kabu_api_password, slack_bot_token, duckdb_path, sqlite_path）。
  - 環境種別（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーションを実装（許容値チェック）。
  - .env 自動ロード機能を実装（プロジェクトルート判定: .git / pyproject.toml を探索）。
  - .env のパースで export プレフィックス、クォート、インラインコメント、エスケープを考慮する堅牢な実装。
  - OS 環境変数を保護する protected オプション、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
- J-Quants クライアント (src/kabusys/data/jquants_client.py):
  - API 通信の基本機能を実装（/token/auth_refresh, /prices/daily_quotes, /fins/statements, /markets/trading_calendar 等）。
  - レート制限制御: 固定間隔スロットリングで 120 req/min を順守する RateLimiter 実装。
  - リトライロジック: 指数バックオフ、最大3回、HTTP 408/429/5xx 対応。429 の Retry-After を優先。
  - 401 の場合はリフレッシュトークンで自動的に id_token を更新して1回リトライ。
  - ページネーション対応（pagination_key を利用）で fetch_* 関数が全件取得。
  - データ保存関数は冪等性を担保（DuckDB への INSERT ... ON CONFLICT DO UPDATE）。
  - データ整形ユーティリティ: _to_float / _to_int（文字列・float 変換、切り捨て回避ロジック）。
  - fetched_at に UTC タイムスタンプを付与し、Look-ahead Bias を回避できる設計。
- ニュース収集モジュール (src/kabusys/data/news_collector.py):
  - RSS フィード取得・パース（defusedxml 使用）、記事整形、DuckDB への保存を実装。
  - セキュリティ:
    - XML Bomb 等を防ぐため defusedxml を使用。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス検査、リダイレクト時の検証ハンドラ実装。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - URL 正規化: トラッキングパラメータ（utm_ 等）除去、クエリソート、フラグメント削除。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
  - テキスト前処理: URL 除去、空白正規化。
  - raw_news への保存はチャンク分割とトランザクションを行い、INSERT ... RETURNING で実際に挿入された ID を返却。
  - news_symbols（記事と銘柄の紐付け）は一括挿入・トランザクション・ON CONFLICT DO NOTHING で冪等に保存。
  - 銘柄抽出ロジック: 正規表現で4桁コード抽出し、既知コードセット（known_codes）との照合で重複除去して返却。
  - run_news_collection: 複数 RSS ソースを順次処理し、個別ソースでの失敗は他ソースに影響しない堅牢な実行フロー。
- DuckDB スキーマ定義 (src/kabusys/data/schema.py):
  - Raw / Processed / Feature / Execution の多層スキーマを定義。
  - テーブル群（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など）を追加。
  - 各カラムに制約（PRIMARY KEY, CHECK 等）を付与しデータ整合性を担保。
  - 頻出クエリ向けのインデックス定義を追加（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) によりディレクトリ作成 → テーブル作成 → インデックス作成を行う初期化処理を提供。get_connection で既存 DB への接続を取得可能。
- ETL パイプライン (src/kabusys/data/pipeline.py):
  - 差分更新を実現するヘルパーとジョブ（get_last_price_date, get_last_financial_date, get_last_calendar_date, run_prices_etl など）。
  - 差分更新ロジック: DB の最終取得日を見て date_from を自動算出（backfill_days を用いて後出し修正を吸収）。
  - 市場カレンダー補助: 非営業日の調整（_adjust_to_trading_day）。
  - ETL 実行結果を表現する ETLResult データクラス（品質問題リスト、エラー集約、to_dict メソッド）。
  - 品質チェック設計指針（quality モジュールとの連携を想定）。
- パッケージ構造:
  - data パッケージ内に jquants_client, news_collector, schema, pipeline を実装。
  - strategy / execution / monitoring のパッケージプレースホルダを追加（__init__.py を配置）。

Security
- RSS と HTTP クライアント周りで以下を導入:
  - defusedxml による XML セキュリティ対策。
  - SSRF 対策（スキーム検証、プライベートアドレスチェック、リダイレクト時の検査）。
  - レスポンスサイズ制限と Gzip 解凍後サイズ検証によるメモリ DoS 対策。
- 環境変数ロード時に OS 環境変数を保護する仕組みを導入。

Notes / Design Decisions
- 取得データは fetched_at（UTC）を付与し「いつデータが利用可能になったか」を追跡可能にした。
- DuckDB 側の保存はできる限り冪等（ON CONFLICT）にし、再実行可能な ETL を目指す。
- ネットワークエラーや API レート制限に配慮したリトライ・バックオフ・トークン更新ロジックを実装。
- ニュース記事の ID は URL の正規化後ハッシュを用いることでトラッキングパラメータの違いによる重複を防止。
- ETL の品質チェックは fail-fast せず収集は継続し、呼び出し元が判断できるように設計。

Known issues / TODO
- strategy / execution / monitoring の具体的実装は今回の初期リリースではプレースホルダ。今後の追加実装予定。
- pipeline.run_prices_etl などの ETL ジョブは品質チェック呼び出しや他データ（financials, calendar）の統合処理を今後拡張予定。

参考
- 各モジュールはソース内に設計方針や利用例の docstring を備え、今後の拡張とテスト容易性を考慮して関数引数に id_token の注入や HTTP 呼び出し箇所のモックポイントを用意しています。