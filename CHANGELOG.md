CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

0.1.0 - 2026-03-17
------------------

初回公開リリース。

Added
- パッケージ基盤
  - パッケージ名: kabusys。バージョン 0.1.0 を設定。
  - __all__ に data, strategy, execution, monitoring を公開（モジュール分離の準備）。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードの無効化をサポート（テスト用途）。
  - .env パーサを独自実装:
    - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理。
    - override / protected を用いた上書き制御。OS 環境変数保護を考慮。
  - Settings クラスでアプリ設定をプロパティとして提供:
    - J-Quants / kabuステーション / Slack / DB パスなどの必須・既定値管理。
    - KABUSYS_ENV と LOG_LEVEL のバリデーション（有効値チェック）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
  - デフォルト DB パス: DuckDB -> data/kabusys.duckdb、SQLite -> data/monitoring.db。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API レート制御: 固定間隔スロットリングで 120 req/min (min interval 設定) を実装。
  - 再試行ロジック:
    - 指数バックオフ（ベース 2 秒）、最大 3 回リトライ。
    - 対象ステータス: 408, 429 および 5xx。
    - 429 の場合は Retry-After ヘッダを優先。
  - 認証トークン処理:
    - refresh_token から id_token を取得する get_id_token() 実装（POST）。
    - モジュールレベルの id_token キャッシュを導入し、ページネーション間で共有。
    - 401 受信時には自動的にトークンを 1 回だけリフレッシュして再試行。
  - データ取得 API:
    - fetch_daily_quotes（株価日足、ページネーション対応、pagination_key の重複検出で終了）。
    - fetch_financial_statements（四半期財務、ページネーション対応）。
    - fetch_market_calendar（マーケットカレンダー）。
    - 取得時に取得件数をログ出力し、fetched_at を記録する慣習を踏襲する実装に合わせやすい設計。
  - DuckDB への保存ユーティリティ（冪等設計）:
    - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE を使って保存。
    - save_financial_statements: raw_financials に ON CONFLICT DO UPDATE を使って保存。
    - save_market_calendar: market_calendar に ON CONFLICT DO UPDATE を使って保存。
    - PK 欠損行はスキップして警告ログを出力。
  - 型安全・変換ユーティリティ:
    - _to_float / _to_int：不正値や空値は None、"1.0" のような文字列は float 経由で安全に int 変換。小数部が残る場合は None を返す。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからの記事収集実装（DEFAULT_RSS_SOURCES に Yahoo Finance を含む）。
  - セキュリティと堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 防止）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト先の事前検証を行うカスタム HTTPRedirectHandler（_SSRFBlockRedirectHandler）。
      - ホスト名の DNS 解決と IP 判定によるプライベートアドレス検出（loopback/link-local/multicast をブロック）。
      - _urlopen を抽象化してテスト時にモック可能に。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - Content-Length の事前検査。
    - 非 http(s) スキームやプライベートアドレスの最終 URL を検出した場合は安全にスキップ。
  - 記事 ID / 正規化:
    - _normalize_url でスキーム/ホストの小文字化、トラッキングパラメータ（utm_ 等）削除、フラグメント削除、クエリソートを実施。
    - 記事ID は _make_article_id で正規化 URL の SHA-256（先頭32文字）を使用し冪等性を確保。
  - テキスト前処理:
    - URL 除去、空白正規化、トリムを行う preprocess_text。
  - RSS パース:
    - content:encoded 名前空間を優先、description をフォールバック。
    - pubDate を RFC2822 から UTC naive datetime に変換し、パース失敗時は現在時刻で代替（NOT NULL 制約対応）。
  - DB 保存（DuckDB）:
    - save_raw_news: 1 トランザクションでチャンク分けして INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事IDリストを返す。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols に対してチャンク INSERT を行い、ON CONFLICT DO NOTHING RETURNING を使って正確な挿入数を返却。トランザクションとロールバックを適切に扱う。
  - 銘柄コード抽出:
    - extract_stock_codes: 正規表現で 4 桁数字を抽出し、与えた known_codes セットでフィルタ、重複除去。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataPlatform の階層構成に基づくテーブル定義を追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・チェック制約・主キー・外部キーを付与。
  - 頻出クエリに対するインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) でディレクトリ作成を含む初期化処理を提供（冪等）。get_connection() を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass を導入し、ETL 実行結果、品質問題、エラーを構造化して返却可能に。
  - 差分更新支援:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date: raw_* テーブルの最大日付を返すヘルパー。
    - _adjust_to_trading_day: 非営業日の場合に直近の営業日に調整するロジック（market_calendar を参照）。
  - run_prices_etl の部分実装:
    - 最終取得日からの差分算出（backfill_days の概念を導入し、後出し修正を吸収）。
    - jq.fetch_daily_quotes を呼び出してデータ取得 → jq.save_daily_quotes で保存。
    - 実行ログと (fetched, saved) の返却を予定（ファイルでは途中まで実装）。
  - 設計方針: 品質チェックを行うが、致命的エラーがあっても全件収集を続ける（Fail-Fast ではない）。id_token の注入によりテスト容易性を確保。

Changed
- （初回リリースのため特になし）

Fixed
- （初回リリースのため特になし）

Security
- RSS パーサに defusedxml を採用し、SSRF・XML Bomb・外部向け URL 検査など多数の防御を実装。
- .env 読み込み時のファイルアクセスエラーは warnings.warn で通知して安全にフォールバック。

Notes / Implementation details
- 依存: duckdb, defusedxml が主要な依存ライブラリとして想定される。
- テスト支援:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数や _urlopen のモック化ポイントを用意。
  - jquants_client の id_token を引数注入可能にして、HTTP 実装を差し替えてテスト可能。
- ロギング: 主要処理は logger を通じて情報・警告・例外を記録する設計。
- 設計文書（README/DataPlatform.md, DataSchema.md 等）を前提に実装されていることを反映したコメントが多数存在。

開発者向け TODO（今後の改良候補）
- pipeline.run_prices_etl の戻り値整備（現在コード断片でタプルの最後が未完になっている点を完了する必要あり）。
- strategy / execution / monitoring の具体実装を追加。
- より詳細な品質チェック実装（kabusys.data.quality を完成させる）。
- 単体テスト・統合テストの追加（HTTP クライアントのモックや DuckDB の一時 DB を使った検証）。
- ドキュメント (Usage / API) と例（CLI / cron での ETL 実行例、Slack 通知例）の追加。

以上。