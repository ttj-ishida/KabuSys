CHANGELOG
=========

すべての重要な変更をここに記録します。  
このプロジェクトはセマンティックバージョニングに従います。詳細は各リリースの説明を参照してください。

[Unreleased]
------------

- 現在未リリースの変更はありません。

[0.1.0] - 2026-03-17
-------------------

初回リリース。日本株自動売買基盤「KabuSys」のコア機能を提供します。主な追加点は以下の通りです。

Added
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__init__、バージョン 0.1.0、公開モジュール定義）。
  - 空のサブパッケージプレースホルダを追加（kabusys.strategy, kabusys.execution, kabusys.data）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索して検出。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env パースの挙動を詳細に扱う（export プレフィックス、クォート内のエスケープ、インラインコメント処理等）。
  - 設定取得用 Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等）。
  - 必須環境変数取得時に未設定なら明示的なエラーを投げる _require を実装。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得するクライアントを実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を尊重する RateLimiter を実装。
  - リトライ戦略: 指数バックオフ付きリトライ（最大 3 回）、HTTP 408/429/5xx に対応。429 の場合は Retry-After を尊重。
  - 認証トークン管理:
    - refresh token から id_token を取得する get_id_token。
    - id_token のモジュールレベルキャッシュ、401 受信時の自動リフレッシュ（1 回）をサポート。
  - ページネーション対応の取得関数を実装（fetch_daily_quotes, fetch_financial_statements）。
  - 取得データを DuckDB に冪等に保存する関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - INSERT ... ON CONFLICT DO UPDATE による重複排除と更新。
    - fetched_at に UTC タイムスタンプを記録し、Look-ahead Bias のトレースを可能に。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news に保存するフローを実装。
  - 安全・品質対策:
    - defusedxml を利用した XML パース（XML Bomb 対策）。
    - HTTP/HTTPS スキームの検証、SSRF 対策（リダイレクト時のスキーム/ホスト検査、プライベートIP除外）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後の再チェック（Gzip bomb 対策）。
    - 受信ヘッダ (Content-Length) の事前チェック。
  - URL 正規化:
    - トラッキングパラメータ（utm_*, fbclid 等）を除去し、スキーム/ホスト小文字化、フラグメント除去、クエリソートを実施。
    - 正規化 URL からの記事ID生成（SHA-256 の先頭32文字）。これにより冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存:
    - INSERT ... RETURNING を用いて新規挿入された記事IDを正確に取得する save_raw_news。
    - 記事と銘柄コードの紐付けを行う save_news_symbols / _save_news_symbols_bulk（チャンク分割、1 トランザクション）。
    - 実運用を想定したチャンクサイズ制御とトランザクションロールバックの実装。
  - 銘柄コード抽出: 正規表現による 4 桁数字抽出と既知コードセットによるフィルタ（extract_stock_codes）。
  - 統合ジョブ run_news_collection を実装（複数ソースの独立エラーハンドリング、既知銘柄と新規記事の紐付け）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataSchema に基づく包括的なスキーマ初期化を追加（init_schema / get_connection）。
  - 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル群を定義:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約、型チェック、主キー、外部キーを含む DDL を整備。
  - 頻出クエリを想定したインデックスを作成。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラスを実装（取得数 / 保存数 / 品質問題 / エラーの集約）。
  - スキーマ存在チェックやテーブル最大日付取得のユーティリティを実装（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 営業日調整ヘルパー（_adjust_to_trading_day）。
  - 差分更新のための run_prices_etl を実装（差分ロジック、backfill_days による後出し修正吸収、jq.fetch / jq.save の利用）。
  - 設計方針: 差分単位は営業日ベース、バックフィル日数デフォルト 3 日、品質チェックは収集を継続し呼び出し元が判断する設計。

Security
- SSRF 対策を強化（ニュース取得時のリダイレクト検査、プライベートIP排除）。
- XML パースで defusedxml を使用（XML による攻撃防止）。
- HTTP レスポンスサイズ・gzip 解凍後サイズの検査で DoS 対策を実装。

Documentation / Examples
- 各モジュールに docstring と使用例・設計ノートを付与（config の使用例、jquants_client の設計原則等）。
- 設定項目（必須環境変数）の明示を追加。

Dependencies
- duckdb（データ保存とクエリ実行）
- defusedxml（XML パースの安全化）
- 標準ライブラリの urllib / gzip / hashlib / ipaddress / socket 他

Notes / Migration
- 初回利用時は必ず schema.init_schema() を実行して DuckDB スキーマを作成してください（例: kabusys.data.schema.init_schema(settings.duckdb_path)）。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- テスト実行や CI 環境で自動 .env 読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector の extract_stock_codes は known_codes を引数で受け取るため、外部で銘柄コードセットを事前に用意してください。

Known limitations / TODO
- strategy / execution サブパッケージは現状プレースホルダ（実装の拡張が必要）。
- pipeline.run_prices_etl は株価 ETL の主要機能を備えていますが、財務・カレンダーの統合 ETL ジョブや品質チェックの呼び出し・集約は今後追加予定。
- テストカバレッジ、エンドツーエンドの統合テストは今後整備する予定。

---

注: 本 CHANGELOG は現行コードベースから推定して作成しています。実際のリリースノート作成時は、コミット履歴やリリース管理ポリシーに基づく最終確認を推奨します。