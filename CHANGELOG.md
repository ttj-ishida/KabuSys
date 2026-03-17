# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  

注: 以下の変更履歴は提供されたソースコードから推測して作成しています。

## [0.1.0] - 2026-03-17

初回リリース — KabuSys のコア機能を実装。

### 追加 (Added)
- パッケージ初期設定
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - サブパッケージ公開: data, strategy, execution, monitoring を __all__ に登録。

- 環境・設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出は .git または pyproject.toml を起点に行い、CWD に依存しない設計。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
    - 読み込み優先度: OS環境変数 > .env.local > .env。
  - .env パーサ実装:
    - export KEY=val 形式、単/二重クォート、エスケープ、インラインコメントの扱いに対応。
  - Settings クラスを提供:
    - J-Quants、kabuステーション、Slack、DBパスなど主要設定をプロパティで取得。
    - env（development/paper_trading/live）や log_level のバリデーションを実装。
    - デフォルトの DB パス（duckdb/sqlite）を提供。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装（_request）。
    - レート制限（120 req/min）を固定間隔スロットリングで実装（内部 RateLimiter）。
    - リトライ/指数バックオフ（最大 3 回、408/429/5xx を再試行対象）。
    - 401 受信時は自動的にトークンをリフレッシュして一度リトライ（再帰防止措置あり）。
    - ページネーション対応（pagination_key を用いた全件取得）。
    - JSON デコード失敗時の明確なエラー報告。
  - get_id_token() を実装（リフレッシュトークンから idToken を取得）。
  - データ取得関数を実装:
    - fetch_daily_quotes (株価日足: OHLCV)
    - fetch_financial_statements (四半期 BS/PL 等)
    - fetch_market_calendar (JPX マーケットカレンダー)
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - fetched_at は UTC で記録（ISO 8601, "Z"）。
    - 型変換ヘルパー (_to_float, _to_int) を実装して不正値を安全に扱う。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集し DuckDB に保存するパイプラインを実装。
    - デフォルト RSS ソース定義（例: Yahoo Finance）。
    - RSS 取得: fetch_rss 関数を実装。
      - defusedxml を利用した XML パース（XML Bomb 対策）。
      - gzip 対応と受信サイズ制限（MAX_RESPONSE_BYTES = 10 MiB）によるメモリ DoS 防止。
      - SSRF 対策:
        - URL スキーム検証 (http/https のみ許可)。
        - ホストのプライベート IP 判定（DNS 解決／直接 IP 判定）による拒否。
        - リダイレクト時にもスキームとプライベートアドレスを検査する専用ハンドラ実装。
      - 記事テキスト前処理（URL 除去、空白正規化）。
      - URL 正規化とトラッキングパラメータ除去（utm_ 等）。
      - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - DB 保存:
      - save_raw_news: チャンク化して INSERT ... RETURNING id を実行。新規挿入 ID のリストを返す。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（トランザクション、ON CONFLICT DO NOTHING）。
    - 銘柄コード抽出機能（4桁数字の抽出、known_codes によるフィルタ）。
    - 総合収集ジョブ run_news_collection を実装（ソースごとに独立したエラーハンドリング、既存記事はスキップ）。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataSchema に基づくスキーマを実装（Raw / Processed / Feature / Execution 層）。
    - raw_prices, raw_financials, raw_news, raw_executions など Raw 層。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed 層。
    - features, ai_scores など Feature 層。
    - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution 層。
  - 各テーブルに制約（PRIMARY KEY、CHECK、FOREIGN KEY）を付与。
  - 頻出クエリに備えたインデックスを定義。
  - init_schema(db_path) でディレクトリ作成から DDL 実行まで行い、冪等に初期化。
  - get_connection(db_path) を提供（既存 DB への接続）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計といくつかのヘルパーを実装:
    - 差分更新用: DB の最終取得日を取得するユーティリティ (get_last_price_date, get_last_financial_date, get_last_calendar_date)。
    - 営業日調整ヘルパー (_adjust_to_trading_day)。
    - ETLResult データクラス: 実行結果・品質問題・エラー一覧を保持し、辞書化する to_dict を提供。
    - run_prices_etl: 差分取得ロジック（backfill_days=3 デフォルト）を実装し、J-Quants から取得 → 保存までの流れを開始。
  - デフォルトの最小データ日付やカレンダー先読み日数などの定数を定義。

### セキュリティ (Security)
- XML パースに defusedxml を使用して XML 関連の脆弱性を軽減。
- ニュース取得で SSRF 対策を複数実装（スキーム検証、プライベートアドレス拒否、リダイレクト時の再検証）。
- RSS レスポンスの受信サイズ上限と Gzip 解凍後のサイズチェックによりメモリ攻撃を緩和。

### パフォーマンス (Performance)
- J-Quants API に対して固定間隔のレートリミッタを実装し、レート制限違反を防止。
- ニュース / 銘柄紐付けの挿入をチャンク化・トランザクション化して DB オーバーヘッドを削減。
- DuckDB DDL にインデックスを追加し、銘柄×日付等のスキャンを高速化。

### 既知の問題 / 注意点 (Known issues / Notes)
- run_prices_etl の戻り値型:
  - run_prices_etl は (取得レコード数, 保存レコード数) を返すことを意図していますが、現状ソースの末尾が "return len(records), " のように1要素のタプルになっており、期待するタプル長 (2) と一致しない可能性があります。テスト・修正が必要です。
- 一部モジュール（strategy、execution、monitoring）はパッケージに存在するが実装は空（プレースホルダ）。
- 単体テスト、統合テストはコードベースからは見つかりません。外部 API を扱う箇所はモックを使ったテストが推奨されます。
- DuckDB の SQL 文は直接組み立ててプレースホルダを埋める方法を多用している箇所があるため（特に可変長の VALUES 部分）、SQL インジェクション対策とパラメータ数の上限に注意が必要です。現在はチャンクサイズ制御で対処済み。

### 修正予定 / 今後の改善案 (Planned)
- run_prices_etl の戻り値修正と完全な ETL フロー（品質チェックへの統合、financials/calendar ETL など）の実装完了。
- strategy / execution / monitoring サブパッケージの実装（シグナル生成 → 発注 → ポジション管理 → モニタリング）。
- より詳細なログ、メトリクス出力（Prometheus など）の追加。
- ユニットテスト・CI の整備、API 呼び出しのモック用インターフェースの拡充。
- news_collector のフィード設定を動的に管理する仕組み（管理 UI や設定ファイル）や、既存記事検出の改善（類似記事統合など）。

---

参考:
- 環境変数キー（必須）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト DB パス: data/kabusys.duckdb（DuckDB）, data/monitoring.db（SQLite）

もし特定の変更点をより詳しく（例: jquants_client のリトライ挙動や news_collector の SSRF 実装）説明してほしければ教えてください。