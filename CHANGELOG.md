CHANGELOG
=========

すべての重要な変更点を記録します。形式は「Keep a Changelog」に準拠しています。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ基盤を追加（kabusys v0.1.0）。
  - パッケージ初期化: src/kabusys/__init__.py（__version__ = "0.1.0"、サブパッケージ公開）。
- 環境設定モジュールを追加（src/kabusys/config.py）。
  - .env/.env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - export KEY=val 形式やクォート・コメントのパースに対応した .env パーサを実装。
  - 必須環境変数取得のヘルパ（_require）と Settings クラスを提供（J-Quants, kabu API, Slack, DB パス, ログ・環境判定など）。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（有効値チェック）。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - データ取得: 日足（fetch_daily_quotes）、財務データ（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）。
  - 認証: リフレッシュトークンからの ID トークン取得（get_id_token）を実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を順守する RateLimiter を実装。
  - 再試行ロジック: 指数バックオフ、最大リトライ回数、HTTP 408/429/5xx のリトライ処理、429 の Retry-After 優先。
  - 401 受信時の自動トークンリフレッシュ（1回のみ）を実装。
  - DuckDB への冪等保存関数を追加（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT DO UPDATE により重複を排除。
  - レスポンスの JSON デコードエラー・ネットワーク例外のラップとログ出力。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS フィード取得（fetch_rss）、記事前処理（preprocess_text）、記事ID生成（URL 正規化＋SHA-256 トリム）を実装。
  - セキュリティ対策: defusedxml を利用した XML パース、SSRF 対策（リダイレクト先スキーム検証・プライベートホスト検査）、許容スキームは http/https のみ。
  - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズ検査（Gzip bomb 対策）。
  - トラッキングパラメータ除去（utm_ 等）とクエリソートによる URL 正規化。
  - DuckDB への冪等保存: save_raw_news（チャンク INSERT + INSERT ... RETURNING により新規挿入 ID を返す）、save_news_symbols / _save_news_symbols_bulk（銘柄紐付けのチャンク化・トランザクション制御）。
  - 銘柄コード抽出ユーティリティ（extract_stock_codes、4桁数字の検出と known_codes によるフィルタ）。
  - デフォルト RSS ソース辞書（DEFAULT_RSS_SOURCES）を定義（例: Yahoo Finance）。

- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）。
  - Raw / Processed / Feature / Execution 層を想定したテーブル群を DDL として定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 頻出クエリ向けのインデックス定義を追加。
  - init_schema(db_path) によるディレクトリ自動作成・テーブル作成（冪等）と DuckDB 接続返却、get_connection() の提供。

- ETL パイプライン基盤を追加（src/kabusys/data/pipeline.py）。
  - 差分更新のためのユーティリティ: テーブル存在チェック、最大日付取得（_get_max_date）、market_calendar を考慮した営業日調整(_adjust_to_trading_day)。
  - last date ヘルパ: get_last_price_date / get_last_financial_date / get_last_calendar_date。
  - ETL 結果を表す dataclass ETLResult（品質問題やエラーの収集、シリアライズ用 to_dict）。
  - run_prices_etl の骨組み（最終取得日からの差分再取得ロジック、backfill_days による再取得の考慮、J-Quants からの取得 → 保存呼び出しの実装方針）。
  - 市場カレンダーの先読み定数やデフォルトバックフィル日数を定義。

- パッケージ構造のスケルトンを用意（strategy/, execution/, data/__init__ 等のモジュール置き場）。

Security
- RSS パーシングに defusedxml を利用し XML ベースの攻撃対策を導入。
- RSS フェッチ時の SSRF 対策を実装（リダイレクト時の検査、最終 URL の再検証、プライベートアドレス拒否）。
- URL スキーム検証により file:, mailto:, javascript: 等の危険なスキームを拒否。

Notes / Known issues
- run_prices_etl の実装が途中（戻り値の形などで不整合の可能性あり）。現状のコードでは最終行の return が不完全（想定は (fetched_count, saved_count) の返却と思われる）で、ユニットテストや実運用前に修正が必要です。
- strategy/ および execution/ サブパッケージは現状スケルトン（実ロジック未実装）。
- quality モジュール参照（pipeline.py）など一部外部依存や追加実装が想定される（品質チェック実装は別途必要）。
- ドキュメント化・テスト・CLI 等は今回の実装に含まれていないため、導入時は API キー・環境変数設定方法や DB 初期化手順（init_schema の呼び出し）を README 等で補足することを推奨。

Deprecated
- （なし）

Removed
- （なし）

以上

もし特定の変更点を詳細化したい、あるいは「既知の不具合を修正したパッチ版 CHANGELOG（例: 0.1.1）」を作成したい場合は、対象ソースの修正箇所を教えてください。