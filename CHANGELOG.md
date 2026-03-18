# CHANGELOG

すべての重要な変更点は Keep a Changelog の形式に従って記載します。  
このファイルはコードベースの初期リリース（0.1.0）に基づき、実装内容から推測して作成しています。

## [Unreleased]
（今後の変更履歴をここに追記します）

## [0.1.0] - 2026-03-18
初回リリース（初期実装）。以下の主要機能・設計方針を実装しています。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージを追加。公開 API として data, strategy, execution, monitoring を __all__ でエクスポート。
  - バージョン: 0.1.0

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env および .env.local をプロジェクトルートから自動読み込み（CWD に依存しない探索ロジック）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env 読み込みで export KEY=val 形式、クォート、行内コメントなどに対応するパーサ実装。
  - 読み込み時の上書き挙動: OS 環境変数を保護する protected セット対応（.env.local は優先で上書き）。
  - Settings クラス（settings インスタンス）を提供。次のキーをプロパティで取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - 環境フラグ: is_live / is_paper / is_dev

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、四半期財務（BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装。
  - 認証: refresh_token から id_token を取得する get_id_token を実装。
  - HTTP リクエストユーティリティ:
    - API レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - リトライロジック（最大 3 回、指数バックオフ、408/429/5xx を対象）。
    - 401 発生時はトークンを自動リフレッシュして 1 回リトライ（再帰防止フラグ）。
    - ページネーション対応（pagination_key の継続取得）。
  - DuckDB への保存関数（冪等性を考慮）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE を使って保存。fetched_at は UTC タイムスタンプで格納。
    - save_financial_statements: raw_financials へ ON CONFLICT DO UPDATE。
    - save_market_calendar: market_calendar へ ON CONFLICT DO UPDATE。HolidayDivision を基に is_trading_day / is_half_day / is_sq_day を判定。
  - 型変換ユーティリティ: _to_float / _to_int（堅牢な変換、空値や不正値を None にする）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得し raw_news / news_symbols に保存する機能を実装。
  - 設計上の特徴:
    - 記事ID: URL 正規化後の SHA-256 の先頭32文字（utm_* 等のトラッキングパラメータを除去して正規化）。
    - defusedxml を使った XML パース（XML Bomb 等の対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にもスキームとホスト（プライベート / ループバック / リンクローカル / マルチキャスト）を検査するカスタム RedirectHandler。
      - DNS 解決してプライベートアドレスを検出（失敗時は安全側で通過）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - URL 正規化、本文前処理（URL 除去・空白正規化）。
    - bulk insert（チャンク処理）とトランザクションでの DB 保存（INSERT ... RETURNING を使用して実際に挿入された ID を取得）。
    - 銘柄コード抽出ロジック（4桁数字パターン、known_codes によるフィルタ）。
  - デフォルト RSS ソース: Yahoo Finance のビジネスカテゴリ（DEFAULT_RSS_SOURCES）

- DuckDB スキーマ定義 / 初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層に対応したテーブル DDL を定義。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（CHECK、PRIMARY KEY、FOREIGN KEY）とインデックスを定義（頻出クエリパターン向け）。
  - init_schema(db_path) によりディレクトリ作成 → 接続 → テーブル/インデックス作成を行う（冪等）。
  - get_connection(db_path) で既存 DB への接続を提供（初回は init_schema を推奨）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult データクラスを導入（結果、品質問題、エラー集約、to_dict）。
  - 市場カレンダー・差分更新ヘルパー:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _adjust_to_trading_day: 非営業日の調整ロジック（最大30日遡る）。
  - 差分更新方針:
    - 最終取得日を基に backfill_days（デフォルト 3 日）分さかのぼって再取得し API の後出し修正を吸収。
    - run_prices_etl を実装（date_from 未指定なら最終取得日 - backfill、最小データ日付は 2017-01-01 を使用）。
  - 品質チェックモジュール (quality) と組み合わせる設計（品質チェックは ETL を停止させず、呼び出し元で判断）。

### セキュリティ (Security)
- XML パースに defusedxml を採用して XML 関連攻撃を緩和。
- RSS フェッチでの SSRF 対策:
  - URL スキーム制限（http/https のみ）。
  - リダイレクト先のスキームおよびホスト検証（プライベート IP を拒否）。
  - Content-Length チェック、最大受信バイト数（10MB）を超えるレスポンスは拒否。
  - gzip 解凍後のサイズ検査を行い Gzip Bomb を検出して拒否。
- .env 読み込みでは OS 環境変数を保護（意図しない上書きを防止）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の制限・注意点 (Notes)
- init_schema を実行してから ETL / ニュース収集機能を利用してください（テーブルが存在しないと保存処理が失敗します）。
- J-Quants API 利用時は JQUANTS_REFRESH_TOKEN を必ず環境変数で設定する必要があります（Settings.jquants_refresh_token が必須）。
- rate limiter はモジュール単位の固定間隔スロットリングを採用しているため、マルチプロセス構成ではプロセス間の共有は行われません。クロスプロセスなレート制御が必要な場合は外部制御を検討してください。
- news_collector は既知の銘柄コードセット（known_codes）を渡すことで銘柄抽出を有効化します。known_codes を渡さない場合は紐付け処理をスキップします。
- jquants_client のリクエストでネットワークエラー・HTTP エラーが発生した場合は例外が送出されることがあります。pipeline.run_* 系はエラーを ETLResult.errors に格納する設計を想定していますが、呼び出し側でのエラーハンドリングを行ってください。
- 一部のユーティリティ（例: pipeline.run_prices_etl）の末尾が実装途中のような箇所が見られます（本 changelog は現時点の実装に基づく推測で作成しています）。実際のリポジトリでは追加実装や微調整が入る可能性があります。

### マイグレーション / 使用方法メモ
- DB 初期化:
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)
- ニュース収集:
  - from kabusys.data.news_collector import run_news_collection
  - run_news_collection(conn, known_codes=set_of_codes)
- ETL 実行（株価差分）:
  - from kabusys.data.pipeline import run_prices_etl
  - run_prices_etl(conn, target_date=date.today())

（この CHANGELOG はコード内容の静的解析と設計コメントから推測して作成しています。実際のリリースノートはコミット履歴やリリース担当者による確認の上で確定してください。）