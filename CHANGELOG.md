CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース。
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 環境設定/ロード機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロードを実装（プロジェクトルート検出: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env のパースロジックを実装（export プレフィックス、クォート／エスケープ、行内コメントの扱い等に対応）。
  - 必須キー取得用の _require、Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境/ログレベルなど）。
  - 環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）と便利な判定プロパティ（is_live 等）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得関数を実装（ページネーション対応）。
  - レート制限（120 req/min）の固定間隔スロットリング実装（RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
  - JSON デコード失敗時の明示的エラー、Retry-After ヘッダ優先処理など堅牢化。
  - DuckDB へ冪等保存する save_* 関数（ON CONFLICT DO UPDATE）を実装（raw_prices, raw_financials, market_calendar）。
  - データ取り込み時に fetched_at を UTC で記録し Look-ahead bias の追跡を可能に。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得・パース・前処理・DuckDB への保存フローを実装（fetch_rss、save_raw_news、save_news_symbols、run_news_collection 等）。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを登録。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等に対応）。
    - SSRF 対策: 非 http/https スキーム拒否、ホストがプライベート/ループバック/リンクローカルであれば拒否、リダイレクト先を検査するカスタム RedirectHandler を導入。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - 許可されない URL スキーム（mailto: 等）はスキップ。
  - 記事ID は URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を担保（utm_* 等のトラッキングパラメータを除去）。
  - テキスト前処理（URL 除去、空白正規化）関数を提供。
  - 銘柄コード抽出（4桁数字、外部 known_codes セットでフィルタ）機能を実装。
  - DuckDB への挿入はチャンク化とトランザクションで行い、INSERT ... RETURNING を用いて実際に挿入された件数を返す。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブルを定義。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores 等の Feature テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
  - 適切な制約（PK, CHECK, FOREIGN KEY）やインデックスを設定。
  - init_schema(db_path) でディレクトリ作成・DDL 実行・接続返却、get_connection を提供。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETL の処理方針・差分更新ロジックの実装（最終取得日からの差分取得、backfill による後出し修正吸収）。
  - ETLResult データクラスを実装（取得数、保存数、品質チェック結果、エラー一覧などを格納・辞書化）。
  - テーブル存在確認や最大日付取得ユーティリティ（_table_exists、_get_max_date）を実装。
  - market_calendar を用いた営業日調整ヘルパー（_adjust_to_trading_day）。
  - raw_prices/raw_financials/market_calendar 用の最終取得日取得関数（get_last_price_date 等）。
  - 株価差分ETL run_prices_etl を実装（差分判定、fetch_daily_quotes → save_daily_quotes を呼び出し、取得数・保存数を返却）。

Security
- RSS パーサーに defusedxml、SSRF 保護、応答サイズ上限を導入。
- HTTP クライアント処理にてリダイレクト先のスキーム・ホスト検査を追加。

Notes / Migration
- 初期化: DuckDB を使うには init_schema(db_path) を実行してスキーマを作成してください。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - これらが未設定の場合、Settings のプロパティアクセス時に ValueError を送出します。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）が見つかった場合にのみ行われます。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API の呼び出しは内部でレート制限・再試行・トークンリフレッシュを行うため、呼び出し側は簡潔に利用可能です。
- run_news_collection は既知銘柄コードセット（known_codes）を渡すことで記事と銘柄の紐付けを自動で行います。

Broken / Deprecated
- なし

Acknowledgments
- 初期実装のため、今後の利用でフィードバックに応じて API、戻り値の細部、ログ出力等を改善します。