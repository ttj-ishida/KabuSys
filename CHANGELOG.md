# Changelog

すべての重要な変更点をここに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-17

### Added
- 初期リリース: KabuSys — 日本株自動売買システムの最小実装を追加。
- パッケージ構成:
  - kabusys (バージョン: 0.1.0)
  - サブパッケージ: data, strategy (初期スタブ), execution (初期スタブ), monitoring（__all__ に含む）
- 設定/環境管理 (`kabusys.config`):
  - Settings クラスを実装。環境変数からアプリケーション設定を取得するプロパティ群を提供（J-Quants, kabuステーション, Slack, DB パス, 実行環境, ログレベル等）。
  - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動読み込み無効化のためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パースロジックを実装（export プレフィックス対応、クォート文字列のエスケープ・コメント処理対応、無効行スキップ）。
  - `duckdb`/`sqlite` のデフォルトパスを Settings で管理。
  - 環境変数検証（KABUSYS_ENV、LOG_LEVEL の値チェック）と便利な is_live/is_paper/is_dev プロパティを追加。

- データ取得クライアント (`kabusys.data.jquants_client`):
  - J-Quants API クライアントを実装。
  - レート制限制御: 固定間隔スロットリング（120 req/min を守る RateLimiter）。
  - HTTP リトライロジック: 指数バックオフ、最大 3 回。対象は HTTP 408/429/5xx およびネットワークエラー。
  - 401 応答時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
  - ページネーション対応の fetch 関数:
    - fetch_daily_quotes（株価日足: OHLCV）
    - fetch_financial_statements（四半期 BS/PL）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB へ冪等保存する save_* 関数（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 値変換ユーティリティ: _to_float, _to_int（不正値・空値を安全に処理）。

- ニュース収集モジュール (`kabusys.data.news_collector`):
  - RSS フィードから記事を取得し、前処理・保存するワークフローを実装。
  - セキュリティ・堅牢化:
    - defusedxml を使った XML パース（XML Bomb 等対策）。
    - SSRF 対策: 初回接続前のホスト検査、リダイレクト時スキーム/ホスト検証用の _SSRFBlockRedirectHandler、許可スキームは http/https のみ。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) を導入（圧縮後も検査）。
    - gzip 圧縮対応と解凍後サイズチェック（Gzip Bomb 対策）。
  - URL 正規化: トラッキングパラメータ（utm_* 等）除去、フラグメント削除、クエリソート。
  - 記事ID 生成: 正規化 URL の SHA-256（先頭32文字）を採用し冪等性を確保。
  - テキスト前処理: URL 除去、空白正規化。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDのみ返す（チャンクとトランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括で安全に保存（INSERT ... RETURNING を利用し実挿入件数を算出）。
  - 銘柄コード抽出ユーティリティ: extract_stock_codes（4桁数字を候補に既知銘柄セットでフィルタ、重複除去）。

- スキーマ管理 (`kabusys.data.schema`):
  - DuckDB 用の完全なスキーマ定義を実装（Raw / Processed / Feature / Execution 層）。
  - 主要テーブルを含む DDL（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）。
  - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）、インデックスの定義を含む（頻出クエリ向け）。
  - init_schema(db_path) によりディレクトリ作成 → テーブル/インデックス作成を冪等に実行。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (`kabusys.data.pipeline`):
  - ETLResult dataclass を追加（実行結果、品質問題リスト、エラー一覧、ユーティリティメソッド）。
  - 差分更新用ヘルパー: 最終取得日取得関数（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - トレーディングデー調整ヘルパー (_adjust_to_trading_day)。
  - run_prices_etl（株価差分 ETL）を実装（差分計算、バックフィル動作、jquants_client 経由で取得→保存）。
  - 定数: データ開始日 (_MIN_DATA_DATE = 2017-01-01)、カレンダー先読み日数、デフォルトバックフィル日数（3日）等。
  - 品質チェックとの統合ポイント（quality モジュールを参照する設計、品質問題は収集を継続して報告）。

### Security
- RSS/XML 周りのセキュリティ強化:
  - defusedxml を用いた安全な XML パース。
  - SSRF 対策（ホスト/IP のプライベート判定、リダイレクト検査、許可スキーム制限）。
  - レスポンスサイズ制限と gzip 解凍後のチェックにより DoS 攻撃対策。
- HTTP クライアントの堅牢化:
  - J-Quants クライアントでのリトライ制御、429 の Retry-After 優先利用、401 時の安全なトークンリフレッシュ。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Notes / Migration
- 初回起動時は kabusys.data.schema.init_schema(settings.duckdb_path) を呼び出して DB を初期化してください。
- .env の自動ロードはプロジェクトルート検出に依存します（.git または pyproject.toml が存在するディレクトリ）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants の API トークンは環境変数 `JQUANTS_REFRESH_TOKEN` にて設定が必須です（Settings.jquants_refresh_token により取得）。
- news_collector の fetch_rss は外部ネットワークへアクセスするため、テストでは _urlopen をモックして使用してください。
- schema.init_schema は冪等操作のため、既存データベースへの再実行は安全です。ただし DDL/制約変更時は既存データとの互換性に注意してください。

---

開発・貢献者: 初期実装 (自動生成ドキュメントとコードから推定)