# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買プラットフォーム「KabuSys」のコアライブラリを提供します。主にデータ取得・保存・ETL・ニュース収集・設定管理の機能を含みます。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0
  - サブパッケージ公開: data, strategy, execution, monitoring（__all__）
  - 基本的なモジュール構造を定義（src/kabusys 以下）

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装
    - 読み込み順序: OS 環境 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
    - プロジェクトルートを .git または pyproject.toml を基準に探索（__file__ ベースで探索）
    - .env パーサーは export プレフィックス、クォート、エスケープ、インラインコメント等に対応
    - .env 読み込み時に OS 環境変数を保護する機能（protected set）
  - Settings クラスにより型付けされたプロパティを提供
    - J-Quants / kabuステーション / Slack / データベースパス / システム設定等
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL の値検証
    - duckdb / sqlite のデフォルトパス設定

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API への HTTP ユーティリティを実装（GET/POST、JSON デコード）
  - 認証トークン取得（get_id_token）とモジュール内のトークンキャッシュ
  - レートリミッタを実装（120 req/min 固定、固定間隔スロットリング）
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対象）
  - 401 受信時はトークンを自動リフレッシュして1回リトライ
  - データ取得関数
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - Look-ahead bias 対策として fetched_at を UTC タイムスタンプで保存
  - 入力変換ユーティリティ (_to_float, _to_int) を追加

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集の実装（デフォルトソース: Yahoo Finance ビジネス RSS）
  - セキュリティ・堅牢性対策
    - defusedxml を用いた XML パース（XML Bomb 等対策）
    - SSRF 対策: URL スキーム検証 (http/https 限定)、ホストがプライベートかチェック、リダイレクト時にも検証
    - レスポンス最大読み取りサイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 展開後のサイズ検査
    - _SSRFBlockRedirectHandler と専用 opener を利用（テスト時は _urlopen をモック可能）
  - テキスト前処理（URL 除去、空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保（utm_* 等のトラッキングパラメータ除去）
  - RSS パースから NewsArticle 型（TypedDict）を生成する fetch_rss 実装
  - DuckDB への保存
    - save_raw_news: バルク INSERT with RETURNING を用いて実際に挿入された記事IDを返す。チャンク単位で1トランザクション。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING、INSERT ... RETURNING で実数を返す）
  - 銘柄コード抽出機能 extract_stock_codes（正規表現による4桁候補、known_codes フィルタ、重複除去）

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataSchema に基づく DB スキーマを定義・初期化する init_schema を実装
  - 層構造に対応したテーブル群を作成（Raw / Processed / Feature / Execution）
    - 例: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等
  - 各種制約（PRIMARY KEY, FOREIGN KEY, CHECK）やインデックス定義を含む（頻出クエリ向け）
  - get_connection: 既存 DB への接続取得（初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass により実行結果を構造化して返却（品質問題・エラー収集含む）
  - 差分更新ヘルパー（テーブルの最終日付取得 get_last_price_date / get_last_financial_date / get_last_calendar_date）
  - 市場カレンダー調整ヘルパー (_adjust_to_trading_day)
  - run_prices_etl 等の差分更新ロジックを備え、以下設計方針を反映
    - 最終取得日から backfill_days 日分を再取得して API の後出し修正を吸収
    - 既存の保存関数は冪等（ON CONFLICT）でデータ上書き可能
    - 品質チェックモジュール (quality) と連携可能な設計

### セキュリティ
- RSS XML パースに defusedxml を使用し XML 攻撃に対処
- RSS フェッチでの SSRF 対策を実装（スキーム検証・ホストのプライベートアドレス検出・リダイレクト時の検査）
- レスポンスサイズ上限と gzip 解凍後サイズチェックによりメモリ DoS を軽減
- .env 読み込みで OS 環境変数を保護（上書き防止）する仕組み

### ドキュメント / 設計ノート（コード内コメントより）
- J-Quants のレート制限（120 req/min）を厳守するため固定間隔スロットリングを採用
- リトライ処理は指数バックオフを用い、429 の Retry-After ヘッダを優先
- データの取得時点（fetched_at）を UTC で記録し、参照バイアスを可視化
- DB 保存は可能な限り冪等性を保つ（ON CONFLICT DO UPDATE / DO NOTHING）
- ニュース記事の ID 生成は URL 正規化後のハッシュで行い、トラッキングパラメータは除去

### 既知の挙動 / 注意点
- settings のプロパティは未設定時に ValueError を送出する（必須の環境変数が不足している場合）
- J-Quants クライアントのトークン取得は settings.jquants_refresh_token に依存
- news_collector の初期 RSS ソースは DEFAULT_RSS_SOURCES に定義されており、必要に応じて上書き可能
- DuckDB の初期化時は親ディレクトリが自動作成される（":memory:" は例外）
- ETL の品質チェック機能は quality モジュールに依存（本リリースでは quality が別モジュールとして参照されている）

### 修正
- （初回リリースため該当なし）

### 削除
- （初回リリースため該当なし）

### 破壊的変更
- （初回リリースため該当なし）

---

備考:
- 本 CHANGELOG はリポジトリ内のソースコードから機能・設計を推測して作成しています。リリースノートや実際の運用ドキュメントは、実際の変更履歴やリリース手順に基づいて適宜追補してください。