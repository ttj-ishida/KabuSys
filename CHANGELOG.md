# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルはコードベースの内容から実装済みの機能・仕様を推測して作成しています。

## [0.1.0] - 2026-03-18

### 追加 (Added)
- 初期リリース。KabuSys のコア機能を実装。
- パッケージ構成
  - kabusys パッケージの公開 API を定義（__version__ = 0.1.0、data/strategy/execution/monitoring を公開）。
  - strategy、execution パッケージのプレースホルダを追加。

- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env ファイルの堅牢なパーサを実装（コメント、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなど）。
  - OS 環境変数の上書き制御（protected set）をサポート。
  - Settings クラスを実装し、以下の設定をプロパティ経由で取得可能：
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパープロパティ: is_live/is_paper/is_dev

- J-Quants API クライアント (kabusys.data.jquants_client)
  - ベース機能:
    - API ベース URL を使用した HTTP リクエスト実装（JSON パース、タイムアウト付き）。
    - レート制限対応（固定間隔スロットリング、デフォルト 120 req/min）。
    - 冪等保存サポート：DuckDB への保存処理は ON CONFLICT DO UPDATE を利用。
  - 認証:
    - リフレッシュトークンから id_token を取得する get_id_token() を実装。
    - モジュールレベルで id_token をキャッシュしページネーション間で共有。
    - 401 を検出した場合の id_token 自動リフレッシュ（1 回のみ）を実装。
  - リトライ／障害対策:
    - 指数バックオフによる再試行（最大 3 回、408/429/5xx を対象）。
    - 429 の場合は Retry-After ヘッダを優先。
    - ネットワークエラー時の再試行とログ出力。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB 保存関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar（fetched_at を UTC で記録し、PK に基づく ON CONFLICT DO UPDATE の冪等挿入）
  - ユーティリティ:
    - 型変換ユーティリティ _to_float / _to_int（空値や不正値に対して安全に None を返す）
  - ログ出力による取得件数・保存件数の記録と警告出力。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS 収集パイプラインの実装。
  - セキュリティ・堅牢性:
    - defusedxml を用いた安全な XML パース（XML Bomb 等の緩和）。
    - SSRF 対策:
      - リダイレクト時のスキーム検証・プライベートアドレス検出を行うカスタム HTTPRedirectHandler を実装。
      - フェッチ前にホストがプライベートアドレスでないかを検証。
      - 許可スキームは http/https のみ。
    - レスポンス最大バイト数上限（デフォルト 10 MB）によりメモリ DoS を緩和。
    - gzip 圧縮応答の解凍とサイズ再検査（Gzip bomb 対策）。
  - URL 正規化と記事 ID:
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）を除去してクエリをソートする _normalize_url()。
    - 正規化 URL から SHA-256 ハッシュの先頭 32 文字で記事 ID を生成 (_make_article_id)。
  - テキスト前処理:
    - URL 除去、空白正規化、トリミングを行う preprocess_text。
  - RSS パース:
    - content:encoded (namespaced) を優先的に利用し、description をフォールバック。
    - pubDate の RFC2822 パースと UTC 変換（失敗時は警告と現在時刻で代替）。
  - DuckDB への保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を使用し、実際に挿入された記事 ID を返す。チャンク単位挿入とトランザクション管理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを INSERT ... ON CONFLICT DO NOTHING RETURNING で保存し、挿入件数を返す。トランザクションでまとめて処理。
  - 銘柄コード抽出:
    - 正規表現による 4 桁コード抽出 (例: 7203) と known_codes に基づくフィルタリング（重複除去）。
  - 統合収集ジョブ:
    - run_news_collection により複数 RSS ソースを順次収集、保存し、known_codes が与えられた場合は新規記事に対して銘柄紐付けを一括挿入。各ソースは独立して例外処理（1 ソース失敗でも他を継続）。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataPlatform の三層設計に基づきテーブル定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）を設定。
  - 頻出クエリ向けのインデックスを作成（idx_prices_daily_code_date など）。
  - init_schema(db_path) により DB ファイルの親ディレクトリを自動作成し、すべての DDL とインデックスを実行して接続を返す（冪等）。get_connection() で既存 DB に接続可能。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラスを実装し、ETL のメタ情報（取得件数、保存件数、品質問題、エラーリスト等）を保持・辞書化可能。
  - テーブル存在チェック・最大日付取得のユーティリティを実装（_table_exists, _get_max_date）。
  - 市場カレンダーを考慮した trading day 調整ヘルパー (_adjust_to_trading_day) を提供。
  - 差分更新に関するヘルパー関数:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - 株価差分 ETL ジョブ run_prices_etl を実装（差分の自動算出、backfill_days による後出し修正吸収、jquants_client からの取得と保存の呼び出し、ログ出力）。（ETL の品質チェック呼び出しは quality モジュールを利用する設計想定）

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### 既知の制約・注意点 (Notes)
- news_collector と jquants_client はネットワーク I/O に依存するため、ユニットテストではネットワークコールをモックする必要がある（_urlopen や id_token キャッシュを差し替え可能）。
- DuckDB スキーマは多くの CHECK 制約や FOREIGN KEY を含むため、既存のデータ構造と合わせて初回マイグレーションを注意深く行う必要がある。
- pipeline.run_prices_etl は差分ロジックを含むが、他の ETL ジョブ（財務データ・カレンダー等）や品質チェックの統合は今後の実装・テストで確認が必要。
- strategy / execution パッケージは現時点では実装がないか最小構成のため、実運用での発注ロジック・戦略評価は未実装。

### 依存ライブラリ
- duckdb
- defusedxml
- Python 標準ライブラリ（urllib, logging, datetime, pathlib, ipaddress 等）

---

今後のリリースで期待される項目（例）
- ETL の一括実行 CLI / Scheduler の追加
- 品質チェック（quality モジュール）の具体実装とレポート機能
- strategy / execution の具体的なアルゴリズム実装と kabu ステーション連携
- テストカバレッジ拡充・CI 設定

（以上）