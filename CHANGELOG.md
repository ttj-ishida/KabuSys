# CHANGELOG

すべての変更は Keep a Changelog の仕様に準拠して記載しています。  
このファイルはプロジェクトの変更履歴を人間が読みやすい形でまとめたものです。

全般的な方針:
- セマンティックバージョニングを採用しています。
- 日付はリリース日を示します。

## [0.1.0] - 2026-03-17
初回リリース

### 追加
- パッケージのエントリポイントとバージョン情報を追加
  - src/kabusys/__init__.py にて __version__ = "0.1.0"、公開モジュール一覧 (__all__) を定義。

- 設定・環境変数管理モジュールを追加
  - src/kabusys/config.py
    - .env ファイル（.env, .env.local）および環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）を行い CWD に依存しない設計。
    - .env パーサを実装し、コメント行・export 構文・クォート文字列（バックスラッシュエスケープ含む）・インラインコメントに対応。
    - .env の上書き制御（override）と「保護キー」（protected）機能を実装し、OS 環境変数を保護。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - Settings クラスを公開（settings インスタンス）。J-Quants トークン、kabu API 設定、Slack トークン・チャンネル、DB パス、環境モード（development/paper_trading/live）やログレベルの検証ロジックを提供。
    - env / log_level の検証を行い不正値時に ValueError を送出。
    - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- J-Quants API クライアントを追加
  - src/kabusys/data/jquants_client.py
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - API 呼び出し共通処理 (_request) にレートリミット（120 req/min 固定間隔スロットリング）、リトライ（指数バックオフ、最大 3 回、408/429/5xx を対象）、429 の場合は Retry-After ヘッダ優先、ネットワークエラーのリトライ処理を実装。
    - 401 Unauthorized 受信時は自動的にリフレッシュトークンから id_token を再取得して 1 回リトライ（無限再帰防止）。
    - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）。
    - JSON デコード失敗時や HTTP エラーの詳細ハンドリングを実装。
    - DuckDB への保存関数を提供（save_daily_quotes, save_financial_statements, save_market_calendar）。いずれも冪等性を確保するため ON CONFLICT DO UPDATE を利用。
    - データ変換ユーティリティ（_to_float, _to_int）を実装し、型安全に空値や不正値を None に変換。

- ニュース収集モジュールを追加
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集し raw_news に保存する機能を実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection 等）。
    - 設計上の特徴:
      - defusedxml を利用して XML Bomb 等への耐性を確保。
      - SSRF 対策を強化: URL スキーム検査（http/https 限定）、ホストがプライベート/ループバック/リンクローカル/マルチキャストでないか検査（DNS 解決含む）、リダイレクト時にも検査を行うカスタムリダイレクトハンドラを実装。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入し、Content-Length チェックと実際の読み取りバイト数で超過を検出（gzip 解凍後も検査）。
      - gzip 圧縮レスポンス対応と Gzip bomb に対する検査。
      - 記事IDを正規化済 URL の SHA-256（先頭32文字）で生成し冪等性を担保（トラッキングパラメータ除去）。
      - トラッキングパラメータ（utm_ 等）除去とクエリソートによる URL 正規化を実装。
      - URL 前処理（URL 削除、空白正規化）を行う preprocess_text を提供。
      - DB 保存はチャンク化（_INSERT_CHUNK_SIZE）してトランザクションでまとめて実行し、INSERT ... RETURNING を用いて実際に挿入された行のみを返す（重複は ON CONFLICT でスキップ）。
      - 銘柄コード抽出機能（extract_stock_codes）を実装（4桁数字を候補、known_codes によるフィルタリング、重複排除）。
      - run_news_collection で複数ソースを独立して処理し、個々のソースで失敗しても他ソースへ影響しない堅牢な実行設計。

- DuckDB スキーマ定義と初期化モジュールを追加
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution 層を想定したスキーマを定義し、init_schema(db_path) で初期化可能。
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを定義。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブルを定義。
    - features, ai_scores など Feature 層のテーブルを定義。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等 Execution 層のテーブルを定義。
    - 各テーブルに適切なチェック制約（CHECK）、主キー、外部キーを設定。
    - 頻出クエリに備えたインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
    - get_connection(db_path) により既存 DB への接続を提供。
    - init_schema は db_path の親ディレクトリを自動作成し、:memory: のサポートあり。

- ETL パイプラインモジュールを追加
  - src/kabusys/data/pipeline.py
    - 差分更新を行う ETL 機能を実装するためのユーティリティ（最終取得日の取得: get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダーに基づく営業日調整ヘルパー (_adjust_to_trading_day) を提供。
    - run_prices_etl 等の差分 ETL ジョブの骨組みを実装（バックフィル日数や差分計算の方針を組み込んだ実装）。
    - ETL 実行結果を表す ETLResult データクラスを導入（品質問題やエラーメッセージの集約、シリアライズ用 to_dict を持つ）。
    - ETL は品質チェック（quality モジュール）と連携する設計（品質問題は収集して呼び出し元が判断）。

### セキュリティ
- RSS パーサに defusedxml を利用して XML パース攻撃から保護。
- ニュース取得モジュールで SSRF 対策を実装（スキーム検証、プライベートIPの排除、リダイレクト検査）。
- ネットワーク読み取りでレスポンスサイズ制限を導入しメモリ DoS を軽減。
- jquants_client の HTTP 実装でタイムアウトとリトライ制御、不正 JSON の検出を行い堅牢性を向上。

### 設計上の注意点 / マイグレーションノート
- DuckDB スキーマは初回は init_schema() を呼び出して作成する必要があります。既存 DB に接続する場合は get_connection() を使用してください（init_schema はスキーマ作成も行います）。
- .env の自動読み込みはデフォルトで有効です。テストや特殊環境で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants の id_token は内部でキャッシュされ、401 時に自動リフレッシュします。外部からトークンを注入してテストしたい場合は各関数の id_token 引数を利用してください（allow_refresh 制御あり）。
- news_collector の extract_stock_codes は known_codes（有効銘柄セット）に依存します。known_codes を渡さない場合は紐付け処理をスキップします。

### 既知の制約 / TODO（今後の改善候補）
- quality モジュールの実装詳細は本リリース範囲外の想定（pipeline は品質チェックと連携する設計になっているが、実際のチェックを行うモジュールの追加・拡充が想定される）。
- ETL の run_prices_etl の末尾の return が途中で切れている（コードベースに現状の部分的実装が見られます）。実運用前に完全な戻り値とエラー処理の確認が必要。
- ニュースの言語や文字エンコーディングの多様性に対する追加テストやエッジケースの強化を推奨。

---

今後はバグ修正、品質チェックの実装、監視＆実行（execution）周りの具体化（kabu ステーション連携や Slack 通知等）を中心にマイナーバージョンを追加していく予定です。