# CHANGELOG

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の慣習に準拠します。  

format: https://keepachangelog.com/ja/1.0.0/

全般:
- 初期リリース（0.1.0）として、KabuSys のコアモジュールとデータパイプライン、DuckDB スキーマ、外部 API クライアント、RSS ニュース収集機能を実装しました。

[0.1.0] - 2026-03-18
Added
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ に __version__ = "0.1.0" を設定。
  - モジュール公開: data, strategy, execution, monitoring を __all__ に追加。

- 環境設定 / 設定管理 (kabusys.config)
  - .env および .env.local からの自動読み込み機能を実装（OS 環境変数 > .env.local > .env の優先度）。
  - プロジェクトルート検出ロジック: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを特定（配布後の動作を考慮）。
  - .env 行パーサ実装: export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント対応。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応（テスト用途）。
  - Settings クラス: 必須環境変数取得（_require）と設定プロパティ群を実装（J-Quants, kabu API, Slack, DB パス, 環境判定, ログレベル等）。
  - バリデーション: KABUSYS_ENV と LOG_LEVEL の許容値チェックを追加。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API クライアントを実装。主な機能:
    - レート制御: 120 req/min を守る固定間隔スロットリング（_RateLimiter）。
    - リトライ: 指数バックオフ、最大 3 回（ネットワークエラー / 408/429/5xx を再試行）。
    - 401 自動リフレッシュ: トークン期限切れ時に一度だけトークンをリフレッシュして再試行。
    - トークンキャッシュ: モジュールレベルで ID トークンをキャッシュ（ページネーション間で共有）。
    - JSON パース失敗時の明確なエラー。
  - データ取得 API:
    - fetch_daily_quotes: 株価日足（ページネーション対応）。
    - fetch_financial_statements: 四半期 BS/PL（ページネーション対応）。
    - fetch_market_calendar: JPX マーケットカレンダー取得。
  - DuckDB 保存関数（冪等性）:
    - save_daily_quotes: raw_prices へ ON CONFLICT DO UPDATE を用いて保存。
    - save_financial_statements: raw_financials へ冪等保存。
    - save_market_calendar: market_calendar へ冪等保存。
  - ユーティリティ: 型変換ヘルパー _to_float / _to_int を実装（安全な変換 / None ハンドリング）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集と DuckDB への保存ワークフローを実装。
  - セキュリティ / 堅牢性対策:
    - defusedxml による XML パース（XML Bomb 等対策）。
    - SSRF 対策: URL スキーム検証、プライベート/ループバック/リンクローカルアドレスの検出と拒否、リダイレクト時の検査を行うカスタム RedirectHandler を実装。
    - 受信サイズ制限 (MAX_RESPONSE_BYTES = 10 MB)、gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - 受け入れる URL スキームを http/https のみ許可。
  - 正規化と冪等性:
    - トラッキングパラメータ除去（utm_ 等）、URL 正規化、SHA-256 (先頭32文字) による記事ID生成で冪等性を確保。
  - RSS パースと前処理:
    - タイトル/本文の前処理（URL 除去、空白正規化）。
    - pubDate のパースと UTC への変換（パース失敗時は現在時刻で代替）。
    - content:encoded を優先して取得。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を用い、実際に挿入された記事IDを返す。チャンク挿入と単一トランザクション。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けを一括挿入（ON CONFLICT DO NOTHING）し、挿入数を正確に返す。
  - 銘柄コード抽出:
    - extract_stock_codes: テキストから 4 桁の銘柄コードを抽出し、known_codes に基づきフィルタリング。

- DuckDB スキーマ (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋Execution レイヤーのテーブル定義を実装。
  - テーブル群: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 制約とチェック: 主キー、外部キー、CHECK 制約（負値や列の妥当性）を設定。
  - インデックス: 頻出クエリに備えた複数のインデックスを定義。
  - init_schema(db_path): 親ディレクトリ自動作成、全テーブル・インデックスの作成（冪等）。
  - get_connection(db_path): 既存 DB への接続ヘルパ。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラス: ETL 実行結果の構造化（品質問題・エラーの集約、has_errors 等のユーティリティ）。
  - 差分更新ユーティリティ:
    - _table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date を実装。
    - _adjust_to_trading_day: 非営業日の調整ヘルパ。
  - run_prices_etl: 株価日足の差分 ETL を実装（差分算出ロジック、backfill_days による再取得、fetch/save 呼び出し）。（注意: ファイル末尾でタプル戻り値が途中で切れているため続きの処理は今後追加予定）

Changed
- （新規リリースのため変更履歴は該当なし）

Fixed
- （初期リリースのため修正項目は該当なし）

Security
- ニュース取得で以下のセキュリティ対策を導入:
  - defusedxml を使用した安全な XML パース。
  - SSRF 対策（ホストのプライベートアドレス検出、リダイレクト先検査、スキーム検証）。
  - レスポンスサイズ上限と gzip 解凍後のサイズ検査による DoS 緩和。
- J-Quants クライアント: トークン自動リフレッシュと再試行で認証・通信の堅牢性を確保。

Notes
- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings._require により未設定は ValueError を発生）。
- デフォルトのデータベースパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (モニタリング用): data/monitoring.db
- 今後の作業（予定）:
  - pipeline.run_prices_etl の戻り値整備と追加 ETL ジョブ（financials / calendar）の実装拡張。
  - strategy / execution / monitoring モジュールの具体実装（現在は __init__ のみ存在）。
  - 単体テスト・統合テストの追加と CI 設定。
  - ドキュメント（DataPlatform.md, DataSchema.md の参照実装の整備）と使用例の追加。

参考
- 本リリースはプロジェクト初期段階の実装であり、ETL の一部や高レベルモジュール（strategy, execution, monitoring）は今後拡張されます。セキュリティ・冗長性に配慮した実装を優先しています。