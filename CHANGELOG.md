# Changelog

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の慣習に従います。セマンティックバージョニングを使用します。

なお、本CHANGELOGは与えられたコードベースからの推測に基づき作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群とデータ基盤の初期実装を追加。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - エクスポート: data, strategy, execution, monitoring を __all__ として公開。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。読み込み順は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、パッケージ設置後も CWD に依存しない方式を採用。
  - .env パーサー実装（コメントや export プレフィックス、クォート内エスケープ、インラインコメント処理に対応）。
  - protected/override の概念を導入し、OS 環境変数の上書きを制御。
  - Settings クラスを提供（プロパティ経由で各種必須設定を取得）。
    - J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite） / 環境（development, paper_trading, live）/ログレベル（DEBUG..CRITICAL）など。
    - 環境値検証（許容値チェック、未設定時は ValueError を送出）。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API クライアントを実装。主に以下をサポート:
    - データ取得: 日次株価（OHLCV）、四半期財務データ、マーケットカレンダー。
    - レート制限の保護: 固定間隔スロットリングで 120 req/min を厳守（RateLimiter）。
    - リトライロジック: 指数バックオフ、最大リトライ回数 3、対象ステータスコード（408, 429, 5xx）に対応。
    - 401 受信時の自動トークンリフレッシュ（1 回まで）とトークンキャッシュの共有。
    - ページネーション対応（pagination_key を用いた全ページフェッチ）。
    - データ保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
      - DuckDB への冪等保存を実現（INSERT ... ON CONFLICT DO UPDATE）。
      - fetched_at を UTC ISO 形式で記録し、データ取得時点をトレース可能に。
      - PK 欠損行のスキップとログ出力。
    - ユーティリティ: 型安全な変換関数 _to_float / _to_int。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュース記事を収集して raw_news テーブルへ保存する一連の実装。
  - セキュリティ・堅牢性対策:
    - defusedxml を用いた XML パース（XML Bomb 等に対処）。
    - SSRF 対策: リダイレクト時のスキーム/ホスト検査を行う独自 HTTPRedirectHandler（_SSRFBlockRedirectHandler）。
    - URL スキーマ検証 (http/https のみ許可)、ホストがプライベートアドレスかチェックして遮断。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止、gzip 解凍後もサイズ検査。
  - URL 正規化:
    - _normalize_url によりスキーム/ホスト小文字化、トラッキングパラメータ（utm_*, fbclid 等）除去、フラグメント除去、クエリソートを実施。
    - 記事ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成し冪等性を保証。
  - RSS パース/前処理:
    - content:encoded を優先、description をフォールバック。URL除去・空白正規化を行う preprocess_text。
    - pubDate のパース処理（RFC 2822）、失敗時は警告とともに現在時刻で代替。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id で、実際に挿入された記事IDを返却。チャンク挿入と 1 トランザクション化。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク/トランザクションで保存し、実際に挿入された件数を返却。
  - 銘柄抽出:
    - extract_stock_codes: 正規表現で 4 桁数字を候補抽出し、known_codes にあるものだけを重複排除して返却。
  - run_news_collection: 複数ソースを巡回して収集・保存・銘柄紐付けを行う統合ジョブ。各ソースは独立してエラーハンドリング（1ソース失敗で他を継続）。

- データベーススキーマ (src/kabusys/data/schema.py)
  - DuckDB 用スキーマ定義および初期化関数を追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム制約（NOT NULL、型チェック、CHECK 制約、外部キー）を多数定義。
  - インデックスを想定した CREATE INDEX 文群（頻出クエリの高速化を目的）。
  - init_schema(db_path) によりファイル親ディレクトリ自動作成後、DDL を順序考慮して実行して接続を返す。get_connection() も提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計概要に従い差分取得・保存・品質チェックフローの基礎実装を追加。
  - ETLResult dataclass を定義（取得/保存件数、quality_issues、errors などを含む）。has_errors / has_quality_errors / to_dict をサポート。
  - テーブル存在チェックや最大日付取得のヘルパー関数（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダーに基づく取引日調整ヘルパー (_adjust_to_trading_day)。
  - run_prices_etl:
    - 差分更新ロジック: DB の最終取得日から backfill_days 分遡って再取得（デフォルト backfill_days=3）し、未取得分だけを取得。
    - _MIN_DATA_DATE（2017-01-01）を初回ロード時の下限として使用。
    - jquants_client の fetch/save を利用して取得・保存を行い、取得件数と保存件数を返却。

### セキュリティ (Security)
- XML パースに defusedxml を使用して外部攻撃を軽減。
- RSS フェッチでの SSRF 対策（スキーム検証、プライベートホスト拒否、リダイレクト検査）。
- HTTP レスポンスサイズと gzip 解凍後サイズの上限検査（メモリ DoS 防止）。
- .env パーサーはクォート内のエスケープを正しく処理し、誤った値の読み込みリスクを低減。

### 変更なし (Changed)
- （初回リリースのため該当なし）

### 修正なし (Fixed)
- （初回リリースのため該当なし）

### 既知の制約 / 備考 (Notes)
- jquants_client のリクエスト実装は urllib を使用。将来的に requests 等への移行やセッション/接続の改善を検討できる。
- run_prices_etl の戻り値行はコード断片のため、継続実装（例: 完全なタプル返却）や追加の品質チェック統合が必要になり得る。
- schema の外部キーや CHECK 制約は実行時の互換性に注意（既存データとの整合性確保が必要）。

---

過去の変更履歴はここに遡って追加していきます。リリースノートをより詳細化したい場合（例: 各関数の使用例、環境変数一覧、DDL の完全な説明など）、追加情報を指定してください。