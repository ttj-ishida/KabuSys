# CHANGELOG

すべての注目すべき変更点を記録します。本プロジェクトは Keep a Changelog の形式に準拠しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティに関する改善
- Performance: 性能改善
- Internal: 内部実装やリファクタリング、公開 API に影響しない変更

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買（KabuSys）用の基盤ライブラリを実装しました。主な機能・設計方針は以下の通りです。

### Added
- パッケージ基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。
  - パッケージ公開対象モジュール: data, strategy, execution, monitoring を __all__ に設定。
- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準にルートを探索する _find_project_root() を実装し、CWD に依存しない自動 .env ロードを実現。
  - .env の自動ロード順序: OS 環境 > .env.local (上書き) > .env（未設定のみ設定）。環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサーの強化: export プレフィックス対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、コメント処理など細かな仕様に対応した _parse_env_line() を追加。
  - 設定プロパティ（トークン、API ベース URL、Slack トークン／チャンネル、DB パス等）を用意。KABUSYS_ENV と LOG_LEVEL の値検証ロジックを実装（許容値チェック）。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* 関数を追加（ページネーション対応）。
  - HTTP リクエストユーティリティ _request() に以下を実装:
    - レート制御（固定間隔スロットリング）で 120 req/min を尊重（_RateLimiter）。
    - 再試行（最大 3 回）と指数バックオフ。408/429/5xx を再試行対象に設定。
    - 429 時は Retry-After ヘッダを優先。
    - 401 受信時はリフレッシュトークンで idToken を自動再取得して 1 回リトライ（無限再帰防止）。
    - JSON デコードエラー時の明示的エラー報告。
  - モジュールレベルの ID トークンキャッシュ実装（ページネーション間で共有）。
  - DuckDB への保存関数 save_daily_quotes, save_financial_statements, save_market_calendar を実装。ON CONFLICT DO UPDATE による冪等性を保持。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を取得し raw_news へ保存する機能を実装（DEFAULT_RSS_SOURCES を提供）。
  - セキュリティ・堅牢性:
    - defusedxml を使用して XML Bomb 等を防止。
    - SSRF 対策: リダイレクト時のスキーム検査とプライベートアドレス検出を行うカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）を実装。初回 URL と最終 URL の両方を検証。
    - 許可スキームは http/https のみ。プライベート/ループバック/リンクローカル/マルチキャストアドレスへのアクセスを拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズチェックを実装しメモリ DoS を軽減。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url、_TRACKING_PARAM_PREFIXES）、SHA-256 の先頭32文字を記事IDとして採用（冪等化）。
  - テキスト前処理（URL 除去、空白正規化）と pubDate の正確な UTC 変換（_parse_rss_datetime）。
  - DB 保存はトランザクションとチャンク化を行い、INSERT ... RETURNING による実際に挿入された ID の取得（save_raw_news、_INSERT_CHUNK_SIZE = 1000）。
  - 記事と銘柄コードの紐付け機能（extract_stock_codes、save_news_symbols、_save_news_symbols_bulk）。銘柄コード抽出は4桁数字かつ known_codes でフィルタ。
  - run_news_collection で複数ソースを順次処理し、ソースごとに独立したエラーハンドリングを実装。
- DuckDB スキーマ（kabusys.data.schema）
  - DataSchema.md に基づく多層スキーマを定義・実装（Raw / Processed / Feature / Execution レイヤー）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブルを定義。
  - features, ai_scores 等の Feature テーブルを定義。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 関連テーブルを定義。
  - インデックスを複数定義（頻出クエリを想定）。
  - init_schema(db_path) を実装し、親ディレクトリ自動作成、全DDL とインデックスを作成（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。
- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラスを導入（品質問題・エラー情報を含む）。
  - 差分更新を考慮したヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）とトレーディングデー調整関数 _adjust_to_trading_day を実装。
  - run_prices_etl を実装：差分更新ロジック（backfill_days デフォルト 3 日）、fetch & save の連携。初回ロードは _MIN_DATA_DATE=2017-01-01 を使用。
  - 品質チェックモジュール quality とのインターフェースを想定（重大度の取り扱い等）。
- その他
  - モジュール化されたパッケージ構成（data サブモジュール群、strategy/execution 空の __init__ 用意）。

### Security
- RSS/XML 関連で defusedxml を使用して XML 攻撃を軽減。
- SSRF 対策を複数実装（スキーム検査、ホストのプライベート判定、リダイレクト時検査）。
- .env 読み込み時に OS 環境変数を保護する protected キーセットを導入（.env.local/.env による上書き時の保護）。

### Performance
- J-Quants API 呼び出しに固定間隔レートリミッタを導入してリクエスト間隔を調整（120 req/min）。
- DB へのバルク挿入はチャンク化して一括実行、トランザクションでまとめてオーバーヘッドを削減。
- DuckDB 側に想定される頻出クエリ向けのインデックスを作成。

### Reliability / Robustness
- HTTP 通信のリトライ、指数バックオフ、Retry-After 利用、401 自動リフレッシュといった堅牢なエラーハンドリングを導入。
- 各種 API はページネーション対応で完全取得をサポート。ID トークンはモジュールレベルでキャッシュしてページネーション間で再利用。
- JSON デコード失敗時の明示的エラー報告や、.env パーサの堅牢な処理を追加。
- NewsCollector のレスポンスサイズチェック、gzip 解凍後のサイズ検査によりリソース枯渇を防止。

### Internal
- コード内に詳細な設計方針・設計原則のコメントを追加（Look-ahead バイアス対策、冪等性、テスト容易性の考慮など）。
- テスト容易性のため、news_collector._urlopen をモック差替可能に実装。

---

注:
- 本 CHANGELOG は提供されたコードベースを元に推測して作成しています。実際の CHANGELOG と異なる場合があります。必要があれば日付・項目の修正やリリースノートの追加を行います。