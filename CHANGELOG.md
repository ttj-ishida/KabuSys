# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
安定版リリース、機能追加、修正、セキュリティ対策などをカテゴリごとに記載します。

※本 CHANGELOG はリポジトリ内の現在のコードベース（初期実装）から推測して作成しています。

## [Unreleased]

### Added
- ドメイン構成
  - パッケージ kabusys を導入。公開 API として data, strategy, execution, monitoring をエクスポートする初期構成を追加。
  - バージョン文字列: `kabusys.__version__ = "0.1.0"` を設定。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルと環境変数から設定を自動読み込みする仕組みを実装（ルート検出は .git または pyproject.toml を基準）。
  - 自動ロードの無効化オプション: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - `.env` と `.env.local` の読み込み優先度を実装（OS環境変数 > .env.local > .env）。
  - .env パーサーを実装（コメント行、export プレフィックス、クォート内のエスケープ、インラインコメント処理などに対応）。
  - 保護（protected）キー機能を実装し、OS環境変数が意図せず上書きされないようにした。
  - Settings クラスを提供し、以下のプロパティを実装:
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - slack_bot_token, slack_channel_id
    - duckdb_path, sqlite_path
    - env, log_level, is_live, is_paper, is_dev
  - env/log_level の入力検証（許容値のチェック）を実装。未設定の必須値取得時は ValueError を発生。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限制御（固定間隔スロットリング）: デフォルト 120 req/min。
  - リトライロジック: 指数バックオフ、最大 3 回リトライ（対象ステータス: 408, 429, 5xx）。
  - 401 応答時の自動トークンリフレッシュ（1 回のみ）とページネーション間でのトークンキャッシュ。
  - ページネーション対応で、fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB にデータを保存する idempotent な保存関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices テーブル）
    - save_financial_statements（raw_financials テーブル）
    - save_market_calendar（market_calendar テーブル）
  - データ型変換ユーティリティ: _to_float, _to_int（空・不正値を None に変換）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集モジュールを実装（デフォルトソース: Yahoo Finance のビジネスカテゴリ）。
  - セキュリティ対策:
    - defusedxml を使った XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス判定（DNS 解決・IP 判定）、リダイレクト時の検査。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - 受信ヘッダ Content-Length の事前チェック。
  - URL 正規化とトラッキングパラメータ除去（utm_ 等）。
  - 記事ID の生成: 正規化 URL の SHA-256 の先頭32文字を使用（冪等性確保）。
  - 文テキスト前処理（URL除去・空白正規化）。
  - RSS 取得関数 fetch_rss を実装（エラーはロギングして空リスト返却 or 例外伝播の方針を使い分け）。
  - DuckDB への保存機能:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING と RETURNING を使い、実際に挿入された記事IDを返す。チャンク/トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT で重複スキップ、INSERT ... RETURNING を利用）。
  - 銘柄コード抽出: 4桁数字パターンから候補抽出し、既知銘柄セットでフィルタリング（重複除去）。
  - 統合ジョブ run_news_collection を実装。各ソースの失敗は他ソースに影響しない形で処理を継続。

- スキーマ管理（kabusys.data.schema）
  - DuckDB のスキーマ定義を追加（Raw / Processed / Feature / Execution レイヤー）。
  - 多数のテーブル DDL を用意（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など）。
  - インデックス定義（頻出クエリ用）を追加。
  - init_schema(db_path) を実装: 必要に応じて親ディレクトリ作成、全テーブルとインデックスを作成する冪等初期化。
  - get_connection(db_path) を実装: 既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の骨子を実装（差分更新、バックフィル、品質チェック統合の方針を含む）。
  - ETLResult データクラスを導入（取得件数、保存件数、品質問題リスト、エラーリストを保持）。
  - テーブル存在確認、最大日付取得などのユーティリティを実装。
  - 市場カレンダーに基づく営業日調整ロジックを実装（最大30日遡るフォールバック）。
  - 差分更新ヘルパー: get_last_price_date / get_last_financial_date / get_last_calendar_date を追加。
  - run_prices_etl の骨組みを実装（差分算出、jquants_client.fetch_daily_quotes / save_daily_quotes を使う）。  
    - （注）ファイル末尾に示される通り run_prices_etl の戻り値処理が途中まで実装されている（コードベースの現状を反映）。

### Security
- news_collector にて複数の SSRF / DoS 対策を導入（スキーム検査、プライベートIP検査、リダイレクト検査、受信バイト数制限、defusedxml 利用、gzip 解凍後サイズ検査）。

### Documentation / Logging
- 各主要処理に logger を挿入し情報・警告・例外のトラッキングを追加。
- モジュールドキュメント文字列や関数 docstring を充実させ、設計方針や期待動作を明確化。

---

## [0.1.0] - 2026-03-17

リリース: 初回公開（推定）。上記 Unreleased の内容を初期リリースとしてまとめています。

### Added
- 初回の主要機能群を実装（設定管理・J-Quants API クライアント・ニュース収集・DuckDB スキーマ・ETL パイプライン・パッケージエントリポイント）。
- 環境変数管理、.env 自動ロードと保護機構。
- J-Quants クライアント: レートリミット、リトライ、トークンリフレッシュ、ページネーション処理。
- ニュースコレクタ: RSS 取得、URL 正規化、トラッキング除去、記事ID生成、SSRF/DoS 対策、DB 保存処理（トランザクションとチャンク処理）。
- DuckDB スキーマ一式と init_schema/get_connection。
- ETL の基礎（差分取得・バックフィル方針・品質チェック統合のための ETLResult）。

### Security
- defusedxml、SSRF ブロック、受信サイズ上限などのセキュリティ強化を導入。

---

注意 / マイグレーション
- 初回セットアップでは必ず schema.init_schema(settings.duckdb_path) を実行して DB スキーマを作成してください。
- 環境変数の必須キー:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings から取得するため必須です（未設定時は ValueError が発生します）。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。CI 等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- jquants_client の rate limit はモジュール内定数で 120 req/min に設定されています。負荷の高いバッチ運用時は考慮してください。
- news_collector は外部 RSS を取得するため、ネットワークアクセス制限やプロキシ環境での動作確認を推奨します。

フィードバック、バグ報告、改善提案は issue を立ててください。