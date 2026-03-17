# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニングに従います。  

## [0.1.0] - 2026-03-17

初回リリース — KabuSys の基盤となる自動売買データ基盤・収集・ETL コンポーネントを実装しました。

### 追加
- パッケージ基礎
  - パッケージ名: kabusys、バージョン: 0.1.0 を定義（src/kabusys/__init__.py）。
  - モジュール公開: data, strategy, execution, monitoring をエクスポート。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - プロジェクトルート検出は .git または pyproject.toml を起点に行い、CWD に依存しない実装。
  - .env パーサーを実装（export プレフィックス対応、クォート内エスケープ、インラインコメント処理等）。
  - 必須環境変数取得ヘルパー _require と Settings クラスを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の取得。
    - DUCKDB/SQLite のデフォルトパス設定。
    - KABUSYS_ENV (development, paper_trading, live) と LOG_LEVEL の入力検証とユーティリティプロパティ（is_live, is_paper, is_dev）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API データ取得（株価日足、財務データ、マーケットカレンダー）を行うフェッチ関数を実装:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
  - 認証: refresh token から id_token を取得する get_id_token を実装。
  - HTTP 層に以下を実装:
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - リトライロジック（最大3回、指数バックオフ、408/429/5xx を対象）。
    - 401 受信時の自動トークンリフレッシュ（1回のみ）とキャッシュ機構（モジュールレベル）。
    - JSON デコードエラーの明示的な検出と例外化。
  - DuckDB への保存関数を実装（冪等性を確保）:
    - save_daily_quotes, save_financial_statements, save_market_calendar。
    - INSERT ... ON CONFLICT DO UPDATE を利用して重複を排除・更新。
  - データ型パーシングユーティリティを提供: _to_float, _to_int（厳格な変換ルールを採用）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからニュース記事を収集し raw_news に保存するエンドツーエンド処理を実装。
    - fetch_rss: RSS の取得・XML パース・記事整形を実装（content:encoded 優先、guid を link の代替に利用）。
    - preprocess_text: URL 除去、空白正規化などの前処理。
    - URL 正規化と記事 ID 生成: トラッキングパラメータ除去、正規化後の SHA-256（先頭32文字）を記事 ID に使用。
    - セキュリティ対策:
      - defusedxml による XML パース（XML Bomb 等の対策）。
      - SSRF 対策: リダイレクト検査を含むスキーム検証、プライベート/ループバックアドレスの拒否。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
      - http(s) スキームの厳格チェック。
    - DB 保存: save_raw_news（INSERT ... RETURNING を用いたチャンク挿入、1 トランザクション）を実装。新規挿入された記事 ID を返す。
    - 銘柄紐付け: extract_stock_codes（4桁コード抽出）、save_news_symbols、内部バルク保管関数 _save_news_symbols_bulk を実装。
    - デフォルト RSS ソースの定義（例: Yahoo Business の RSS）。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層をカバーするテーブル群を定義。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY 等）を含むDDLを整備。
  - 頻出クエリ向けのインデックスを定義。
  - init_schema(db_path) による初期化関数を提供（親ディレクトリ自動作成、冪等性）。
  - get_connection(db_path) による既存 DB への接続取得。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult データクラスを実装（ETL 実行結果と品質問題・エラーの集約）。
  - 差分更新ヘルパー:
    - テーブルの最終取得日取得関数: get_last_price_date, get_last_financial_date, get_last_calendar_date。
    - 日付調整ヘルパー: _adjust_to_trading_day（非営業日の調整）。
  - run_prices_etl を実装（差分取得、バックフィル制御、jq.fetch_daily_quotes と jq.save_daily_quotes を呼び出し）。
  - 設計方針としてバックフィル期間（デフォルト 3 日）、最小取得開始日（2017-01-01）、カレンダーの先読み等を設定。

### セキュリティ
- RSS 処理で以下のセキュリティ対策を導入:
  - defusedxml による安全な XML パース。
  - SSRF 緩和 (スキーム検証、プライベート IP 拒否、リダイレクト検査)。
  - レスポンスサイズ制限、gzip 解凍後サイズ検査（Gzip Bomb 対策）。
- .env 読み込みに失敗した場合は警告を出して続行（致命的に失敗しない挙動）。

### 既知の実装上の注意点
- DB スキーマや一部 ETL フローは初版実装のため、運用に応じたマイグレーション・追加の品質チェックロジックや運用監視の実装を推奨します。
- run_news_collection は既知銘柄セット（known_codes）を受け取り、検出した銘柄との紐付けを行います。known_codes を渡さない場合は紐付けをスキップします。

### 変更点（履歴対象外）
- 本バージョンは初回リリースのため過去バージョンとの比較はありません。

---

今後のリリースでは以下を予定しています（例）:
- strategy / execution / monitoring モジュールの実装補完（オーダー送信、ポジション管理、リアルタイム監視）。
- 品質チェックモジュール（quality）による自動検出・修正フローの強化。
- 単体テスト・統合テストの追加、CI/CD の整備。
- ドキュメント(Usage, DataPlatform.md, DataSchema.md) と運用ガイドの充実。

もし CHANGELOG に含めたい追加情報や公開日を変更したい場合はお知らせください。