# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

### Known issues / TODO
- run_prices_etl の戻り値実装に未完の箇所あり（現在は取得レコード数のみ返す実装断片が見られる）。完全な ETL 結果の返却（prices_saved など）を要修正。
- ユニットテストは想定されている（例: KABUSYS_DISABLE_AUTO_ENV_LOAD / _urlopen のモックなど）ものの、テストスイートは未同梱。テスト整備を推奨。
- 追加のエラーハンドリングや監視・メトリクス出力は今後拡張予定。

---

## [0.1.0] - 2026-03-17

初期リリース。日本株自動売買システムのコア基盤を提供します。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージの初期構成（サブモジュール: data, strategy, execution, monitoring をエクスポート）。
  - バージョン定義: 0.1.0。

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動ロード機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env の柔軟なパース実装（コメント行、export プレフィックス、シングル/ダブルクォート、インラインコメント処理を考慮）。
  - 環境変数保護の仕組み（OS 環境変数を protected として .env.local の上書きを制御）。
  - Settings クラス: J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル検証、is_live/is_paper/is_dev ヘルパー。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 安全で堅牢な HTTP ラッパー _request を実装（JSON デコード例外ハンドリング）。
  - レート制御（120 req/min）を満たす固定間隔レートリミッタ実装。
  - 再試行（指数バックオフ）ロジック: ネットワークや指定ステータス（408, 429, 5xx）に対する最大 3 回リトライ、429 の場合は Retry-After を優先。
  - 401 Unauthorized 受信時の ID トークン自動リフレッシュ（1 回のみ）とトークンキャッシュ共有。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足／OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ取り込み時の fetched_at を UTC ISO8601 で記録し、Look-ahead Bias 対策。
  - 数値変換ユーティリティ _to_float / _to_int（文字列からの安全な変換と不正値処理）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して DuckDB に保存するモジュールを実装。
  - セキュリティ対策:
    - defusedxml を使った XML パースで XML Bomb 等を防止。
    - 非 http/https スキーム拒否、SSRF 対策（リダイレクト先のスキーム検査、プライベート IP アドレス判定）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip Bomb対策）。
  - URL 正規化:
    - トラッキングパラメータ（utm_*, fbclid, gclid など）除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート。
    - 正規化 URL から SHA-256 の先頭32文字を記事 ID として生成（冪等性確保）。
  - テキスト前処理（URL 除去、空白正規化）。
  - フィード取得とパース（fetch_rss）:
    - content:encoded を優先、description をフォールバック。
    - pubDate の RFC 形式パースと UTC への正規化。
    - 不正フィードやパース失敗時は警告ログを出し空配列を返却。
  - DB 保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用、1 トランザクションで挿入された新規記事 ID を返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けをバルク挿入（ON CONFLICT DO NOTHING）で保存し、実際に挿入された件数を返却。
  - 銘柄抽出機能:
    - extract_stock_codes: テキスト中の 4 桁数値（日本株銘柄）を抽出し、既知のコードセットと照合して重複除去して返す。
  - 統合収集ジョブ:
    - run_news_collection: 複数ソースの独立処理（1 ソース失敗でも他ソース継続）、新規保存数の集計、既知銘柄との紐付けを実施。
    - デフォルト RSS ソース（yahoo_finance）を定義。

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマ DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw Layer。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed Layer。
  - features, ai_scores などの Feature Layer。
  - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution Layer。
  - 運用上の頻出クエリを考慮したインデックスを定義。
  - init_schema(db_path) でディレクトリ作成（必要時）とテーブル/インデックスの冪等作成を実行。get_connection で既存 DB に接続。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETLResult dataclass により ETL 実行結果（品質問題・エラー含む）を構造化し、辞書化可能に。
  - 差分更新ロジックのヘルパー:
    - DB の最終取得日取得（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - 市場カレンダーに基づき非営業日を直近営業日に調整する _adjust_to_trading_day。
  - run_prices_etl の差分取得ロジック（最終取得日から backfill_days を遡るデフォルト 3 日、_MIN_DATA_DATE で初回ロードを制御）。jquants_client を使った取得と保存のワークフロー設計（idempotent 保存を前提）。
  - ETL 設計方針: 差分更新、backfill、品質チェック（quality モジュールと連携想定）、テスト容易性のため id_token 注入可能。

### Security
- RSS/XML パーサに defusedxml を採用し XML 攻撃を軽減。
- RSS フェッチで SSRF 対策を実装（スキーム検証・プライベートホスト拒否・リダイレクト検査）。
- .env 読み込み時に OS 環境変数を保護する仕組みを導入。

### Performance / Reliability
- J-Quants クライアントにレートリミッタ、リトライ、トークンキャッシュを実装して API レート制限と信頼性を確保。
- DuckDB へのバルク挿入をチャンク化してオーバーヘッドを抑制。
- ON CONFLICT を用いた冪等保存で重複更新を抑制。
- インデックス定義により 銘柄×日付 スキャンやステータス検索を高速化。

### Notes / Design decisions
- fetched_at は UTC の ISO8601（Z）で記録し、データが「いつシステムに到着したか」をトレース可能に。
- news_collector の記事 ID はトラッキングパラメータ除去後の URL をハッシュ化して生成し、トラッキング差分での重複挿入を防止。
- pipeline は Fail-Fast ではなく、品質チェックで重大問題が発見されても処理自体は継続し、呼び出し元での判断を想定。

---

今後予定（例）
- run_prices_etl の戻り値/レポート出力を完結させる修正。
- quality モジュールとの連携実装（欠損・スパイク検出の自動レポート）。
- strategy / execution / monitoring モジュールの具現化（現在はパッケージ構成のみ）。
- テストカバレッジの整備と CI 設定。

以上。