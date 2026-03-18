# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
Semantic Versioning（https://semver.org/）に従います。

なお、本 CHANGELOG はコードベースから推測して作成したもので、実際のリリースノートと差異がある可能性があります。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-18

### Added
- パッケージ骨格
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - サブパッケージの公開: data, strategy, execution, monitoring。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装:
    - コメント行、export プレフィクス対応。
    - シングル／ダブルクォート内でのバックスラッシュエスケープに対応。
    - インラインコメント扱い（クォート外で「#」直前が空白/タブの場合）。
  - 環境変数必須チェック（_require）および Settings クラスを提供。
    - 主要設定項目（J-Quants、kabuステーション、Slack、DB パス等）をプロパティとして公開。
    - KABUSYS_ENV の検証（development/paper_trading/live）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - パス系は Path に展開（duckdb/sqlite のデフォルトパスを含む）。
    - is_live / is_paper / is_dev のヘルパー。

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の 3 層（＋Execution 層）に基づくテーブル定義を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）とインデックスを定義。
  - init_schema(db_path) による初期化処理（親ディレクトリ自動作成含む）を提供。
  - get_connection(db_path) による接続取得（スキーマ初期化は行わない）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティを実装:
    - ベース URL: https://api.jquants.com/v1。
    - レート制御: 固定間隔スロットリング（120 req/min = min_interval=0.5s 程度）。
    - リトライ: 指数バックオフ、最大 3 回。408/429/5xx 系に対する再試行。
    - 429 の場合は Retry-After ヘッダを優先。
    - 401 Unauthorized を受けた場合はトークンを自動リフレッシュして 1 回リトライ（無限再帰回避）。
    - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）。
    - JSON デコード失敗時の明示的エラー。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes: 株価日足（OHLCV）
    - fetch_financial_statements: 財務（四半期 BS/PL）
    - fetch_market_calendar: JPX マーケットカレンダー
  - DuckDB への保存関数（冪等、ON CONFLICT DO UPDATE）:
    - save_daily_quotes → raw_prices に保存
    - save_financial_statements → raw_financials に保存
    - save_market_calendar → market_calendar に保存
  - データ型変換ユーティリティ: _to_float, _to_int（安全な変換と不正値処理を実装）
  - fetched_at（UTC ISO）を保存して将来的な Look-ahead バイアス追跡に対応

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS ベースのニュース収集機能を実装:
    - デフォルト RSS ソース（Yahoo Finance の business カテゴリ）。
    - fetch_rss: RSS 取得 + XML パース（defusedxml 使用） → NewsArticle 型で返却。
    - save_raw_news: raw_news へ冪等保存（INSERT ... ON CONFLICT DO NOTHING、INSERT ... RETURNING を用いて新規挿入 ID を返す）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols へ記事と銘柄コードの紐付けを一括保存（トランザクション、チャンク処理、RETURNING 利用）。
    - extract_stock_codes: テキスト内の 4 桁銘柄コード抽出（既知コードセットでフィルタ、重複除去）。
    - run_news_collection: 複数 RSS ソースを順次取得して DB 保存 → 新規記事に対して銘柄紐付けを実行。ソース毎に独立したエラーハンドリング。
  - セキュリティ／堅牢性設計:
    - defusedxml を使用して XML 攻撃（XML Bomb 等）を防止。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時のスキーム・ホスト検証を行うカスタム RedirectHandler を導入。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否（IP 直接判定および DNS 解決で A/AAAA をチェック）。
    - レスポンスサイズ上限: MAX_RESPONSE_BYTES = 10 MB。Content-Length の事前チェック＋読み込みで超過時はスキップ（Gzip 解凍後サイズも再検証）。
    - URL 正規化と記事 ID の決定:
      - トラッキングパラメータ（utm_*, fbclid 等）を除去し、正規化 URL の SHA-256（先頭32文字）を記事IDに利用。冪等性を担保。
    - テキスト前処理でリンク除去と空白正規化を実施。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）
  - ETLResult データクラスを導入（取得数・保存数・品質問題・エラー等を格納）。
  - 差分更新ヘルパー:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date：raw_* テーブルの最終日取得。
    - _adjust_to_trading_day：非営業日のターゲット日調整（market_calendar を使用、最大 30 日遡る）。
  - run_prices_etl（株価日足の差分 ETL、差分計算・backfill ロジックを実装）
    - date_from 未指定時は DB の最終取得日からデフォルトで backfill_days（デフォルト 3 日）前から再取得。
    - データ取得は jquants_client.fetch_daily_quotes を使用、保存は jq.save_daily_quotes を使用。
  - ETL 設計方針: 差分更新、backfill による後出し修正の吸収、品質チェック継続方針（Fail-Fast しない）、id_token 注入可能でテスト容易性を確保。

### Security
- 設定・外部通信・XML パース周りにセキュリティ考慮を実装済み:
  - defusedxml による安全な XML パース。
  - SSRF 回避のためのスキーム検証・プライベートIP検査・リダイレクト時の検査。
  - HTTP レスポンスサイズ制限（メモリ DoS / Gzip Bomb 対策）。
  - .env の読み込みは OS 環境変数を protected として上書き防止（.env.local は override 可）。

### Known issues / Notes / TODO（コードから推測）
- pipeline.run_prices_etl の末尾が不完全に見える箇所が存在する（関数の戻り値としてタプルを返す想定だが、コード末尾が切れている/未完成の可能性あり）。実装確認が必要。
- strategy、execution、monitoring パッケージは __init__ が存在するが具体的な実装ファイルは含まれていない（骨格のみ）。
- 単体テストや統合テストの記述はこの差分からは確認できない。外部 API 呼び出し部（ネットワーク）や DB 操作はモック可能な設計になっているが、テスト実装が必要。

### Removed
- なし

### Changed
- なし

### Fixed
- なし

---

参照:
- 必須環境変数（コード内で _require によりチェックされるものの一部）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- データベース:
  - デフォルト DuckDB ファイル: data/kabusys.duckdb
  - デフォルト SQLite モニタリング DB: data/monitoring.db

（以上）