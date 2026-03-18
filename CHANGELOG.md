# Changelog

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣例に従います。
セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システムのコア基盤を実装しました。
以下はコードベースから推測される主要な追加機能・設計方針です。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（src/kabusys/__init__.py）。
  - package の公開サブモジュール: data, strategy, execution, monitoring（strategy/execution/monitoring は初期は空のパッケージとして用意）。

- 環境設定管理 (src/kabusys/config.py)
  - .env/.env.local ファイルおよび OS 環境変数からの設定自動読み込み機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索するため配布後も安定。
  - .env パーサを独自実装（export プレフィックス、クォート、インラインコメント、エスケープ処理に対応）。
  - Settings クラスを提供し、主要な設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパス）
    - KABUSYS_ENV（development/paper_trading/live の検証）とユーティリティ is_live / is_paper / is_dev
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- J-Quants データクライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装。
  - レートリミット制御: 固定間隔スロットリングで 120 req/min に対応する RateLimiter を実装。
  - 冪等性の DB 保存: DuckDB への保存は ON CONFLICT DO UPDATE を使用。
  - リトライロジック: 指数バックオフ、最大リトライ回数、HTTP ステータス（408/429/5xx）で再試行。
  - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回リトライする仕組み。
  - ページネーション対応（pagination_key を使った連続取得）。
  - 型変換ユーティリティ (_to_float / _to_int) を実装し不正値を安全に扱う。
  - get_id_token 関数（リフレッシュトークンから id_token を取得）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュース記事を収集し DuckDB の raw_news / news_symbols へ保存する一連処理を実装。
  - 主要機能:
    - fetch_rss: RSS の取得・XML パース（defusedxml を使用）・記事抽出
    - preprocess_text: URL 除去・空白正規化
    - URL 正規化と記事ID生成: 正規化した URL の SHA-256（先頭32文字）で記事 ID を生成し冪等性を担保
    - SSRF / セキュリティ対策:
      - http/https のみ許可
      - プライベート/ループバック/リンクローカル/マルチキャストアドレスへのアクセス防止（DNS 解決を含む判定）
      - リダイレクト先の検査を行うカスタムハンドラ（_SSRFBlockRedirectHandler）
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後サイズ検査（Gzip bomb 対策）
    - save_raw_news: INSERT ... RETURNING を用いて新規挿入された記事 ID を返す。チャンク挿入とトランザクション制御に対応。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING）し、実際に挿入された件数を返す。
    - 銘柄コード抽出: テキストから 4 桁数字を抽出し、既知コード集合でフィルタ（extract_stock_codes）。
    - run_news_collection: 複数 RSS ソースを巡回して収集・保存・銘柄紐付けを行う統合ジョブ（各ソースは独立してエラー処理）。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed テーブル。
  - features, ai_scores などの Feature テーブル。
  - signal_queue, orders, trades, positions, portfolio_performance などの Execution テーブル。
  - 適切なチェック制約（CHECK、NOT NULL、FOREIGN KEY）やインデックスを定義。
  - init_schema(db_path) で DB ファイルの親ディレクトリを自動作成し、全テーブルとインデックスを作成する初期化関数を提供。
  - get_connection(db_path) により既存 DB への接続を取得可能。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass により ETL 実行結果（取得数・保存数・品質問題・エラー）を統一表現。
  - 差分更新ヘルパー: DB 内最終取得日取得（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - 市場カレンダー調整: 非営業日の場合に直近営業日へ調整するユーティリティ (_adjust_to_trading_day)。
  - run_prices_etl: 差分更新ロジック（最終取得日 - backfill_days による再取得、_MIN_DATA_DATE フォールバック）を実装し、jquants_client の fetch/save を使ってデータを取得・保存する処理を用意。
  - 設計方針: 差分更新（デフォルト backfill_days=3）、品質チェック（quality モジュール連携）を考慮した構成。

### セキュリティ (Security)
- RSS / XML 関連:
  - defusedxml を利用して XML 大規模攻撃（XML bomb 等）への耐性を確保。
  - レスポンス読み取り上限（MAX_RESPONSE_BYTES）と gzip 解凍後のサイズチェックを実装。
- ネットワーク関連:
  - SSRF 対策としてスキーム検証、ホストのプライベートアドレス判定、リダイレクト時の事前検査を実装。
- 環境変数:
  - 機密トークンを必須プロパティとして明確化（取得失敗時は例外を投げる）。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### 既知の注意点 / 今後の改善候補
- ETL の品質チェック（quality モジュール）との統合は設計に含まれており、quality 側の実装およびパイプライン内でのハンドリングの調整が今後の作業となる可能性があります。
- strategy / execution / monitoring サブパッケージは初期は空で雛形が用意されています。戦略実装や発注フロー、監視機能は別途実装が必要です。
- J-Quants API 周りはネットワーク・認証に依存するため、統合テストやモックを用いた検証を推奨します。
- DuckDB への大量挿入時のパフォーマンス調整（チャンクサイズやインデックス設計のチューニング）は運用状況に応じて改善の余地あり。

---

以上がコードベースから推測できる本リリースの主な変更点です。必要であれば、各機能ごとにより詳細な使用例や API ドキュメント（例: Settings の使用例、ETL の実行手順、DuckDB スキーマのカラム説明など）を追加で作成します。どのセクションを優先して詳細化するか指示してください。