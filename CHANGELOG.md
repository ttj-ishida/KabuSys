Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

[Unreleased]


[0.1.0] - 2026-03-17
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基盤実装を追加。
- パッケージ公開情報
  - パッケージ名とバージョン: kabusys v0.1.0
  - パッケージトップレベル: src/kabusys/__init__.py に __version__ と __all__ を定義。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード:
    - プロジェクトルートを .git または pyproject.toml から検索して .env / .env.local を自動読み込み。
    - OS 環境変数を保護するため .env と .env.local の読み込み順序と上書き制御を実装（.env.local は override=True）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト向け）。
  - .env パーサを強化:
    - export KEY=val 形式対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理。
  - 必須設定取得用の _require、環境値バリデーション:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等を Settings プロパティで提供。
    - KABUSYS_ENV (development/paper_trading/live) と LOG_LEVEL の検証。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）は Path 型で提供。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得関数を実装:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - API のページネーションに対応（pagination_key を追跡）。
  - 認証とトークン管理:
    - get_id_token: リフレッシュトークンから idToken を取得する POST を実装。
    - モジュールレベルの ID トークンキャッシュと自動リフレッシュ（401 受信時に1回のみリフレッシュして再試行）。
  - レート制御とリトライ:
    - 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
    - リトライロジック（最大 3 回、指数バックオフ、408/429/5xx を対象、429 の Retry-After 優先）。
  - データ保存（DuckDB）:
    - save_daily_quotes, save_financial_statements, save_market_calendar：取得データを raw_* テーブルへ冪等的に保存（ON CONFLICT DO UPDATE）。
    - fetched_at を UTC ISO 形式で付与して「いつデータを取得したか」を追跡（Look-ahead Bias 対策）。
  - ユーティリティ関数:
    - _to_float, _to_int（安全な型変換、float 文字列→int の扱いを明示的に制御）。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからのニュース収集機能を実装:
    - fetch_rss: RSS の取得・XML 解析・記事抽出を実装（content:encoded 優先、description フォールバック）。
    - preprocess_text: URL 除去・空白正規化。
    - _normalize_url / _make_article_id: トラッキングパラメータ除去・URL 正規化・SHA-256(先頭32文字) による記事ID生成で冪等性を担保。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキーム/ホストを検査するカスタム HTTPRedirectHandler を導入。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストかを判定してアクセス拒否。
    - 安全対策:
      - defusedxml を使った XML 解析（XML Bomb 対策）。
      - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査。
      - User-Agent を設定（KabuSys-NewsCollector/1.0）。
    - DB への保存:
      - save_raw_news: INSERT ... RETURNING を用いて新規挿入された記事IDを返す（チャンク分割、1 トランザクション）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括で保存（ON CONFLICT DO NOTHING、RETURNING で実挿入数を取得）。
    - 銘柄コード抽出:
      - extract_stock_codes: テキスト中の4桁数字を抽出し、known_codes に基づきフィルタリング。
    - run_news_collection: 複数ソースを独立して収集し、記事保存と銘柄紐付けを実行する統合ジョブを追加。デフォルトソースに Yahoo Finance（business）を設定。
- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層のテーブル定義を追加:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）を定義してデータ整合性を担保。
  - 頻出クエリ向けのインデックス定義を追加（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) と get_connection(db_path) を公開。init_schema はディレクトリ作成やテーブル作成を行う（冪等）。
- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass を追加（取得数・保存数・品質問題・エラー一覧を集約）。
  - 差分更新ヘルパーと日付取得関数を追加:
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
    - _get_max_date, _table_exists
  - 市場カレンダー補助: _adjust_to_trading_day（非営業日を最も近い過去営業日に調整）。
  - run_prices_etl を実装（差分更新ロジック、バックフィル日数 default=3、最小データ日は 2017-01-01、J-Quants から取得して保存）。
  - 設計方針と実装により、品質チェック（quality モジュール）との連携を想定（品質問題は収集を継続して呼び出し元で対応可能）。
- テスト / モック性向上
  - news_collector._urlopen をモック差し替え可能にして単体テストを容易にするなど、外部依存の差し替えポイントを用意。

Security
- SSRF 対策を強化:
  - URL スキーム検証、リダイレクト先の事前検査、プライベート IP/ホストのチェックを実装。
- XML パースは defusedxml を使用し XML 攻撃から防御。
- HTTP レスポンスサイズに上限を設けてメモリ DoS を緩和。

Performance
- J-Quants API 呼び出しに RateLimiter（120 req/min）を導入しスロットリングで安定性を確保。
- 大量データ挿入はチャンク/バルク INSERT とトランザクションで効率化（news/save_* のチャンク処理、_INSERT_CHUNK_SIZE）。
- DuckDB のインデックスを追加し読み取りパフォーマンスを向上。

Notes / Implementation details
- リトライ戦略: 最大3回のリトライ、指数バックオフ（基底 2.0 秒）。429 の場合は Retry-After ヘッダを優先して待機時間を決定。
- トークン更新: 401 受信時は id_token を一度だけ再取得して再試行（無限再帰を防止）。
- 日時取り扱い: News の pubDate は UTC に正規化して保存、fetch 時刻は UTC ISO 文字列で記録。
- DB 保存の冪等性は主に SQL の ON CONFLICT を使って達成。
- デフォルト RSS ソース: Yahoo Finance（news.yahoo.co.jp の business カテゴリ）。

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Acknowledgements / References
- 実装上の設計方針や仕様はプロジェクト内の DataPlatform.md / DataSchema.md 等に基づくことを想定しています（ドキュメントへの言及をコード内コメントで保持）。

--- 

今後のリリースでは、ETL の品質チェック実装（quality モジュールの統合）、実行（execution）モジュールの注文送信ロジック、リアルタイム監視（monitoring）や Slack 連携の詳細実装、単体テスト・統合テストの追加を予定しています。