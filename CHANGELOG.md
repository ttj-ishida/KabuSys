# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージを追加。__version__ = 0.1.0。公開サブパッケージ: data, strategy, execution, monitoring。

- 環境設定 / ロード機構（kabusys.config）
  - .env / .env.local ファイルまたは既存の環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動でプロジェクトルートを探索（CWD非依存）。
  - .env パーサ実装: コメント、export プレフィックス、クォート（エスケープ処理含む）、インラインコメントの扱い等に対応。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - Settings クラスを提供し、以下などの設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト localhost）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL の検証
    - is_live / is_paper / is_dev の便利プロパティ

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 基本クライアントを実装。主機能:
    - レート制御: 固定間隔スロットリングで 120 req/min を遵守（_RateLimiter）。
    - 再試行ロジック: 指数バックオフ、最大 3 回リトライ（対象: 408/429/5xx）。429 の場合は Retry-After ヘッダを尊重。
    - 認証トークン管理: refresh token→id token、モジュールレベルのトークンキャッシュ、および 401 受信時の自動リフレッシュ（1 回のみ）をサポート。
    - JSON レスポンスの安全なデコードとエラー報告。
  - データ取得関数:
    - fetch_daily_quotes: 株価日足（ページネーション対応）
    - fetch_financial_statements: 四半期財務（ページネーション対応）
    - fetch_market_calendar: JPX マーケットカレンダー取得
  - DuckDB への保存関数（冪等性を重視）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE による保存
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE による保存
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE による保存
  - ユーティリティ: 型変換ヘルパー _to_float / _to_int（空値や不正値を安全に None 化）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news / news_symbols に保存する機能を実装。主な特徴:
    - デフォルト RSS ソース（例: Yahoo Finance のビジネスカテゴリ）。
    - URL 正規化: トラッキングパラメータ（utm_*, fbclid 等）削除、スキーム/ホスト小文字化、フラグメント削除、クエリソート。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）を採用し冪等性を担保。
    - セキュリティ対策:
      - defusedxml による XML パース（XML Bomb 対策）。
      - SSRF 対策: リダイレクト先のスキーム検証、ホストのプライベート/ループバック/リンクローカル判定（DNS で A/AAAA を解決）を行い内部ネットワークアクセスを拒否。
      - 許可スキームは http / https のみ。
      - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - テキスト前処理（URL除去、空白正規化）と pubDate パース（UTC 変換、フォールバック処理）。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用いて新規挿入IDを正確に取得。チャンク分割・1トランザクションで処理。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols へ（news_id, code）をバルク挿入。ON CONFLICT で重複スキップし、挿入数を正確に返す。
    - 銘柄コード抽出: 4桁数字を候補とし known_codes に含まれるもののみを返す extract_stock_codes。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataSchema.md に基づく多層スキーマを実装（Raw / Processed / Feature / Execution 層）。
  - 主要テーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK 等）や外部キーを定義。
  - 頻出クエリ用インデックスを作成（code/date や status など）。
  - init_schema(db_path) でディレクトリ自動作成・DDL/INDEX を一括適用して DuckDB 接続を返す。
  - get_connection(db_path) により既存DBへの接続を取得可能。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の骨格を実装:
    - 差分更新の考え方（最終取得日を参照して未取得分のみ取得、バックフィルで後出し修正を吸収）。
    - ETLResult データクラス: 実行結果・品質問題・エラーを集約し to_dict によりシリアライズ可能。
    - スキーマ存在確認・最終日取得ユーティリティ（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダーを参照して非営業日を直近営業日に調整するヘルパー（_adjust_to_trading_day）。
    - run_prices_etl: 差分更新ロジック、バックフィル日数指定、jquants_client を使った取得・保存フロー（取得数・保存数を返す）。
  - 設計方針として、品質チェック（quality モジュール）を ETL の一部として扱うことを想定（品質問題を検出しても ETL を継続し呼び出し元でハンドリングする設計）。

### Security
- ニュース収集で SSRF 対策を実装（リダイレクト検査、ホストのプライベートIP検出、許可スキーム制限）。
- RSS XML パースに defusedxml を使用し、XML による攻撃ベクトルを低減。
- レスポンスサイズ制限と gzip 解凍後のサイズチェックを追加（メモリDoS / Gzip Bomb 対策）。

### Known issues / Notes
- strategy および execution パッケージは初期化ファイルのみで、アルゴリズムや発注ロジックの実装は今後の作業。
- pipeline.run_prices_etl の実装は株価差分取得のフローを実装済みですが、財務・カレンダー等のETL統合・品質チェックの呼び出し統合は継続作業対象。
- 外部サービス（J-Quants / RSS ソース）との挙動確認は実運用環境での検証が必要です。環境変数（トークン類）の管理に注意してください。

---

今後の予定:
- ETL の完全ワークフロー化（財務・カレンダー ETL、品質モジュール統合）
- 戦略モジュール（特徴量生成・AIスコア連携）の実装
- 発注実行（kabu ステーション連携）、監視/通知機能の追加

--------------------------
（本 CHANGELOG はコードベースの内容から推測して作成しています。細かな仕様・実装意図はソースコードや設計ドキュメントを参照してください。）