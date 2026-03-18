# Changelog

すべての注目すべき変更点を記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-18

### Added
- パッケージの初期リリース。
  - パッケージバージョン: 0.1.0

- 基本モジュール構成を追加:
  - kabusys.config: 環境変数／設定管理
    - .env ファイルの自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）
    - .env, .env.local の読み込み順序と override/保護（OS 環境変数保護）を実装
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）
    - 複雑な .env 行パース（export 句、クォート内のバックスラッシュエスケープ、インラインコメント処理）
    - Settings クラス: 必須設定の取得メソッド、デフォルト値、入力検証（KABUSYS_ENV, LOG_LEVEL）
    - デフォルト DB パス（DUCKDB_PATH, SQLITE_PATH）のサポート

  - kabusys.data.schema: DuckDB スキーマ定義・初期化
    - Raw / Processed / Feature / Execution 層に対応したテーブル群を定義（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）
    - 外部キーやチェック制約、主キー、インデックスを含む DDL を用意
    - init_schema(db_path) によりディレクトリ自動作成と冪等なテーブル作成を実行
    - get_connection(db_path) で既存 DB へ接続可能

  - kabusys.data.jquants_client: J-Quants API クライアント
    - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーの取得実装（ページネーション対応）
    - API レート制御（固定間隔スロットリングで 120 req/min を順守する RateLimiter 実装）
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有（ページネーション間）
    - 取得タイミング（fetched_at）を UTC で記録し look-ahead bias を防止する設計
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等性を保証（ON CONFLICT DO UPDATE）

  - kabusys.data.news_collector: ニュース収集モジュール（RSS）
    - 複数 RSS ソースの定義と収集処理（既定で yahoo_finance）
    - RSS 取得 -> テキスト前処理（URL 除去、空白正規化）-> raw_news への冪等保存 -> 銘柄紐付け のフローを実装
    - 記事ID は URL 正規化後の SHA-256 ハッシュの先頭 32 文字で生成（utm_* 等のトラッキングパラメータ除去）
    - defusedxml による安全な XML パース（XML Bomb 等の防御）
    - SSRF 対策:
      - URL スキーム検証（http/https のみ）
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否（DNS 解決した A/AAAA をチェック）
      - リダイレクト時にも検査するカスタム RedirectHandler を使用
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検査（Gzip-bomb 対策）
    - DB 保存はチャンク化して 1 トランザクションで実行、INSERT ... RETURNING による挿入結果の正確な取得
    - extract_stock_codes によるテキスト中の 4 桁銘柄コード抽出（known_codes によるフィルタ、重複除去）
    - run_news_collection により複数ソースからの安全な収集・保存・銘柄紐付けをまとめて実行

  - kabusys.data.pipeline: ETL パイプライン
    - 差分更新ロジック（DB の最終取得日からの差分取得）
    - backfill_days による後出し修正吸収のための再取得（デフォルト 3 日）
    - 市場カレンダーの先読み（デフォルトで一定日数の先読みを想定）
    - ETLResult データクラス（取得件数・保存件数・品質問題・エラー等を集約）
    - 品質チェック（quality モジュールに依存）を実行し、致命的であっても ETL 自体は継続する方針
    - テスト容易性のため id_token の注入をサポート

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集モジュールに対して複数のセキュリティ対策を実装
  - defusedxml による XML パーサー保護
  - SSRF 対策（スキーム検証、ホストのプライベートアドレス検出、リダイレクト先検査）
  - レスポンスサイズ上限と gzip 解凍後サイズチェックによりメモリ DoS を軽減
- J-Quants クライアントは認証トークンの安全な自動リフレッシュと最大リトライ方針を備える

### Notes / Usage tips
- 自動 .env 読み込みはパッケージインポート時に行われます。テストなどで自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）が未設定の場合、Settings 経由でアクセスすると ValueError が発生します。
- DuckDB スキーマは init_schema(db_path) で初期化してください。既存テーブルがある場合は安全にスキップされます。
- ニュース収集関係の挙動（トラッキングパラメータ除去、記事 ID 生成、銘柄抽出）は設計上の互換性を保つために安定化させています。

### Breaking Changes
- （初回リリースのため該当なし）

---

今後のリリースでは、品質チェック結果に基づく自動修正や実行レイヤー（発注送信）の実装、より細かなメトリクス収集やテストカバレッジ強化を予定しています。