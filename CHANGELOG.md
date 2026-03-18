# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
リリースは日付順（最新が上）に記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-18
初回リリース。KabuSys のコア機能を実装しました。

### 追加
- パッケージ基盤
  - パッケージ初期化（kabusys.__init__）を追加。バージョンを "0.1.0" として公開。
  - モジュール構成: data, strategy, execution, monitoring のプレースホルダを用意。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込みを実装。プロジェクトルート検出（.git / pyproject.toml）に基づく自動ロードをサポート。
  - .env のパース実装（export 形式、クォート、インラインコメント対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを追加し、J-Quants / kabu ステーション / Slack / DB パス / 環境モード（development/paper_trading/live） / ログレベルのプロパティを定義。
  - 必須設定が欠落している場合に ValueError を送出する _require() を提供。

- J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API からのデータ取得機能を実装：
    - 株価日足（fetch_daily_quotes）
    - 財務データ（fetch_financial_statements）
    - JPX マーケットカレンダー（fetch_market_calendar）
  - ページネーション対応の取得ロジックを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）を実装。
  - リトライロジック（指数バックオフ、最大3回、対象ステータス: 408/429/5xx）を実装。429 の場合は Retry-After を優先。
  - 401 受信時にリフレッシュトークンで ID トークンを自動更新して一度だけリトライする仕組みを実装（トークンキャッシュ共有化）。
  - DuckDB への保存関数を実装（冪等: INSERT ... ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias のトレースを可能に。
  - 型変換ユーティリティ（_to_float, _to_int）を追加し、入力データの堅牢な変換を実現。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を取得して raw_news テーブルへ保存する機能を実装。
  - 主要機能:
    - fetch_rss: RSS 取得・XML パース（defusedxml を使用して XML 攻撃対策）
    - preprocess_text: URL 除去・空白正規化
    - 記事IDを URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を担保
    - レスポンスサイズ上限（10 MB）や gzip 解凍後のチェック（Gzip bomb 対策）
    - SSRF 対策: URL スキーム検証、リダイレクト先のスキーム/ホスト検証、プライベート IP 判定（DNS 解決を含む）
    - save_raw_news: チャンク化（_INSERT_CHUNK_SIZE）して INSERT ... RETURNING により新規挿入IDを返す（トランザクション内）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING、挿入数を正確に返す、トランザクション管理）
    - extract_stock_codes: テキストから 4 桁銘柄コードを抽出（known_codes でフィルタ、重複除去）
    - run_news_collection: 複数 RSS ソースを順次処理し、記事保存 → 銘柄紐付けまで実行。ソース毎に独立してエラーハンドリング。

  - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを登録。

- DuckDB スキーマ (kabusys.data.schema)
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）および Execution 層のテーブル定義を追加。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックス（頻出クエリ向け）を定義。
  - init_schema(db_path) により DB ファイルの親ディレクトリ作成、全テーブル・インデックスの冪等作成を実装。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の骨格を提供:
    - ETLResult データクラス（取得数 / 保存数 / 品質問題 / エラー収集 / ヘルパプロパティ）
    - テーブル存在チェック、最大日付取得ユーティリティ (_table_exists, _get_max_date)
    - market calendar を参照した営業日調整ヘルパー (_adjust_to_trading_day)
    - 差分更新用ヘルパ（get_last_price_date, get_last_financial_date, get_last_calendar_date）
    - run_prices_etl の開始実装（差分計算、backfill_days による後出し修正吸収、jquants_client との連携）
  - バックフィル設定や品質チェックとの連携設計（quality モジュールとの連携を想定）。

### セキュリティ（重要な設計上の配慮）
- news_collector で defusedxml を用いた XML パースと、レスポンスサイズ制限・gzip 解凍後サイズチェックを実装し XML Bomb / Gzip Bomb やメモリ DoS を防止。
- RSS 取得で SSRF 対策を複数レイヤーで実施（スキーム検証、プライベートIP判定、リダイレクト時の検査）。
- .env パーサは export 形式やクォート、コメントを安全に扱う。

### ロギングと観測性
- 主要処理にログを追加（info/warning/exception）。例: fetch/save の取得件数ログ、リトライ/HTTP エラー時の警告、トランザクション失敗時の例外ログ。

### 既知の制約 / 注意事項
- strategy および execution パッケージは初期化ファイルのみで具体的な戦略ロジック・発注ロジックは未実装（プレースホルダ）。
- pipeline の run_prices_etl はファイル末尾で途中で切れている（コードベースからの推測で ETL の主要部分は実装済みだが、完全な処理フローは今後整備する必要あり）。
- settings の必須値（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は環境変数または .env にて設定が必要。
- DuckDB の SQL をそのまま組み立てる箇所があるため（f-string を経由する DDL など）、外部入力を直接埋め込む用途では注意が必要（本コードでは開発用途を想定した安全な扱いを前提）。

---

今後の予定（提案）
- pipeline の各 ETL ジョブ（financials, calendar, news）の完全実装と品質チェック機能（quality モジュール）の実装・統合。
- strategy / execution の具体実装（シグナル生成、発注フロー、kabu ステーション API 統合）。
- テストカバレッジ拡充（単体テスト・統合テスト、外部依存のモック化）。
- ドキュメント（DataPlatform.md, API 使用方法、運用手順）の整備。