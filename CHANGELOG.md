# CHANGELOG

すべての重要な変更は Keep a Changelog の慣習に従って記載しています。  
リリース日はコードベースから推測した作成日を記載しています。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコアモジュール群を実装しました。主な内容は以下のとおりです。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージを追加。__version__ = 0.1.0 を設定。
  - 公開モジュール群: data, strategy, execution, monitoring（フォルダ構造は用意）。

- 設定管理 (kabusys.config)
  - .env/.env.local および OS 環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パースの実装:
    - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行コメントの考慮などに対応。
    - ファイル読み込み失敗時は警告を出力。
    - override / protected（OS 環境変数保護）オプションを実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level）をプロパティで取得・検証。

- J-Quants データクライアント (kabusys.data.jquants_client)
  - API クライアントを実装:
    - 基本 URL とエンドポイント（株価日足、財務、マーケットカレンダー）からデータ取得。
    - レート制限 (120 req/min) を守る固定間隔スロットリング（RateLimiter）を導入。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。対象はネットワーク起因の 408/429 と 5xx。
    - 401 受信時はトークンを自動リフレッシュして1回リトライする仕組みを搭載（無限再帰を防止）。
    - ページネーション対応（pagination_key を用いた継続取得）。
    - fetch_* 系関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供。
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar：ON CONFLICT DO UPDATE を用いて重複を排除し更新。
    - データ型変換ユーティリティ (_to_float, _to_int) を実装。
    - 取得時刻 (fetched_at) は UTC ISO 形式で保存して Look-ahead Bias のトレースが可能。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュースを収集して raw_news に保存するモジュールを実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防止）。
    - SSRF 対策: URL スキーム検証 (http/https のみ)、リダイレクト時のスキームおよびプライベート IP 検査（_SSRFBlockRedirectHandler）。
    - 最大全面サイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後のサイズ検査。
  - フィードパースと前処理:
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント除去）、SHA-256（先頭32文字）ベースの記事ID生成。
    - テキスト前処理（URL 除去、空白正規化）。
    - pubDate の RFC 2822 パース（UTC に正規化、パース失敗時は現在時刻で代替）。
  - DB 保存処理:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用い、実際に挿入された記事IDリストを返す（チャンク分割、1トランザクション）。
    - save_news_symbols, _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けをバルクインサートで行い、実挿入数を返す（ON CONFLICT DO NOTHING）。
  - 銘柄抽出:
    - 4桁数値パターンから既知銘柄セットに基づいて抽出する extract_stock_codes を実装。
  - run_news_collection:
    - 複数 RSS ソースを順次処理（ソース単位でエラーを捕捉して継続）。新規保存件数や銘柄紐付けを集約して保存。

- DuckDB スキーマ (kabusys.data.schema)
  - DataPlatform 設計に基づくスキーマ初期化を実装:
    - Raw / Processed / Feature / Execution レイヤーのテーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
    - 各種制約（PK/FOREIGN KEY/CHECK）を定義。
    - 頻出クエリに対するインデックスを作成。
    - init_schema(db_path) によりディレクトリ作成 → テーブル/インデックス作成を行う。get_connection を提供。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の基本ユーティリティと差分更新ロジックを実装:
    - ETLResult データクラス（取得数、保存数、品質問題、エラーなどを保持、辞書化メソッドを提供）。
    - テーブル存在チェックや最大日付取得ヘルパー（_table_exists, _get_max_date）。
    - 市場カレンダーに基づく営業日調整関数 (_adjust_to_trading_day)。
    - 差分更新用の最終日取得関数: get_last_price_date, get_last_financial_date, get_last_calendar_date。
    - run_prices_etl: 差分取得ロジック（最終取得日から backfill_days を考慮して再取得）、J-Quants からの fetch と保存を呼び出す。backfill_days のデフォルトは 3 日。
  - ETL 設計方針:
    - 差分更新（営業日単位）、backfill による後出し修正吸収、品質チェックは Fail-Fast ではなく呼び出し元が判断する方針。

### セキュリティ (Security)
- RSS パーシングで defusedxml を使用して XML関連攻撃を軽減。
- RSS フェッチにおいて SSRF 対策（スキーム検証、プライベートIP検査、リダイレクト検証）を実装。
- ネットワークリソース読み込みサイズを上限で制限（メモリ DoS 対策）。
- .env ロードで OS 環境変数を保護する protected 機能を提供。

### 依存関係（実装上想定）
- duckdb（データ格納）
- defusedxml（安全な XML パース）
- 標準ライブラリ（urllib, json, datetime, logging 等）

### 既知の注意点（注意）
- settings の必須環境変数が未設定の場合は ValueError を送出します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
- run_news_collection の銘柄抽出は known_codes を渡した場合のみ実行されます（既知銘柄に限定）。
- API レート制御やリトライ挙動は実装で保護していますが、運用にあたっては J-Quants の利用規約 / レート制限の最新仕様を確認してください。

---

今後の予定（未リリース）
- strategy / execution / monitoring の具体的実装（戦略ロジック、発注実行・監視機能）の追加。
- 品質チェックモジュール（kabusys.data.quality）との連携強化と詳細チェックの実装。
- ユニットテスト・統合テストの整備と CI 設定。

以上。