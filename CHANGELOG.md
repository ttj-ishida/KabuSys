# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  
安定版や互換性はセマンティックバージョニングに従います。

現在のリリース: 0.1.0

## [Unreleased]

- 今後の予定（実装中 / 検討中）
  - ETL パイプラインの継続的な拡張（財務データ・カレンダーの ETL、品質チェックの詳細レポート出力など）。
  - execution / strategy / monitoring パッケージの実装（現状はパッケージプレースホルダ）。
  - 単体テスト・統合テストの整備（ネットワーク呼び出しのモック整備、DB 初期化テストなど）。
  - run_prices_etl 等のエラーハンドリング・戻り値の最終確認と追加の ETL ジョブ完成。

---

## [0.1.0] - 2026-03-17

初回リリース — 日本株自動売買システムのコア基盤を実装。

### Added
- パッケージ基礎
  - kabusys パッケージの初期エクスポート定義（__version__ = "0.1.0"、主要サブパッケージを __all__ に定義）。

- 設定／環境管理 (`kabusys.config`)
  - .env ファイルおよび OS 環境変数から設定を自動ロードする仕組みを実装。
    - ロード順: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
    - プロジェクトルートの検出は __file__ を起点に `.git` または `pyproject.toml` を探索（配布後も確実に動作するよう設計）
  - .env パーサーは以下に対応:
    - コメント・空行の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のエスケープ処理
    - インラインコメントの処理（クォート有無に応じた扱い）
    - 読み込み時の上書き制御（override フラグ）と protected キー（OS 環境変数を保護）
  - Settings クラスを提供し、プロパティ経由で設定取得を容易に:
    - J-Quants / kabu ステーション / Slack / DB パス（DuckDB, SQLite）等の取得
    - KABUSYS_ENV（development / paper_trading / live）の検証
    - LOG_LEVEL の検証
    - is_live / is_paper / is_dev のヘルパー

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API ベース実装（_BASE_URL、認証、ページネーション対応）を実装。
  - レート制限制御:
    - 固定間隔スロットリング（120 req/min を守る _RateLimiter）
  - 再試行（リトライ）ロジック:
    - 最大 3 回の指数バックオフ
    - 再試行対象ステータス: 408, 429 および 5xx
    - 429 時は `Retry-After` ヘッダを優先
  - 認証トークン処理:
    - リフレッシュトークンから ID トークンを取得する get_id_token()
    - 401 受信時はトークンを自動リフレッシュして 1 回だけ再試行
    - モジュールレベルで ID トークンをキャッシュしページネーション間で共有
  - データ取得関数:
    - fetch_daily_quotes（OHLCV、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX 市場カレンダー）
    - 取得時に logger.info により取得件数を出力
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE を用いた冪等保存（重複更新）
    - fetched_at を UTC ISO フォーマットで記録し Look-ahead Bias を防止
  - 値変換ユーティリティ: _to_float / _to_int（安全な型変換、空値や不正値は None）

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからニュース記事を収集して DuckDB に保存する統合機能を実装。
  - セキュリティ・堅牢性の設計:
    - defusedxml による XML パース（XML Bomb 等の対策）
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、プライベートアドレス/ループバック/リンクローカル/マルチキャストへのアクセスを拒否
    - リダイレクト時にもターゲット URL の検証を行うカスタムリダイレクトハンドラ
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を超えるレスポンスは拒否、gzip 解凍後もサイズチェック（Gzip bomb 対策）
    - User-Agent と Accept-Encoding を指定
  - フィード処理:
    - URL 正規化（スキーム・ホスト小文字化、トラッキングパラメータ（utm_* 等）除去、フラグメント除去、クエリソート）
    - 記事 ID は正規化 URL の SHA-256 先頭32文字で生成（冪等性）
    - タイトル・本文の前処理（URL除去、空白正規化）
    - pubDate のパース（RFC 2822→UTC naive datetime、パース失敗時は警告ログと現在時刻で代替）
    - fetch_rss は XML パース失敗時に空リストを返し安全にフォールバック
  - DB 保存:
    - save_raw_news：チャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、新規挿入された記事 ID を返す（トランザクションでまとめて実行）
    - save_news_symbols / _save_news_symbols_bulk：news_symbols テーブルへの紐付けをチャンクで一括挿入（ON CONFLICT で重複スキップ、INSERT RETURNING を使用して挿入数を正確に把握）
  - 銘柄コード抽出:
    - 4桁数字を候補とする抽出（known_codes によるフィルタ、重複除去）
  - デフォルト RSS ソース定義（例: Yahoo Finance 日本のビジネスカテゴリ）

- スキーマ定義・初期化 (`kabusys.data.schema`)
  - DuckDB 用の DDL を整備し、3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を実装。
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature 層: features, ai_scores
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY 等）と頻出クエリ向けインデックスを定義
  - init_schema(db_path) によりファイルパスの親ディレクトリ自動作成と DDL 実行を行う（冪等）
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）

- ETL パイプライン基礎 (`kabusys.data.pipeline`)
  - ETLResult データクラスで ETL 実行結果（取得件数・保存件数・品質問題・エラー等）を表現
  - 差分更新を支援するユーティリティ:
    - _table_exists / _get_max_date / get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _adjust_to_trading_day: 非営業日調整（market_calendar がある場合に直近営業日に調整）
  - run_prices_etl: 差分更新ロジック（最終取得日からの backfill をサポート、デフォルト backfill_days=3、取得→保存のフロー）を実装
    - 初回ロードでは J-Quants が提供する最小日（2017-01-01）から取得
    - ETL は idempotent に設計（保存は jquants_client.save_* で ON CONFLICT により重複対応）
  - 品質チェック（quality モジュール）との連携を想定（品質問題は収集して ETLResult に蓄積）

### Security
- RSS/XML/HTTP に関する対策を多数導入:
  - defusedxml を使用した XML パース
  - SSRF 対策（スキーム制限・プライベートアドレス拒否・リダイレクト検査）
  - レスポンス長の厳格チェック（受信上限、gzip 解凍後のチェック）
- 環境変数の保護:
  - .env の上書き時に既存 OS 環境変数を protected として扱う（意図しない上書きを防止）

### Notes / Design decisions
- 冪等性を重視:
  - データ保存は ON CONFLICT / DO UPDATE / DO NOTHING を多用して再実行可能に設計
- Look-ahead Bias 対策:
  - データ取得時に fetched_at を UTC タイムスタンプで保存し、いつデータを入手したかをトレース可能に
- API レート制限・再試行戦略は明示的に実装（120 req/min, max 3 retries, exponential backoff）
- ネットワーク周りのタイムアウト / エラーはログに記録し、可能な限りリトライして堅牢性を確保

### Known issues / Limitations
- strategy / execution / monitoring パッケージはプレースホルダ（実装なし）。
- run_prices_etl 等の ETL 関数は基本フローを実装しているが、現状のコード断片や戻り値の整合性（ログ・戻り値の完全な仕様）については追加のテストとドキュメント化が必要。
- 単体テストや CI 設定はまだ含まれていないため、ネットワークや DB 依存のテストを実行するにはモック整備が必要。

---

## リリースポリシー
- バージョン番号は SemVer に従います。BREAKING CHANGES は major バージョンを上げて明示します。
- 重要な変更およびセキュリティ修正は CHANGELOG に必ず記載します。

---

（注）本 CHANGELOG は提供されたソースコードから実装内容・設計方針を推測して作成しています。実際の意図や未公開の機能については差異がある可能性があります。必要であれば、各モジュールの実装者・運用担当者による確認後に修正・補完してください。