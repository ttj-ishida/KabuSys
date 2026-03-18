# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

現在のパッケージバージョン: 0.1.0

## [0.1.0] - 2026-03-18
初回リリース（推定）。コードベースから推測される導入機能・設計方針・修正点をまとめています。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - モジュール構成: data, strategy, execution, monitoring（公開 API に含める設計）。
- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パース実装: export プレフィックス対応、クォート内のエスケープ対応、インラインコメント処理。
  - Settings クラスによる型付きプロパティ提供（J-Quants / kabuAPI / Slack / DB パス / 環境判定等）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値検査）、必須項目チェック（_require）。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティ (_request) を実装。JSON デコード・例外ハンドリングを含む。
  - レート制限制御: 固定間隔スロットリング実装（_RateLimiter、120 req/min を想定）。
  - リトライロジック: 指数バックオフ、最大試行回数 (_MAX_RETRIES = 3)、ステータスに応じた再試行（408/429/5xx 等）。
  - 401 応答時の自動トークンリフレッシュ（get_id_token を用いた1回リトライ、無限再帰回避フラグ allow_refresh）。
  - ページネーション対応のデータ取得関数: fetch_daily_quotes, fetch_financial_statements（pagination_key を利用）。
  - JPX マーケットカレンダー取得: fetch_market_calendar。
  - DuckDB へ冪等保存する save_* 関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）。
  - 取得メタ (fetched_at) を UTC で記録し、Look-ahead bias を防止する設計。
  - 型変換ユーティリティ: _to_float, _to_int（安全な変換・不正値は None）。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得・解析・DB 保存処理を実装（fetch_rss, save_raw_news, save_news_symbols 等）。
  - デフォルト RSS ソース設定（例: Yahoo Finance）。
  - 記事ID の生成: URL 正規化後の SHA-256（先頭32文字）を採用して冪等性を保証。
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_ 等）、フラグメント削除、クエリソート。
  - テキスト前処理: URL 除去、空白正規化（preprocess_text）。
  - RSS 日時パース: RFC2822 形式対応、パース失敗時は現在時刻で代替（UTC に変換）。
  - XML パースに defusedxml を使用（XML ボムや外部攻撃対策）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト時のスキーム・プライベートアドレス検査用ハンドラ (_SSRFBlockRedirectHandler) を導入。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストかを判定する関数 (_is_private_host)。
  - 応答サイズ制限（MAX_RESPONSE_BYTES = 10MB）、Content-Length 事前チェック、gzip 解凍後サイズ検査（Gzip bomb 対策）。
  - DB 保存処理の最適化:
    - INSERT ... RETURNING を用いた実際に挿入された記事IDの取得。
    - チャンク分割によるバルクINSERT（_INSERT_CHUNK_SIZE = 1000）。
    - トランザクションでラップし失敗時にロールバック。
  - 銘柄コード抽出: 正規表現による 4 桁数字抽出と既知コードフィルタ（extract_stock_codes）。
  - run_news_collection による複数ソースの統合収集ジョブ、既知銘柄紐付けの一括保存。
- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataSchema に基づくテーブル定義を実装（Raw / Processed / Feature / Execution 層）。
  - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）やデータ型を設定。
  - 頻出クエリに対するインデックスを定義。
  - init_schema(db_path) でディレクトリ作成・DDL 実行して DB を初期化可能。
  - get_connection(db_path) による接続取得（スキーマ初期化は行わない）。
- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計方針と差分更新ロジックを実装。
  - ETLResult データクラスにより ETL 実行結果（取得件数、保存件数、品質問題、エラー等）を表現。
  - テーブル存在チェック、最終取得日取得ユーティリティ (_table_exists, _get_max_date, get_last_price_date 等) を提供。
  - 市場カレンダーを用いた営業日調整ヘルパー (_adjust_to_trading_day) を実装。
  - run_prices_etl による株価差分 ETL（差分算出、backfill_days による再取得、jquants_client の fetch/save 呼び出し）。
  - 品質チェック統合フック（quality モジュールとの連携を想定、重大度の概念を保持）。
- その他ユーティリティ
  - モジュール内ログ出力（logger）を適切に配置。
  - 型ヒント・TypedDict を多用し可読性・静的解析性を向上。

### 変更 (Changed)
- 初回リリースのため該当なし（初期導入機能群）。

### 修正 (Fixed)
- 初回リリースのため該当なし（ただし各モジュールで入力検証・例外ハンドリングを強化）。

### 削除 (Removed)
- 該当なし

### 廃止予定 (Deprecated)
- 該当なし

### セキュリティ (Security)
- RSS/HTTP 層に対する安全対策を多く取り入れています:
  - defusedxml による XML パース（XML ボム対策）。
  - URL スキームの検証（http/https のみ）。
  - リダイレクト先の検査でプライベートアドレス到達を防止（SSRF 対策）。
  - レスポンス長の上限チェックと gzip 解凍後サイズチェック（メモリ DoS / Gzip bomb 対策）。
  - .env 自動ロード時の OS 環境変数保護（protected set を使用し上書きを制御）。

---

注記:
- 上記は提供されたコード内容からの推測に基づく CHANGELOG です。実際の変更履歴（コミットログ等）と照合のうえ必要に応じて調整してください。