CHANGELOG
=========

このCHANGELOGは「Keep a Changelog」の形式に準拠します。  
リリース日付は本リポジトリの現時点の状態（バージョン __version__ = 0.1.0）に基づいています。

[0.1.0] - 2026-03-17
--------------------

Added
- パッケージ全体
  - KabuSys: 日本株自動売買システムの初期実装を追加。
  - パッケージ公開モジュール: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring（strategy/execution は初期プレースホルダ）。
  - バージョン: 0.1.0

- 環境設定 (src/kabusys/config.py)
  - .env / .env.local からの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。  
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パースロジックを独自実装: export 形式、クォート/エスケープ、インラインコメント扱いなどに対応。
  - Settings クラスを提供し、環境変数をプロパティ経由で安全に取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパー: is_live / is_paper / is_dev

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しラッパーを追加:
    - レート制限制御（120 req/min）: 固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック: 指数バックオフ、最大リトライ回数 3、対象ステータス 408/429/5xx。
    - 401 受信時のトークン自動リフレッシュ（1回のみ）とトークンキャッシュ共有（モジュールレベル）。
    - ページネーション対応や JSON デコードエラーハンドリング。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期 BS/PL、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB 保存関数（冪等性を考慮した ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 取得時刻(fetched_at)を UTC で記録し、Look-ahead Bias を防止する設計。
  - 入力変換ユーティリティ: _to_float, _to_int（小数文字列等の扱いに注意）

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS 収集パイプライン:
    - fetch_rss: RSS フィードの取得・XML パース（defusedxml を使用）・記事抽出（title, content, pubDate, link）を実装。
    - セキュリティ対策: SSRF 対策（リダイレクト検査・プライベートIP拒否）、http/https スキーム限定、受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍の安全性チェック。
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）、記事ID は正規化 URL の SHA-256 の先頭32文字で生成し冪等性を確保。
    - テキスト前処理 (preprocess_text) と RFC2822 形式 pubDate パース（UTC 換算）。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING を利用して新規挿入された記事 ID を返却、チャンク化して一つのトランザクションで挿入。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING + RETURNING で正確な挿入数を取得）。
  - 銘柄コード抽出:
    - extract_stock_codes: 4桁数字パターンで抽出し、既知銘柄 set と照合して重複除去。
  - 統合ジョブ:
    - run_news_collection: 複数ソースを順次収集。各ソースは独立してエラーハンドリングし、known_codes に基づく銘柄紐付けを一括登録。

- スキーマ定義 & DB 初期化 (src/kabusys/data/schema.py)
  - DuckDB 用スキーマを定義（Raw / Processed / Feature / Execution の 3 層＋実行層）。
  - テーブル定義は制約（PRIMARY KEY, CHECK, FOREIGN KEY）を含む。
  - 頻出クエリ向けインデックスを作成。
  - init_schema(db_path): ディレクトリ作成→全テーブル・インデックスの作成（冪等）。
  - get_connection(db_path): 既存 DB への接続取得（初回は init_schema を推奨）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の差分更新戦略とユーティリティを追加:
    - ETLResult dataclass により fetch/save 数、品質問題、エラーの収集とシリアライズを提供。
    - 差分判定用ヘルパー: get_last_price_date, get_last_financial_date, get_last_calendar_date。
    - 市場カレンダーを考慮した調整: _adjust_to_trading_day（非営業日は直近の営業日に調整）。
    - run_prices_etl: 差分更新ロジック（バックフィル日数のデフォルト 3 日）と jquants_client からの取得→保存を実装（取得範囲自動算出、最小データ開始日対応）。
  - 設計方針: 差分更新、後出し修正吸収のための backfill、品質チェックは fail-fast とせず呼び出し側で対処。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security
- defusedxml を RSS パーサに導入し XML Bomb 等を軽減。
- RSS フェッチで SSRF 対策を導入（リダイレクト検査、プライベートアドレス検出、スキーム検証）。
- RSS レスポンスのサイズ上限（MAX_RESPONSE_BYTES）と gzip 解凍後のサイズ検査を追加しメモリ DoS を緩和。

Known issues / Notes
- run_prices_etl の戻り値:
  - run_prices_etl は (取得レコード数, 保存レコード数) のタプルを想定していますが、現行コードは最終行で saved を含めず "return len(records)," のように取得数のみを返す形になっています（戻り型の不一致／意図しない挙動の可能性）。ETL の呼び出し側では saved 数が期待通り返らないため注意してください。
- pipeline モジュールは quality モジュール（品質チェック）の API を参照しますが、本差分内に quality の実装が含まれていない場合があります（別ファイルで実装予定／別途提供）。
- strategy / execution / monitoring モジュールはパッケージ構造上存在しますが、現時点では実装が空または最小限です。戦略ロジックや発注実行ロジックは別途実装が必要です。
- テストについて:
  - HTTP コールや DB 操作をモックしやすいように設計されています（例: news_collector._urlopen の差し替え）。ユニットテスト・統合テストの追加を推奨します。

Migration / Usage notes
- 初回セットアップ:
  - DuckDB スキーマを作成するには init_schema(settings.duckdb_path) を実行してください（":memory:" も可）。
  - .env/.env.local をプロジェクトルートに配置すると自動で読み込まれます。CI／テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意: KABUSYS_ENV (development/paper_trading/live)、LOG_LEVEL、KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH
- RSS 収集:
  - デフォルト RSS ソースは Yahoo Finance の business カテゴリ。追加ソースは run_news_collection の sources 引数で指定可能。
  - 銘柄紐付けには known_codes を渡すことで抽出と登録が行われます。

今後の予定（例）
- pipeline の品質チェック（quality モジュール）実装の統合。
- strategy / execution 実装（実際の売買ロジック・kabu ステーション接続）。
- テストカバレッジ拡充および CI での自動チェック。
- run_prices_etl の戻り値修正（saved を確実に返す）および他の小さな整合性チェック。

---

変更点の補足や日付修正等が必要であればお知らせください。