# Changelog

すべての非破壊的な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。
このプロジェクトはセマンティックバージョニングを採用します。

※ 日付はリリース日を示します。

## [Unreleased]

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム "KabuSys" の基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基本設定
  - kabusys パッケージの初期化（__version__ = "0.1.0"）。
  - パッケージ公開モジュール一覧（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - OS の既存環境変数を保護するための protected 処理。
  - .env パーサ実装:
    - export KEY=val 形式やシングル/ダブルクォート、エスケープ、インラインコメント対応。
  - Settings クラスを提供（settings インスタンス経由で利用）。
    - J-Quants / kabuステーション / Slack / DB パス 等の取得プロパティ。
    - KABUSYS_ENV と LOG_LEVEL の入力検証（許容値チェック）。
    - パスは expanduser を使って展開。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本 API 呼び出しユーティリティ実装（_request）。
    - レート制御（RateLimiter）: 120 req/min を守る固定間隔スロットリング。
    - 再試行ロジック: 指数バックオフ（base=2.0）、最大3回リトライ。対象は 408/429/5xx、ネットワークエラーもリトライ。
    - 429 の場合は Retry-After ヘッダを優先して待機時間を決定。
    - 401 を受信した場合は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰防止）。
    - ページネーション対応（pagination_key の取り扱い）。
  - 認証ヘルパー: refresh_token から id_token を取得する get_id_token。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等性を考慮）:
    - save_daily_quotes: raw_prices に対して INSERT ... ON CONFLICT DO UPDATE を使用して保存。
      - fetched_at を UTC（Z表記）で記録。
      - PK 欠損行のスキップとログ出力。
    - save_financial_statements: raw_financials に対して同様の冪等保存。
    - save_market_calendar: market_calendar に対して同様の冪等保存。
  - 型安全な変換ユーティリティ (_to_float, _to_int)。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからの記事収集および DuckDB 保存ワークフローを実装。
    - fetch_rss:
      - defusedxml を使用した安全な XML パース（XML Bomb 対策）。
      - SSRF 対策:
        - URL スキーム検証（http/https のみ）。
        - ホストがプライベート/ループバック/リンクローカルかを判定して拒否。
        - リダイレクト検査用のカスタム HTTPRedirectHandler を導入。
      - 応答サイズの上限チェック（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズ検査（Gzip bomb 対策）。
      - User-Agent と gzip 受け入れ対応。
      - title / content の前処理（URL 除去、空白正規化）。
      - 公開日時のパースと UTC への正規化。パース失敗時はログと現在時刻代替。
      - 記事ID は正規化した URL の SHA-256 ハッシュ（先頭32文字）で生成（utm_* 等のトラッキング除去含む）し冪等性を確保。
    - save_raw_news:
      - INSERT ... ON CONFLICT DO NOTHING と RETURNING を使い、実際に挿入された記事IDのみを返す。
      - チャンク分割（_INSERT_CHUNK_SIZE）と単一トランザクションによる効率的挿入。
    - save_news_symbols / _save_news_symbols_bulk:
      - 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING + RETURNING）して正確な挿入数を取得。
    - extract_stock_codes:
      - テキスト中の4桁の数字を抽出し、与えられた known_codes に含まれるものだけを返す（重複除去）。
    - run_news_collection:
      - 複数 RSS ソースを処理、ソース毎にエラーハンドリングを行い他ソースへ影響を与えない設計。
      - 新規挿入記事に対して銘柄紐付けを一括処理。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataSchema に基づくスキーマを定義・初期化する init_schema 関数を実装。
  - レイヤー構成:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・制約（CHECK、PRIMARY KEY、FOREIGN KEY）を設定。
  - 頻出クエリ向けのインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - get_connection ヘルパーを提供（既存 DB への接続）。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETLResult dataclass を実装（取得件数・保存件数・品質問題・エラー一覧等を保持）。
    - to_dict により品質問題をシリアライズ可能。
    - has_errors / has_quality_errors のユーティリティプロパティ。
  - 差分更新ユーティリティ:
    - 最終取得日の取得ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - _adjust_to_trading_day: 非営業日調整（market_calendar に基づき最大 30 日遡る）。
  - run_prices_etl 実装（差分取得、バックフィル日数サポート、保存処理の呼び出し）。
  - 設計方針（コード内コメント）:
    - 差分更新のデフォルト単位は営業日1日、backfill_days により後出し修正を吸収。
    - 品質チェックは Fail-Fast ではなく全件収集し呼び出し元で判断する方針（quality モジュールの利用を想定）。

### Performance
- API 呼び出しでの固定間隔レートリミッタ実装によりレート管理を一元化。
- ニュース挿入はチャンク化・単一トランザクションで行い DB オーバーヘッドを低減。
- DuckDB に対する冪等な INSERT/ON CONFLICT パターンにより二重保存を防止。

### Security
- RSS パースに defusedxml を採用し XML 関連攻撃に対処。
- SSRF 対策:
  - URL スキーム検証、プライベートアドレス検出、リダイレクト先の事前検査を実装。
- .env の自動読み込みは既存 OS 環境変数を保護する実装。
- ニュース収集で受信サイズや gzip 解凍後サイズをチェックし DoS を緩和。

### Other / Developer ergonomics
- 各所に詳細な docstring と設計コメントを追加し、仕様や設計意図を明確化。
- テスト容易性を考慮した差し替えポイントを用意（例: news_collector._urlopen をモック可能）。
- 型注釈を多数導入して可読性と静的解析を容易に。

---

開発・改善の方針や既知の実装詳細は各モジュールの docstring（ソース内コメント）を参照してください。今後は品質チェックモジュール、戦略（strategy）・実行（execution）周りのロジック実装、監視（monitoring）機能の追加を予定しています。