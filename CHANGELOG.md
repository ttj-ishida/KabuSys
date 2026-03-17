# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、リリースごとの主要な追加・変更・修正点、及びセキュリティ関連の注意点を日本語でまとめたものです。

全般的な設計方針についてはソース内ドキュメント（モジュールの docstring）に従い、可観測性・冪等性・セキュリティ（SSRF 等）・API レート制御を優先して実装しています。

リリース履歴
------------

### [0.1.0] - 2026-03-17
初回公開リリース。

Added
- パッケージ基盤
  - kabusys パッケージの初期化（src/kabusys/__init__.py）とバージョン定義を追加（__version__ = "0.1.0"）。
  - サブパッケージ公開: data, strategy, execution, monitoring。

- 設定管理
  - 環境変数/.env 自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env/.env.local を自動ロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env のパース機構は export 形式やクォート、インラインコメント（#）に対応。
    - 既存の OS 環境変数を保護する protected パラメータを導入し、.env.local は override=True で上書き可能。
  - Settings クラスを実装し、必要な環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）やデフォルト値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH 等）を提供。
  - KABUSYS_ENV と LOG_LEVEL の検証を追加（許可値の検査とエラーメッセージ）。

- J-Quants API クライアント
  - jquants_client モジュール（src/kabusys/data/jquants_client.py）を追加。
    - API 呼び出しのための共通 _request 関数（JSON デコード、最大 3 回のリトライ、指数バックオフ）。
    - レート制御: 固定間隔スロットリングで 120 req/min を守る _RateLimiter を実装。
    - 401 Unauthorized 受信時にリフレッシュトークンから id_token を再取得して 1 回リトライ（無限ループ回避のため allow_refresh 制御）。
    - get_id_token、fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar を実装（ページネーション対応）。
    - DuckDB へ保存する save_daily_quotes、save_financial_statements、save_market_calendar を追加。すべて冪等（ON CONFLICT DO UPDATE）で fetched_at は UTC タイムスタンプで記録。
    - 型変換ユーティリティ _to_float / _to_int を実装し、データ不正時に安全に None を返す。

- ニュース収集モジュール
  - news_collector（src/kabusys/data/news_collector.py）を追加。
    - RSS フィードの取得・解析、記事前処理、DuckDB への保存・銘柄紐付けを実装。
    - セキュリティ・堅牢性:
      - defusedxml を使った XML パース（XML Bomb 等への防御）。
      - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカル/マルチキャストでないか検査、リダイレクト時の事前チェック用カスタムハンドラ（_SSRFBlockRedirectHandler）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、超過時はスキップ。gzip 圧縮に対応し、解凍後もサイズ検査を実施（Gzip bomb 対策）。
      - URL 正規化でトラッキングパラメータ（utm_*, fbclid 等）を除去し、記事 ID を正規化 URL の SHA-256（先頭32文字）で生成（冪等性確保）。
    - DB への保存:
      - save_raw_news はチャンク化 INSERT（INSERT ... RETURNING）を用い、トランザクションでまとめて挿入。実際に挿入された記事IDを返す。
      - save_news_symbols / _save_news_symbols_bulk により (news_id, code) ペアをチャンクで保存（ON CONFLICT DO NOTHING）し、挿入数を正確に返す。
    - 銘柄抽出:
      - テキストから 4 桁数字の候補を抽出し、既知銘柄セットでフィルタリングする extract_stock_codes を実装。
    - run_news_collection により複数ソースの収集ジョブを統合（ソース毎に独立してエラーハンドリングし、失敗しても他のソースは継続）。

- DuckDB スキーマ
  - schema モジュール（src/kabusys/data/schema.py）を実装。
    - Raw / Processed / Feature / Execution の多層スキーマを定義する DDL を追加（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
    - カラム制約（CHECK、NOT NULL、PRIMARY KEY、FOREIGN KEY）を設計に反映。
    - 頻出クエリのためのインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
    - init_schema(db_path) でディレクトリ自動作成およびテーブル/インデックスの冪等な作成を行う。get_connection() で既存 DB への接続を提供。

- ETL パイプライン
  - pipeline モジュール（src/kabusys/data/pipeline.py）を追加（ETL の骨組み）。
    - ETLResult dataclass による ETL 実行結果の構造化（target_date, fetched/saved カウント、quality_issues、errors）。
    - テーブル存在チェック、最大日付取得ユーティリティ、営業日調整（_adjust_to_trading_day）を実装。
    - 差分更新ロジックの骨格: get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - run_prices_etl の初期実装: 差分取得（最後の取得日から backfill_days 前から再取得）、J-Quants から取得して保存する流れを実装（backfill_days デフォルト=3、最小データ日 _MIN_DATA_DATE=2017-01-01）。
    - 設計上、品質チェックモジュール（quality）と連携して欠損やスパイク等の検出を想定（quality チェックは重大度に応じた扱いが可能）。

Changed
- （初回リリース）設計意図や実装上のトレードオフ（例: レート制御は固定間隔スロットリング、リトライは 3 回、gzip 上限チェック等）をソース内の docstring / コメントで明記。

Fixed
- （初回リリース）該当なし（初期実装のため）。

Security
- SSRF・XML攻撃対策を強化:
  - defusedxml を使用した安全な XML パース。
  - URL スキーム検証（http/https のみ）およびプライベート IP 判定による接続拒否。
  - リダイレクト先も検査するカスタムハンドラを導入し、内部ネットワーク到達を防止。
  - レスポンスサイズ上限を実装し、メモリDoS や Gzip bomb を防止。
- 環境変数の取り扱い:
  - OS 環境変数を保護する protected 機能により、意図しない上書きを防止。

Notes（実装上の注意・既知の制限）
- run_prices_etl 等パイプラインの一部は ETLフローの骨格として実装されています。品質チェック（quality モジュール）や他の ETL ジョブは別モジュール/続実装を想定しています。
- jquants_client の _request は urllib を使用しており、詳細な HTTP ロギングやセッション管理（接続プール等）は将来的な改善ポイントです。
- news_collector は記事 ID の冪等性を SHA-256（先頭32文字）で担保していますが、ソースにより同一記事の表現差分がある場合は重複判定のチューニングが必要になることがあります。
- DuckDB の SQL 文に生の文字列埋め込み（テーブル名や DDL）があり、使用時には DBPath 等の扱いに注意してください（init_schema は path の親ディレクトリを自動作成します）。

今後の予定（短期）
- pipeline における完全な差分 ETL（財務/カレンダーの定期取得）、品質チェック実装の連携、及びモニタリング・アラート機能の実装。
- strategy / execution / monitoring パッケージ内実装の充実（アルゴリズム、注文実行ラッパー、Slack 通知等）。
- 詳細なテスト（単体・統合）および CI/CD 設定の追加。

著記
- 各モジュール内の docstring に設計方針や利用方法の説明を記述しています。API の具体的利用例（settings、init_schema、jquants_client.fetch_*/save_*、news_collector.run_news_collection 等）はソースを参照してください。

未分類
- 破壊的変更（Breaking Changes）なし（初回リリース）。