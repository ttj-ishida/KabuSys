# Changelog

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングに従います。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買基盤のコア機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を導入。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に追加。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準にルートを探索（__file__ 基点の探索で配布後も動作）。
  - .env 読み込みの優先順位を OS 環境 > .env.local > .env に設定。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env パーサを実装（export 対応、シングル/ダブルクォートとエスケープ、インラインコメントの扱い）。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / システム設定（env, log_level 等）をプロパティで取得。値検証（有効な KABUSYS_ENV 値・LOG_LEVEL）を実装。
  - 必須環境変数が未設定の場合は ValueError を発生させ明示的に失敗させる _require() を提供。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - レート制限: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - リトライロジック: 指数バックオフ、最大3回リトライ（対象: 408, 429, 5xx）。429 時は Retry-After を優先。
  - 認証: refresh_token から id_token を取得する get_id_token()、モジュールレベルの id_token キャッシュ（ページネーション間共有）を実装。401 受信時は自動で一度トークンをリフレッシュして再試行。
  - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar を実装。冪等性を保つために INSERT ... ON CONFLICT DO UPDATE を使用。
  - 取得時刻（fetched_at）を UTC ISO 形式で保存して Look-ahead Bias のトレースを可能に。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正データの安全な処理を行う。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news に保存する機能を実装。DEFAULT_RSS_SOURCES に既定ソース（Yahoo Finance）を定義。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等に対する防御）。
    - HTTP/HTTPS スキームのみ許可し、その他スキーム（file:, mailto:, javascript: 等）を拒否。
    - SSRF 対策: リダイレクト時にスキームとホスト（IP）を検査するカスタム HTTPRedirectHandler を実装。ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定し、読み込み時・gzip 解凍後にチェック（Gzip bomb 対策）。
    - URL 正規化でトラッキングパラメータ（utm_*, fbclid, gclid など）を除去し、ID は正規化 URL の SHA-256 先頭32文字を採用して冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて実際に挿入された記事 ID を返す実装（チャンク・トランザクション化）。
  - news_symbols（記事と銘柄の紐付け）を一括保存する内部関数 _save_news_symbols_bulk を実装（重複除去・チャンク挿入・TRANSACTION）。
  - 銘柄コード抽出機能 extract_stock_codes を実装（4桁数字パターン、known_codes フィルタ、重複除去）。
  - run_news_collection: 複数 RSS ソースを順次処理し、ソース単位でエラーを隔離して収集を継続。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく多層スキーマを実装（Raw / Processed / Feature / Execution レイヤー）。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤー、prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤー、features, ai_scores 等の Feature レイヤー、signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤーを定義。
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）や推奨インデックスを用意。
  - init_schema(db_path) でディレクトリ作成（必要時）・テーブル作成を行う冪等な初期化を提供。get_connection(db_path) で既存 DB への接続を返す。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult データクラスを実装し、ETL 実行結果（取得数、保存数、品質問題、エラー）を集約・辞書化できるようにした。
  - 差分更新ロジック（最終取得日を基に date_from を自動算出、backfill_days による再取得）を実装。
  - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS）や最小データ開始日（_MIN_DATA_DATE）を定義。
  - テーブル存在チェック、最大日付取得ユーティリティを実装（_table_exists, _get_max_date）。
  - 非営業日調整ヘルパー _adjust_to_trading_day を実装。
  - run_prices_etl を実装（差分取得 → jq.fetch_daily_quotes → jq.save_daily_quotes）。引数で id_token を注入可能にしてテスト容易性を考慮。

### 変更 (Changed)
- （初回リリースのため変更履歴はなし）

### 修正 (Fixed)
- （初回リリースのため修正履歴はなし）

### セキュリティ (Security)
- news_collector において複数の SSRF / XML 攻撃対策を導入:
  - defusedxml を利用した安全な XML パース。
  - リダイレクト時にスキームとホスト検査を行うカスタムリダイレクトハンドラ。
  - ローカル/プライベートアドレスへのアクセスを拒否。
  - レスポンスサイズ制限・gzip 解凍後のサイズチェック（Gzip bomb対策）。
  - URL スキームの厳格な検証（http/https のみ）。

### 既知の注意点 (Notes)
- settings の必須環境変数未設定時は ValueError で明示的に失敗します。開発時は .env.example を参照して .env を用意してください。
- J-Quants API に対するレート制限・リトライは組み込まれていますが、実運用では API プロバイダの最新ルールを確認してください。
- DuckDB の SQL 文は文字列連結により動的に構築している箇所があります（プレースホルダを使用していますが、念のため取り扱いに注意してください）。（現状はパラメータがバインドされています）
- 初期リリースのため監視・エラー集約や運用ドキュメントは今後追加を予定。

---

今後のリリースでは、戦略実装（strategy）、注文執行（execution）、監視（monitoring）周りの詳細な実装追加、品質チェックモジュール（data.quality）の統合、テストカバレッジ向上、運用向けドキュメント整備を予定しています。