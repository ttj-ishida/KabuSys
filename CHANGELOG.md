# CHANGELOG

すべての注目すべき変更点を記録しています。本ファイルは Keep a Changelog の形式に準拠しています。意図的に後方互換性を保つよう設計されていますが、各リリースの詳細を確認してください。

## [0.1.0] - 2026-03-17

初回リリース。

### 追加
- パッケージのエントリポイントを追加
  - kabusys.__init__ を実装（__version__ = 0.1.0、公開モジュール: data, strategy, execution, monitoring）。

- 環境設定管理モジュールを追加（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込みを自動化（プロジェクトルート検出: .git または pyproject.toml）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env の行パーサーを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理）。
  - Settings クラスを追加し、以下のプロパティを提供:
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id
    - duckdb_path, sqlite_path
    - env（development / paper_trading / live 検証）、log_level（DEBUG/INFO/... 検証）、is_live / is_paper / is_dev ヘルパー

- J-Quants API クライアントを追加（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得 API を実装（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - トークン取得関数 get_id_token（refreshtoken -> idToken）。
  - レート制御（_RateLimiter）を導入し、120 req/min の制限を固定間隔スロットリングで遵守。
  - リトライ戦略を実装（指数バックオフ、最大3回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを尊重。
  - 401 受信時はトークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止の allow_refresh フラグ）。
  - ページネーション対応（pagination_key を用いた反復取得、モジュールレベルの id_token キャッシュ共有）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。いずれも冪等性のため ON CONFLICT DO UPDATE を使用。
  - データ型変換ユーティリティ (_to_float / _to_int) を実装し、変換失敗や不正値を安全に扱う。
  - レスポンス JSON デコード失敗時の明確なエラー報告。

- ニュース収集モジュールを追加（kabusys.data.news_collector）
  - RSS フィードから記事を取得し raw_news に保存するフローを実装（fetch_rss, save_raw_news）。
  - 記事IDは URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を確保（_normalize_url, _make_article_id）。
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_*, fbclid など）の除去、フラグメント削除、クエリパラメータソートを実施。
  - セキュリティ対策:
    - defusedxml を使い XML Bomb 等を防止。
    - SSRF 対策: リダイレクト時にスキームとプライベートアドレスを検査する _SSRFBlockRedirectHandler と事前ホスト検査（_is_private_host）を導入。
    - 許可スキームは http/https のみ（_validate_url_scheme）。
    - レスポンス最大バイト数制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後のサイズチェックを実装（メモリ DoS 対策）。
  - テキスト前処理（URL 除去・空白正規化）を実装（preprocess_text）。
  - raw_news 保存はチャンク化してトランザクション内で行い、INSERT ... RETURNING を使って実際に挿入された記事IDを返す（_INSERT_CHUNK_SIZE）。
  - 記事と銘柄の紐付け用 API（save_news_symbols, _save_news_symbols_bulk）を追加。重複除去しチャンクINSERTで効率化。
  - テキストから銘柄コード（4桁数字）を抽出する extract_stock_codes を実装（known_codes フィルタ付き）。
  - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを設定。

- DuckDB スキーマ定義と初期化モジュールを追加（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の層ごとにテーブル定義を追加:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を定義。
  - 頻出クエリ向けインデックス群を定義（idx_prices_daily_code_date 等）。
  - init_schema(db_path) でディスク上に DB フォルダを自動作成し、全DDLとインデックスを冪等に実行して接続を返す。get_connection() で既存 DB へ接続可能。

- ETL パイプラインを追加（kabusys.data.pipeline）
  - 差分更新の考え方に基づく ETL ヘルパーとジョブを実装（run_prices_etl 等）。
  - ETLResult データクラスを導入し、取得件数、保存件数、品質問題、エラーを構造化して返却。
  - 差分更新のためのユーティリティ (_table_exists, _get_max_date, get_last_price_date 等) を追加。
  - 市場カレンダーに基づき非営業日を直近営業日に調整する _adjust_to_trading_day を実装。
  - デフォルト値・方針:
    - J-Quants データの最小開始日: 2017-01-01
    - カレンダー先読み: 90日
    - デフォルトバックフィル: 3日（backfill_days）
    - 品質チェックの重大度は別モジュール quality と連携（fail-fast ではなく全件収集）

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### セキュリティ
- news_collector にて以下のセキュリティ対策を導入:
  - defusedxml による XML パース（XML Bomb 等の防御）
  - SSRF 対策（リダイレクト先と初回ホストのプライベートIPチェック、許可スキームの制限）
  - レスポンスサイズ上限と gzip 解凍後の再チェックによる DoS 緩和

### 既知の注意点 / 破壊的変更
- 本パッケージは初版のため API が確定していません。将来的に関数署名や戻り値の構造が変更される可能性があります。
- DuckDB スキーマは初期設計に基づいており、スキーマ変更時はマイグレーションが必要になります。

---

今後の TODO（実装予定/検討項目、リリースノートに含めるための備忘）
- quality モジュールの具体的な実装（欠損・スパイク・重複検出ロジック）と pipeline との統合強化
- strategy / execution / monitoring パッケージの実装（現在はパッケージ空ディレクトリ）
- 単体テスト・統合テストの追加（外部 API モックやネットワークの分離）
- ロギングとモニタリングの整備（Slack 連携などの運用通知）
- DB マイグレーション機能の追加

詳しい利用方法や設計資料はソース内の docstring（DataPlatform.md / DataSchema.md 相当の記述）を参照してください。