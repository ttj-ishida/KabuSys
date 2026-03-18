# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このリポジトリはセマンティックバージョニングに従います。

## [0.1.0] - 初回リリース
リリース日: 未指定

### Added
- パッケージ骨格の追加
  - パッケージ名: kabusys
  - __version__ を "0.1.0" として定義
  - サブパッケージ公開: data, strategy, execution, monitoring（空の __init__ でプレースホルダ）

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを実装
    - 自動ロード順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
    - プロジェクトルート検出: 現在ファイル位置から .git または pyproject.toml を探索
  - .env 解析の実装（export プレフィックス、クォート、インラインコメントなどに対応）
  - 環境読み込み時の上書き制御（override と protected）
  - 必須値チェック用ヘルパー _require()
  - Settings クラスを公開 (settings)
    - JQUANTS_REFRESH_TOKEN（必須）、KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH の既定パス
    - KABUSYS_ENV 値検証（development, paper_trading, live）
    - LOG_LEVEL 値検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - is_live / is_paper / is_dev の簡易プロパティ

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティ _request の実装
    - ベース URL、クエリ・JSON ボディ対応
    - レスポンス JSON デコードとエラーハンドリング
    - リトライロジック（指数バックオフ、最大 3 回）
    - ステータスに応じた再試行判定（408, 429, 5xx）、429 の Retry-After 優先
    - 401 発生時の自動 ID トークンリフレッシュを 1 回だけ実行（無限再帰対策あり）
  - 固定間隔のレートリミッタ実装（120 req/min に対応）
  - ID トークンのキャッシュ / 強制更新 API (get_id_token, _get_cached_token)
  - データ取得関数（ページネーション対応）
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
    - 各 fetch は fetched レコード件数をログ出力
  - DuckDB への冪等保存関数
    - save_daily_quotes（raw_prices テーブルへ ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials テーブルへ ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar テーブルへ ON CONFLICT DO UPDATE）
    - 保存時に fetched_at を UTC ISO8601 で記録、PK 欠損行はスキップして警告ログ

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を取得・正規化して DuckDB に保存する一連の処理を実装
  - 主な機能:
    - RSS の取得（fetch_rss）
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）
    - 記事 ID を正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成
    - テキスト前処理（URL 除去、空白正規化）
    - defusedxml による XML パース（XML Bomb 対策）
    - gzip 圧縮対応と最大受信バイト数制限（デフォルト 10MB、Gzip-bomb 対策）
    - SSRF 対策
      - 初回 URL / リダイレクト先のスキーム検証（http/https のみ許可）
      - リダイレクト時にプライベート/ループバック/リンクローカル/マルチキャストへの到達を拒否する _SSRFBlockRedirectHandler
      - ホストの IP 解決とプライベート判定（DNS 解決失敗は安全側で通過）
    - DB 保存の冪等化とバルク挿入
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id（チャンク分割・トランザクション）
      - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けをチャンクで挿入（RETURNING による挿入数取得）
    - 銘柄コード抽出 (extract_stock_codes): 正規表現ベースで 4 桁数列を抽出し既知コードセットでフィルタ
    - run_news_collection: 複数 RSS ソースをまとめて取得・保存・銘柄紐付けする統合ジョブ

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層のテーブル群を DDL として定義
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（PRIMARY KEY / CHECK / FOREIGN KEY 等）を付与
  - インデックス定義（頻出クエリパターンに合わせたインデックス）
  - init_schema(db_path): DB ファイルの親ディレクトリ自動作成、全テーブル・インデックスを作成して接続を返す（冪等）
  - get_connection(db_path): 既存 DB への接続を返す（スキーマ初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計に基づくユーティリティとジョブを実装
  - ETLResult データクラス: ETL 実行結果・品質問題・エラーを集約して保持、辞書化可能
  - テーブル存在チェック / 最大日付取得ユーティリティ
  - 市場カレンダーを用いた営業日調整ヘルパー (_adjust_to_trading_day)
  - 差分更新ヘルパー: get_last_price_date, get_last_financial_date, get_last_calendar_date
  - run_prices_etl: 日次差分 ETL（差分計算、backfill_days による再取得、fetch + save の呼び出し）
  - ETL の設計方針（backfill、品質チェックは fail-fast とせず呼び出し元に委ねる等）を実装

### Security
- ニュース取得での SSRF 対策を導入
  - リダイレクト先のスキーム検証とホスト/IP のプライベート判定を実行
  - defusedxml を用いた XML パースで XML 関連の攻撃を低減
  - レスポンスサイズと gzip 解凍後サイズの上限チェック（DoS 対策）
- J-Quants クライアントでのトークン自動リフレッシュ時に無限再帰を防ぐ設計

### Documentation
- 各モジュールに詳細な docstring を追加
  - 設計原則、処理フロー、エラーハンドリング方針、戻り値や例外条件などを明記

### Notes / Migration
- 初回利用時は DuckDB スキーマ初期化が必要: kabusys.data.schema.init_schema(db_path)
- 必須環境変数（未設定だと起動時に ValueError を送出）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 環境読み込みはプロジェクトルート検出に依存するため、パッケージ配布後も .env を使う場合はプロジェクトルートに .git か pyproject.toml を置くか、環境変数を直接設定してください
- run_news_collection / run_prices_etl 等は DuckDB 接続を引数に取る設計のため、ユニットテストではインメモリ DB (":memory:") を使用可能

### Breaking Changes
- 初回リリースのため該当なし

---

今後のリリースでは以下のような拡張が想定されています（例）:
- strategy / execution / monitoring の実装（現状はパッケージプレースホルダ）
- quality モジュールの実装と ETL による品質レポート出力
- Slack 通知やモニタリング連携の実装
- 単体テスト・統合テストの追加と CI 設定

もしリリース日や追加のリリースノート追記が必要であれば、日付やその他詳細を教えてください。