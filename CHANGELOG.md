# CHANGELOG

すべての重要な変更履歴はここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを追加。__version__ を "0.1.0" として公開。
  - パッケージの公開モジュール: data, strategy, execution, monitoring。

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび環境変数からの設定読み込みを自動化。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD に依存せず動作。
  - .env パース実装: export プレフィックス対応、クォート内エスケープ処理、インラインコメント処理など。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須設定取得ヘルパー _require と Settings クラスを提供（J-Quants トークン、Kabu API パスワード、Slack トークン/チャンネル、DB パス、環境 / ログレベル検証等）。
  - KABUSYS_ENV / LOG_LEVEL の入力検証とユーティリティプロパティ（is_live / is_paper / is_dev）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務（四半期 BS/PL）、市場カレンダー取得エンドポイントを実装（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - 認証トークン取得（get_id_token）とモジュールレベルのトークンキャッシュ（ページネーション時のトークン共有）。
  - レート制御（固定間隔 Throttling）で 120 req/min を保証する RateLimiter 実装。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx に対応）と 401 発生時の自動トークンリフレッシュ（1回のみ）。
  - 取得データの保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）。DuckDB への冪等保存（ON CONFLICT DO UPDATE）を実装。fetched_at を UTC ISO フォーマットで記録。
  - 型変換ユーティリティ (_to_float / _to_int) を実装し、不正値を適切に None に変換。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集する fetch_rss と DB 保存用 save_raw_news / save_news_symbols / _save_news_symbols_bulk を実装。
  - 記事ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を保証。トラッキングパラメータ（utm_* 等）を除去して正規化。
  - defusedxml を用いた XML パース（XML Bomb 対策）。
  - SSRF 対策: URL スキーム検証 (http/https のみ)、ホストがプライベート/ループバック/リンクローカルでないことを検証、リダイレクト時にも検証するカスタム RedirectHandler を導入。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - HTTP ヘッダ（User-Agent, Accept-Encoding）対応、Content-Length 事前チェック。
  - raw_news へのチャンク単位挿入（INSERT ... ON CONFLICT DO NOTHING RETURNING id）で実際に挿入された記事 ID を返却。
  - 銘柄コード抽出ロジック（4桁数字パターン）および既知コードフィルタリング（extract_stock_codes）。
  - run_news_collection による複数ソース一括収集。各ソースは独立してエラーハンドリング（1ソース失敗でも他は継続）。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataPlatform.md に基づくスキーマ初期化機能を実装（init_schema, get_connection）。
  - 3層構造のテーブル定義を追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルは適切な型制約・CHECK 制約・PRIMARY/FOREIGN KEY を定義。ON DELETE 動作を含む外部キー制約を設定。
  - 頻出クエリ向けのインデックスを作成（銘柄×日付、ステータス検索など）。
  - init_schema は親ディレクトリ自動作成、冪等的なテーブル作成を保証。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計に基づいた差分更新パイプライン基盤を実装。
  - ETLResult データクラスで実行結果・品質問題・エラーを集約。
  - 差分判定ユーティリティ（テーブル存在確認、最大日付取得）を追加。
  - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）。
  - 価格差分 ETL の run_prices_etl を実装（差分取得、backfill_days による再取得、取得→保存の流れ）。J-Quants クライアントを利用して取得し、保存は冪等で行う。
  - デフォルトの挙動: 最小データ開始日を定義（2017-01-01）、カレンダー先読み、デフォルトバックフィル日数=3。

### セキュリティ/堅牢性 (Security / Hardening)
- ニュース収集での SSRF 対策（スキーム/ホスト検証、リダイレクト時検査）。
- XML パースに defusedxml を採用（XML Bomb 等への防御）。
- HTTP レスポンスサイズ上限の導入（メモリ DoS / Gzip bomb 対策）。
- .env 読み込み時のファイル読み取り例外で警告を発する実装（安全にフォールバック）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意事項 / マイグレーションノート (Notes)
- 自動で .env / .env.local を読み込みます。自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマを初めて作成する場合は init_schema(db_path) を呼び出してください。既存 DB に接続するだけの場合は get_connection を使用してください。
- J-Quants API のレート上限（120 req/min）やリトライ/トークン更新の挙動に注意してください（クライアント実装に組み込み済み）。
- RSS のデフォルトソースは Yahoo Finance のビジネス RSS です（DEFAULT_RSS_SOURCES）。必要に応じて run_news_collection に sources 引数で差し替えてください。
- news_collector._urlopen はテスト時にモック差し替え可能です（ユニットテスト容易性を確保）。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの充実（戦略実装、発注実行、監視アラート）。
- 品質チェックモジュール quality の拡張と ETL への統合（現在は品質チェック呼び出しのための枠組みを用意）。
- 単体テスト・統合テストの追加、CI パイプライン構築。

お問い合わせやバグ報告、機能提案はリポジトリの Issue にお願いします。