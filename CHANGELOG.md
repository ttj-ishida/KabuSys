# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
このプロジェクトはセマンティックバージョニングを採用しています。

なお、本CHANGELOGはリポジトリ内のコードから推測して作成しています（自動生成ではありません）。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-18

初回公開リリース。日本株自動売買システム「KabuSys」のコアライブラリを実装。

### Added
- パッケージ初期化
  - パッケージメタ情報と公開モジュールを定義（kabusys.__version__ = 0.1.0、data/strategy/execution/monitoring をエクスポート）。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動ロードのルール:
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサー: コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
  - 必須設定の取得関数（_require）。必須環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルト値 / バリデーション:
    - KABUSYS_ENV（development / paper_trading / live）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - DUCKDB_PATH/SQLITE_PATH のデフォルトパス

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ（_request）を実装。特徴:
    - レート制御（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）。
    - 再試行（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時はリフレッシュトークンから id_token を自動取得して 1 回だけリトライ（無限再帰防止のため allow_refresh 制御）。
    - ページネーション対応（pagination_key の追跡）。
    - JSON デコードエラーやネットワークエラーのハンドリング。
  - 認証: get_id_token(refresh_token=None)
  - データ取得関数:
    - fetch_daily_quotes（OHLCV、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB へ冪等に保存する関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - ON CONFLICT DO UPDATE を利用して重複を排除・上書き
    - fetched_at（UTC ISO8601）を記録して Look-ahead Bias を低減
  - 型変換ユーティリティ: _to_float, _to_int（厳密な変換ルール）

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得と raw_news への保存機能一式を実装。
  - セキュリティ対策・堅牢性:
    - defusedxml を用いて XML Bomb 等の攻撃を軽減。
    - SSRF 対策: リダイレクト先のスキーム検証とプライベートIP/ループバックの検出（_SSRFBlockRedirectHandler、_is_private_host）。
    - HTTP スキーム制限（http/https のみ）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後の検査（Gzip-bomb 対策）。
    - トラッキングパラメータ除去（utm_ 等）を含む URL 正規化。
  - 記事ID生成:
    - 正規化 URL の SHA-256 ハッシュ先頭 32 文字を記事IDとして利用し冪等性を保証。
  - DB 保存:
    - save_raw_news: チャンク化（_INSERT_CHUNK_SIZE）して INSERT ... ON CONFLICT DO NOTHING RETURNING id を実行。トランザクションでまとめ、挿入された新規記事IDのリストを返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存、ON CONFLICT で重複をスキップし実際に挿入された件数を返却。
  - テキスト前処理:
    - URL 削除、空白正規化（preprocess_text）。
  - 銘柄コード抽出:
    - 正規表現で 4 桁数字を抽出し、known_codes でフィルタ（extract_stock_codes）。
  - 統合収集ジョブ:
    - run_news_collection: 複数ソースを個別に処理、ソース単位で障害を隔離して継続実行。新規保存数を返す。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature / Execution）テーブル群を DDL で定義。
  - テーブル群:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY, CHECK 等）とインデックスを含む。
  - init_schema(db_path) でディレクトリ自動作成と全テーブル作成（冪等）。get_connection で既存 DB への接続を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass により ETL の集計結果を表現（quality_issues を含む）。
  - 差分更新ヘルパー:
    - テーブル存在チェック、最大日付取得ユーティリティ。
    - 市場カレンダー調整ヘルパー（非営業日の補正）。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date。
  - run_prices_etl（株価差分ETL）を実装（差分更新、backfill_days のサポート、jq.fetch/save を利用）。設計上は backfill_days=3 がデフォルト、最小データは 2017-01-01。

### Performance
- API レート制御（固定間隔）により J-Quants への過剰リクエストを防止。
- ニュース保存はチャンク化してバulk INSERT、トランザクションでオーバーヘッド削減。
- DuckDB でのインデックスを作成（クエリパターンに対する最適化）。

### Security
- RSS 処理での SSRF 対策（リダイレクト検査・プライベートIP拒否）。
- defusedxml による XML パース時の安全化。
- レスポンスサイズ制限によるメモリ DoS / Gzip-bomb 対策。
- .env 読み込みはプロジェクトルート基準で CWD に依存しない実装（配布後の安全性向上）。

### Documentation / Examples
- config.py 内に使用例コメントを追加（from kabusys.config import settings）。
- 各モジュールに実装の設計方針や注意点をコメントで記載。

### Notes / Known limitations
- strategy/, execution/, monitoring/ パッケージは空の __init__.py しか含まれておらず、実際の戦略・発注・監視ロジックは今後の実装予定。
- pipeline.run_prices_etl 等はデータ取得→保存→品質チェックのフロー設計に従っているが、quality モジュールの実装（品質チェックルール）は別途提供される想定。
- jquants_client のリトライ対象は主に 408/429/5xx。429 では Retry-After ヘッダを優先。
- デフォルト設定や環境変数が不足している場合は ValueError が発生するため、.env.example を基に環境変数の準備が必要。

---

開発や導入にあたっての簡易チェックリスト:
- 必須環境変数を設定する（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
- DuckDB を使用する場合は DUCKDB_PATH を確認、初回は kabusys.data.schema.init_schema() を呼ぶ。
- 自動 .env 読み込みを無効化したいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

（以上）