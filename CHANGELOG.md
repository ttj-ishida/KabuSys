# Keep a Changelog

すべての変更はセマンティックバージョニングに従います。  
この CHANGELOG はリポジトリ内の現在のコードベースから推測して作成した初期リリースノートです。

## [0.1.0] - 2026-03-17

### 追加 (Added)
- パッケージ基盤
  - 初期パッケージ kabusys を追加。バージョンは __version__ = "0.1.0"。
  - 公開モジュールとして data, strategy, execution, monitoring をエクスポート。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env 読み込み:
    - プロジェクトルート検出（.git または pyproject.toml を基準）により cwd に依存せず自動ロード。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - テスト等で自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは `export KEY=value`、クォート（シングル／ダブル）のエスケープ、インラインコメントの扱いなどをサポート。
  - OS 環境変数保護（protected set）を利用した .env 上書き制御。
  - Settings に J-Quants、kabuステーション、Slack、DB パスなどのプロパティを提供。KABUSYS_ENV と LOG_LEVEL の検証ロジックを実装。
  - デフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API から日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する機能を実装。
  - レート制限: 固定間隔スロットリングで最大 120 req/min に対応（_RateLimiter）。
  - リトライロジック: 指数バックオフ付き最大 3 回リトライ（HTTP 408/429 および 5xx を対象）、429 の場合は Retry-After ヘッダを尊重。
  - 認証トークン自動リフレッシュ: 401 を受けた場合はリフレッシュして1回リトライ（無限再帰防止の allow_refresh フラグ）。
  - ページネーション対応で全ページを取得。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等（INSERT ... ON CONFLICT DO UPDATE）で実装。
  - データ取得時刻（fetched_at）を UTC で記録し、Look-ahead bias を抑止。
  - モジュールレベルで id_token をキャッシュしてページネーション間で共有可能。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news に保存する機能を実装（DEFAULT_RSS_SOURCES に Yahoo Finance を含む）。
  - セキュリティ対策:
    - defusedxml を使った XML パースで XXE/XML Bomb 対策。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベートアドレス検出、リダイレクト時の事前検証ハンドラ (_SSRFBlockRedirectHandler)。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を読み込み前後で検証、gzip 解凍後のサイズ検査も実施（Gzip bomb 対策）。
  - URL 正規化（小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）と記事 ID 生成（正規化 URL の SHA-256 の先頭32文字）で冪等性を保証。
  - テキスト前処理（URL除去、空白正規化）。
  - DuckDB への保存はトランザクションとチャンク分割で実行:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、新規挿入された記事IDを返す。
    - news_symbols のバルク保存、INSERT ... RETURNING で正確な挿入件数を返す。
  - 銘柄抽出: 正規表現で 4 桁数字を抽出し、known_codes に基づいてフィルタリングする extract_stock_codes を提供。
  - run_news_collection: 複数ソースの独立処理、既存記事スキップ、収集結果の要約を返す。

- スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DuckDB 用スキーマを定義（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブルを定義。
  - features, ai_scores など Feature 層の定義。
  - 信号・注文・トレード・ポジション・パフォーマンス等 Execution 層の定義。
  - 頻出クエリ用のインデックスを作成。
  - init_schema(db_path) 関数で親ディレクトリの自動作成も行い、全テーブル・インデックスを冪等に作成して DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない）。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - 差分更新を行う ETL 実行ロジックの基盤（説明文書に基づく設計）。
  - ETLResult dataclass を導入し、取得件数、保存件数、品質問題リスト、エラー一覧等を保持・シリアライズ可能に実装。
  - テーブル最終日取得ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - 非営業日の調整ヘルパー（_adjust_to_trading_day）を実装（market_calendar があれば過去方向で直近の営業日に調整）。
  - run_prices_etl 実装（差分・バックフィルロジック、_MIN_DATA_DATE の利用、J-Quants 関連呼び出しと保存）。  

### セキュリティ (Security)
- RSS パーサで defusedxml を使用し XML 攻撃を防止。
- ニュース取得時の SSRF 対策を多数実装:
  - リダイレクト先検査、スキーム制限、DNS 解決してプライベートアドレスを検出してブロック。
- HTTP クライアント処理でタイムアウトやサイズ制限を設け、メモリ DoS を軽減。
- .env 読み込み時に OS 環境変数を保護するしくみを導入。

### パフォーマンス・信頼性 (Performance & Reliability)
- API クライアントでレート制御・リトライ・トークン自動リフレッシュを実装し、運用耐性を向上。
- DuckDB への書き込みは冪等な UPSERT（ON CONFLICT DO UPDATE）やトランザクショナルなバルク INSERT を用い、同一データの重複・競合に強い設計。
- ニュース保存はチャンク毎に分割して一括 INSERT を行うことで SQL 長やパラメータ数を抑制。

### 既知の制限 / 未実装
- strategy, execution, monitoring パッケージは __init__.py のみが存在し、実装は含まれていない（将来的な実装対象）。
- pipeline モジュールは ETL 基盤と run_prices_etl を含むが、品質チェック quality モジュールや日次スケジューリング等の統合処理は外部依存または追加実装が必要。
- run_prices_etl の戻り値直後でコードが切れており（ファイル末尾が切れている）、完全な戻り値の構築や ETLResult 統合など残作業が想定される（現行コードは取得件数を返す実装が途中）。

### 破壊的変更 (Breaking Changes)
- なし（初期リリース）。

---

注: 本 CHANGELOG は提供されたソースコードの構造とコメントから推測して作成しています。リリースに含める正式な変更点や日付はリポジトリ管理者の判断で調整してください。