# Changelog

すべての重要な変更履歴をこのファイルに記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。  
このプロジェクトの初期公開リリースに相当する内容は、ソースコードの実装から推測して記載しています。

フォーマット:
- 変更は大分類（Added / Changed / Fixed / Security / etc.）ごとに整理しています。
- 可能な限り該当するモジュール名・関数名を明記しています。

## [Unreleased]
（次のリリースに向けた未リリースの変更はここに記載してください）

---

## [0.1.0] - 2026-03-17

初期リリース（アルファ/ベータ相当）。以下は実装されている主要機能・設計上の特徴と注意点の要約です。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開 API: data, strategy, execution, monitoring（各サブパッケージは初期骨子を含む）。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込み（優先順位: OS 環境 > .env.local > .env）。
  - 自動読み込みの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサ（_parse_env_line）を実装。export プレフィックス、クォート、インラインコメント等に対応。
  - Settings クラスを提供（プロパティ経由で設定値を取得）。例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスを指定）
    - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL（検証付き）
  - 必須設定未定義時は ValueError を送出する `_require` を実装。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 基本機能:
    - ID トークン取得: get_id_token()
    - ページネーション対応のデータ取得:
      - fetch_daily_quotes()
      - fetch_financial_statements()
      - fetch_market_calendar()
  - 信頼性機能:
    - 固定間隔スロットリングによるレート制限遵守（120 req/min）: _RateLimiter
    - 冪等性（DuckDB へ保存する際の ON CONFLICT DO UPDATE を前提にした save_* 関数）
    - リトライと指数バックオフ: ネットワークエラーや 408/429/5xx を対象に最大 3 回リトライ
    - 401 Unauthorized 受信時はトークン自動リフレッシュを1回実施して再試行（無限再帰防止の allow_refresh オプション）
    - レスポンスの JSON デコードエラーやレスポンス不正時の明示的な例外メッセージ
  - DuckDB 保存ユーティリティ:
    - save_daily_quotes(conn, records): raw_prices テーブルへの冪等保存（ON CONFLICT DO UPDATE）
    - save_financial_statements(conn, records): raw_financials テーブルへの冪等保存
    - save_market_calendar(conn, records): market_calendar テーブルへの冪等保存
  - データ型変換ユーティリティ: _to_float(), _to_int()（厳密な型変換ルール）

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード収集と前処理パイプライン:
    - fetch_rss(url, source, timeout): RSS 取得・XML パース・記事抽出
    - preprocess_text(), URL 正規化、トラッキングパラメータ除去、記事ID生成（SHA-256 の先頭32文字）
  - セキュリティ・堅牢性機能:
    - defusedxml を利用して XML Bomb 等から保護
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - プライベート/ループバック/リンクローカル/IP の検出とブロック（_is_private_host）
      - リダイレクト検査用カスタムハンドラ（_SSRFBlockRedirectHandler）
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）
  - DB 保存機能（DuckDB）:
    - save_raw_news(conn, articles): INSERT ... RETURNING を用いて新規挿入された記事IDリストを返す（チャンク化、1 トランザクション）
    - save_news_symbols(conn, news_id, codes): news_symbols への紐付け（INSERT ... RETURNING）
    - _save_news_symbols_bulk(conn, pairs): 複数記事の銘柄紐付けを一括挿入（重複除去・チャンク化）
  - 銘柄抽出:
    - extract_stock_codes(text, known_codes): テキストから4桁銘柄コードを抽出（既知コードフィルタ）

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層を想定した一連のDDLを定義
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切なチェック制約（CHECK）、PRIMARY KEY、外部キーを多用
  - 頻出クエリのためのインデックス定義（複数）
  - init_schema(db_path) でディレクトリ作成→テーブル作成→インデックス作成を行い、DuckDB 接続を返す
  - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない）

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新を前提とした ETL フロー（差分算出、保存、品質チェックフック）
  - ETLResult dataclass を導入し、処理結果・品質問題・エラーを集約
  - 市場カレンダーに基づく営業日調整ユーティリティ（_adjust_to_trading_day）
  - テーブルの最終日取得ユーティリティ:
    - get_last_price_date(), get_last_financial_date(), get_last_calendar_date()
  - 個別 ETL ジョブ雛形（run_prices_etl を含む。fetch → save の流れを実装）
  - 設定:
    - 最小データ開始日: 2017-01-01
    - カレンダー先読み: 90 日
    - デフォルトバックフィル: 3 日（後出し修正を吸収するため）

### Changed
- （初期リリースのため変更履歴はなし。将来のリリースでここに差分を記載）

### Fixed
- （初期リリースのため修正履歴はなし）

### Security
- ニュース収集における SSRF 対策と XML パース安全化（defusedxml）
- レスポンスサイズ制限と Gzip 解凍後のサイズ検査によりリソース枯渇攻撃を軽減
- .env パーサはクォートとエスケープに対応し、意図しない解釈を低減

### Notes / Caveats
- 現バージョンは初期実装であり、以下の点に注意してください:
  - strategy/execution/monitoring サブパッケージは骨子のみ（今後の実装が必要）。
  - jquants_client の HTTP 実装は urllib を使用しており、プロキシや詳細な接続設定を必要とする環境では追加実装が必要となる可能性があります。
  - DuckDB の SQL 文は標準的だが、本番移行時にはマイグレーション方針（DDL 変更時の互換性維持）を検討してください。
  - NewsCollector の既知銘柄リスト（known_codes）は外部で管理・供給する必要があります。
  - ETL の品質チェックモジュール（quality）は外部参照されている想定のため、実装/連携を行ってください。

---

開発・運用上の詳細や将来のマイグレーション（Breaking changes や API 互換性の方針など）は次回以降のリリースノートにて追記します。