Keep a Changelog 準拠の CHANGELOG.md（日本語）

すべての変更はソースコードから推測して記載しています。初回リリース相当のまとめです。

Unreleased
---------
（なし）

[0.1.0] - 2026-03-18
-------------------
Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。バージョン識別子 __version__ = "0.1.0" を追加。公開サブパッケージとして data, strategy, execution, monitoring を列挙。

- 環境設定読み込み・管理（src/kabusys/config.py）
  - .env / .env.local / OS 環境変数から設定を自動ロードする仕組みを実装。プロジェクトルート判定は .git または pyproject.toml を基準に行い、CWD に依存しない探索を実現。
  - .env 行パーサーがコメント・クォート・export KEY= 形式をサポート。トラブル時は警告を出す。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル等の設定をプロパティで取得。必要な環境変数未設定時は明確な例外を投げる。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得用 API クライアントを実装。
  - レート制限制御（120 req/min）を固定間隔スロットリングで実装する RateLimiter を導入。
  - リトライ戦略を備えた HTTP 呼び出しロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを尊重。
  - 401 Unauthorized 受信時はリフレッシュトークンで id_token の自動更新を試みて 1 回リトライ（無限再帰を避ける制御あり）。
  - id_token のモジュールレベルキャッシュを提供し、ページネーション等で共有。
  - fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。ページネーション対応。
  - DuckDB に冪等保存する save_* 関数を実装（ON CONFLICT DO UPDATE）。fetched_at を UTC で記録して取得時点をトレース可能に。
  - ユーティリティ関数 _to_float / _to_int を追加し、入力値の安全な数値変換を提供。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事収集して raw_news に保存する仕組みを実装（DataPlatform.md に準拠した設計）。
  - デフォルトソースとして Yahoo Finance のカテゴリ RSS を登録。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホストの小文字化、フラグメント削除）と、正規化 URL の SHA-256（先頭32文字）による記事ID生成を実装。
  - defusedxml を用いた安全な XML パース、最大受信バイト数（MAX_RESPONSE_BYTES = 10MB）でのサイズ制限、gzip 圧縮対応および解凍後のサイズチェックを実装（Gzip bomb 対策）。
  - SSRF 対策を強化：初回 URL のプライベートホスト判定、リダイレクト時にスキーム検証とプライベートアドレス検出を行うカスタム RedirectHandler（_SSRFBlockRedirectHandler）を導入。DNS 解決した A/AAAA を検査してプライベートIPを拒否（解決失敗は安全側で通過）。
  - URL スキーム検査、http/https 以外の URL 拒否、コンテンツ長チェック、XML パース失敗時のログと安全な挙動を実装。
  - テキスト前処理（URL除去、空白正規化）と記事抽出ロジックを実装。
  - save_raw_news: DuckDB に対するチャンク単位の INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いた保存を実装し、新規挿入された記事IDのリストを返す（トランザクションでまとめてコミット/ロールバック）。
  - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク INSERT + RETURNING で正確に返す実装。
  - extract_stock_codes: テキストから4桁銘柄コードを抽出し、既知の銘柄セットでフィルタして重複除去して返す。
  - run_news_collection: 複数 RSS ソースからの収集を統合し、個々のソース失敗時も他ソースを継続する頑健なジョブ実装。既知銘柄が与えられれば新規挿入記事に対して銘柄紐付けを一括実行。

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層に渡る包括的なテーブル定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）を実装。
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックス（頻出クエリ向け）を定義。
  - init_schema(db_path) によりディレクトリ自動作成 → DuckDB 接続 → DDL/インデックス作成を行い初期化済み接続を返す。get_connection() は既存 DB へ接続（初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL 実行結果を表す ETLResult dataclass を実装（品質チェック結果・エラー一覧を保持、辞書変換可能）。
  - テーブル存在確認・最大日付取得等のユーティリティを実装。
  - 市場カレンダーを考慮した営業日調整ヘルパーを実装（_adjust_to_trading_day）。
  - 差分更新ロジックの方針を実装（最終取得日からの差分取得、backfill による後出し修正吸収、calendar の先読み等）。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
  - run_prices_etl: 差分単位で日足を取得して保存するジョブを実装（date_from の自動算出と backfill 処理、J-Quants からの取得→保存フロー）。（実装済みのロジックあり、処理の戻り値/ログ出力を行う）

Changed
- 設計方針やログメッセージを詳細化しており、運用時の可観測性を向上（fetched_at の UTC 記録、ログ出力の充実）。

Security
- RSS パーサーに defusedxml を採用して XML ベースの攻撃を低減。
- SSRF 対策を複数レイヤーで実施（スキーム検証、プライベートIP検出、リダイレクト先検査）。
- レスポンスサイズ制限（MAX_RESPONSE_BYTES）と gzip 解凍後のサイズチェックによりメモリ DoS を緩和。
- DB 操作はトランザクションで保護し、例外時にロールバックする設計。

Notes / Known limitations
- pipeline モジュールは ETL のコア部分を備えるが、品質チェックモジュール（quality）の実装に依存する設計で、品質チェックの詳細実装は本コードベースからは確認できない。
- strategy/execution/monitoring パッケージはパッケージ階層は存在するが、今回提供コード中に具体的な戦略ロジックや発注実装は含まれていない（今後の実装予定）。
- run_prices_etl を含む ETL 関連処理は差分取得・保存の基本ロジックを提供するが、フルパイプライン（スケジューリング、監査ログ、外部モニタリング連携等）は外部の運用フレームワークでの接続が必要。
- 環境変数が未設定の場合は Settings が ValueError を投げるため、初期セットアップ時には .env を準備すること。

Acknowledgements
- 本 CHANGELOG はソースコードの実装内容から自動的に推測して作成しています。実際のリリースノートや運用ドキュメントとして公開する前に、必要に応じて補足・修正を行ってください。