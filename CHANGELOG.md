# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
フォーマット: [バージョン] - YYYY-MM-DD、カテゴリ: Added / Changed / Fixed / Security / Deprecated / Removed / Breaking Changes

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム「KabuSys」の基盤モジュール群を実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ基礎
  - パッケージ初期化と公開モジュール定義を追加（kabusys.__init__）。
  - バージョン番号を 0.1.0 に設定。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して検出）。
  - 自動読み込みを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - .env パーサの実装:
    - コメント行・export 形式のサポート、
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、
    - インラインコメントの取り扱い（クォート外で直前が空白/タブの場合に # をコメントと認識）、
    - 無効行は安全にスキップ。
  - 環境変数必須チェック用のヘルパー `_require` と Settings クラスを提供。
  - J-Quants / kabuステーション / Slack / DB パス / ログ・環境モード等のプロパティを実装（バリデーション含む）。
  - 有効な環境値セット（development, paper_trading, live）およびログレベル検証を実装。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - OHLCV、財務データ、マーケットカレンダーの取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - 認証トークンの取得・キャッシュ（get_id_token, モジュールレベルのトークンキャッシュ）。
  - レート制限ガード（固定間隔スロットリング: 120 req/min に基づく _RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408, 429, 5xx）。
  - 401 の際の自動トークンリフレッシュ（1回のみ）を実装。
  - JSON デコードエラーのハンドリングと詳細メッセージ出力。
  - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE を用いて重複を排除・更新。
  - レコード整形ユーティリティ（_to_float, _to_int）を追加し、不正値を安全に扱う。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を取得・前処理・保存する一連の機能を実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - セキュリティと堅牢性:
    - defusedxml を用いた XML パースで XML Bomb 等に対処。
    - SSRF 対策: URL スキーム検証、プライベートIP/ループバックの検出（DNS での解決を含む）、リダイレクト検査用のカスタムハンドラ（_SSRFBlockRedirectHandler）、最終 URL の再検証。
    - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ再チェック（Gzip bomb 対策）。
    - 許可されないスキームや大きすぎるレスポンスはログを残してスキップ。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url）。記事 ID は正規化 URL の SHA-256 の先頭32文字で生成（_make_article_id）して冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）を提供（preprocess_text）。
  - 銘柄抽出ロジック（4桁コード抽出）と既知コードフィルタ（extract_stock_codes）。
  - DB 保存はチャンク単位かつトランザクションで実行し、INSERT ... RETURNING で実際に挿入された行のみを返す実装（チャンクサイズ制限、ロールバック処理あり）。

- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与。
  - 頻出クエリ向けのインデックスを定義。
  - init_schema(db_path) によりファイルパスの親ディレクトリ自動作成とテーブル作成（冪等）を行う。get_connection() による単純接続取得も提供。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETL 実行結果を表す ETLResult データクラスを実装（品質チェック結果やエラーの集約、JSON化サポート）。
  - 差分取得のためのヘルパー関数（テーブル存在チェック、最大日付取得、営業日調整等）。
  - 差分更新の方針:
    - J-Quants のデータ開始日（2017-01-01）を定義。
    - デフォルトバックフィル日数 3 日（後出し修正吸収のため）。
    - 市場カレンダーの先読み（90日）。
  - 個別 ETL ジョブ（例: run_prices_etl）を実装し、最終取得日から差分のみを取得して保存するロジックを提供。品質チェックモジュールとの連携ポイントを用意（quality モジュール想定）。

### Security
- news_collector において SSRF 対策を強化:
  - URL スキーム/ホストの検証、リダイレクト時の検査、プライベートアドレスの遮断。
  - defusedxml を使った安全な XML パース。
  - レスポンス・解凍後サイズ制限で DoS 対策。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Breaking Changes
- （初回リリースのため該当なし）

補足:
- 現在の実装は基盤機能（データ取得・保存・スキーマ・ETL の骨組み）に注力しています。戦略（strategy）、実行（execution）、監視（monitoring）モジュールはパッケージ階層を用意していますが、個別実装は今後のリリースで追加予定です。
- APIの利用には環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）の設定が必要です。.env.example を参考に .env を準備してください。