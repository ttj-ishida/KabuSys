# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般方針：
- バージョンはパッケージ内の `kabusys.__version__` に合わせて付与しています。
- 記載はソースコードから推測してまとめた内容です。

## [0.1.0] - 2026-03-18

### Added
- 初期リリース（基本機能群を実装）
  - パッケージメタ
    - `kabusys` パッケージを導入。トップレベルで `data`, `strategy`, `execution`, `monitoring` を公開（各サブパッケージの基盤構造を用意）。
    - パッケージバージョン: `0.1.0`

  - 設定管理
    - `kabusys.config` モジュールを追加。
      - プロジェクトルート（`.git` または `pyproject.toml`）を基準にして `.env` / `.env.local` を自動読み込みする仕組みを提供（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
      - `.env` ファイルのパース機能（コメント、`export` プレフィックス、シングル/ダブルクォート・エスケープ、インラインコメント処理などを考慮）。
      - `Settings` クラスを提供し、アプリケーションで用いる主要な環境変数（J-Quants リフレッシュトークン、kabu API パスワード、Slack トークン/チャネル、DB パス等）をプロパティ経由で取得。値のバリデーション（`KABUSYS_ENV`／`LOG_LEVEL` の許容値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）を実装。
      - 必須環境変数未設定時は `ValueError` を投げる `_require` を用意。

  - データ取得（J-Quants）
    - `kabusys.data.jquants_client` を追加。
      - API 呼び出しラッパー `_request` を実装。設計上の特徴：
        - API レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
        - リトライ処理（最大 3 回、指数バックオフ）、HTTP 408/429/5xx に対する再試行、429 の `Retry-After` ヘッダ優先処理。
        - 401 受信時は ID トークンを自動でリフレッシュして 1 回リトライ（再帰防止のため allow_refresh フラグ制御）。
        - JSON デコードエラーやネットワークエラーの適切なラップ/再送制御。
      - 認証補助 `get_id_token`（リフレッシュトークンから idToken を取得する POST 実装）。
      - データ取得関数（ページネーション対応）:
        - `fetch_daily_quotes`（株価日足）
        - `fetch_financial_statements`（四半期財務データ）
        - `fetch_market_calendar`（JPX カレンダー）
      - DuckDB へ保存する冪等的保存関数:
        - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`
        - すべて ON CONFLICT / DO UPDATE による更新で重複を排除。保存時に `fetched_at` を UTC ISO 形式で付与。
      - 値変換ユーティリティ（型安全な float/int 変換） `_to_float`, `_to_int` を実装。

  - ニュース収集
    - `kabusys.data.news_collector` を追加。
      - RSS フィードの取得と記事抽出（`fetch_rss`）：
        - defusedxml を使った安全な XML パース（XML Bomb 対策）。
        - gzip 圧縮対応、最大受信バイト数（10MB）制限、Gzip 解凍後のサイズ検証。
        - SSRF 対策（許可されないスキームの拒否、リダイレクト先の検査、プライベート/ループバックアドレス判定 `_is_private_host`、リダイレクトハンドラ `_SSRFBlockRedirectHandler`）。
        - URL 正規化（トラッキングパラメータ除去、クエリソート）と記事ID生成（正規化 URL の SHA-256 先頭32文字）。
        - テキスト前処理（URL 除去、空白正規化）`preprocess_text`。
        - pubDate の RFC2822 パース（UTC に正規化）`_parse_rss_datetime`。
      - DuckDB への保存（冪等）：
        - `save_raw_news`：チャンク分割、トランザクション管理、INSERT ... RETURNING により新規挿入された記事 ID を返す実装。
        - `save_news_symbols` / `_save_news_symbols_bulk`：記事と銘柄コードの紐付けを一括で保存（ON CONFLICT DO NOTHING、トランザクション管理）。
      - 銘柄コード抽出ユーティリティ `extract_stock_codes`（記事テキストから4桁の銘柄コードを抽出し既知コードセットでフィルタ）。
      - 統合収集ジョブ `run_news_collection`：複数 RSS ソースからの収集→保存→（必要なら）銘柄紐付けを実行、各ソースは独立してエラーハンドリング。

  - DuckDB スキーマ
    - `kabusys.data.schema` を追加。DataSchema に基づくスキーマ定義を実装。
      - Raw / Processed / Feature / Execution の各レイヤー用テーブル定義を DDL で用意（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）。
      - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY）を定義。
      - 頻出クエリ向けインデックス群を作成。
      - `init_schema(db_path)`：DB ファイルの親ディレクトリ自動作成、すべての DDL とインデックスを実行して接続を返す。
      - `get_connection(db_path)`：既存 DB への接続（スキーマ初期化は行わない）。

  - ETL パイプライン（初期実装）
    - `kabusys.data.pipeline` を追加。
      - ETL 実行結果を表す `ETLResult` データクラス（品質問題・エラー収集、辞書化ユーティリティ）。
      - DB 状態参照ユーティリティ `_table_exists`, `_get_max_date`、および raw テーブルの最終取得日取得関数（`get_last_price_date`, `get_last_financial_date`, `get_last_calendar_date`）。
      - カレンダーを使った営業日調整 `_adjust_to_trading_day`（市場カレンダーが存在する場合に target_date を直近営業日に調整）。
      - 差分更新方針を取り入れた `run_prices_etl` の初期実装：
        - 最終取得日からバックフィル日数分（デフォルト 3 日）さかのぼって再取得するロジック。
        - J-Quants から差分取得し、`jquants_client.save_daily_quotes` で保存する流れを実装。
      - ETL の設計方針として品質チェック（`kabusys.data.quality` を呼ぶ想定）を含めた構成を想定。

### Changed
- 初期リリースのため該当なし（ベース実装を追加）。

### Fixed
- 初期リリースのため該当なし。

### Security
- 複数のセキュリティ強化を実装：
  - XML パースに defusedxml を採用（XML Bomb 等対策）。
  - RSS フィード取得時の SSRF 対策（スキーム検証、リダイレクト先検査、プライベートアドレス拒否）。
  - 外部リソースからの受信サイズ上限（MAX_RESPONSE_BYTES）を設け、メモリ DoS / Gzip Bomb に対処。
  - `.env` ファイル読み込み時、OS環境変数の保護（protected set）を考慮した上書き制御。

### Notes / Limitations / TODO
- pipeline.run_prices_etl は差分取得と保存の基本ロジックを実装しているが、品質チェック（quality モジュールとの統合）や他の ETL ジョブ（財務・カレンダーの完全な ETL フロー）と統合する作業が必要。
- strategy / execution / monitoring サブパッケージの実体はこのリリース時点では最小構成（パッケージ空ディレクトリ）で、発注実装や戦略ロジックは今後実装予定。
- 単体テスト・統合テストに関するコードは含まれていない（テストの整備は今後のリリースで実施予定）。
- 一部の戻り値や例外処理に関して（実運用における詳細なリトライ/バックオフ方針、監視フック、メトリクス出力等）の追加改善余地あり。

---

（以降のリリースでは、変更点を新しいヘッダに追記してください）