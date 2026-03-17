# Keep a Changelog

すべての変更はセマンティックバージョニングに従います。  
このファイルは主にコードベースから推測して作成した初期リリースの変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買プラットフォーム「KabuSys」の基盤となるモジュール群を追加しました。主な内容は以下のとおりです。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化: kabusys.__init__ にてバージョン管理と公開サブパッケージを定義。
  - 空のパッケージプレースホルダ: execution, strategy モジュールを追加（将来の実装用）。

- 設定管理 (kabusys.config)
  - 環境変数 / .env 自動読み込み機能を実装。
    - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWDに依存しない設計。
    - 読み込み順序: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パースの堅牢化:
    - exportプレフィックス対応、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理、無効行スキップ。
  - Settings クラスを提供:
    - J-Quants 用トークン、kabu API、Slack、DBパス（DuckDB/SQLite）、環境種別（development/paper_trading/live）やログレベルの検証等をプロパティで取得。
    - 不正値や未設定の必須変数は明瞭なエラー（ValueError）で通知。

- J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API から日次株価、財務データ（四半期BS/PL）、マーケットカレンダーを取得するクライアントを実装。
  - レート制御:
    - 固定間隔スロットリングによる 120 req/min 制御（_RateLimiter）。
  - リトライ戦略:
    - 指数バックオフ、最大3回リトライ。対象ステータス 408, 429, >=500。
    - 429 の場合は Retry-After を尊重。
  - 認証トークン管理:
    - refresh_token から id_token を取得する get_id_token。
    - 401 受信時にはトークン自動リフレッシュを1回試行。
    - モジュールレベルで id_token をキャッシュし、ページネーション間で共有。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供。
    - 取得日時（fetched_at）を UTC で記録する方針を採用（Look-ahead Bias 対策）。
  - DuckDB への保存関数（冪等性）:
    - save_daily_quotes, save_financial_statements, save_market_calendar は INSERT ... ON CONFLICT DO UPDATE により冪等に保存。
  - 入力整形ユーティリティ:
    - _to_float / _to_int により不正な数値を安全に None 等に変換。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集し raw_news テーブルへ保存するモジュールを追加。
  - セキュリティ・堅牢性対策:
    - defusedxml を使用した XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト先のプライベートアドレス検出、リダイレクト時の事前検証ハンドラを実装。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - 受信ヘッダの Content-Length を事前チェックして超過時はスキップ。
  - URL 正規化・記事ID生成:
    - トラッキングパラメータ（utm_*, fbclid 等）を除去し、正規化後に SHA-256（先頭32文字）で記事IDを生成し冪等性を担保。
  - テキスト前処理:
    - URL 削除、空白正規化等の preprocess_text。
  - DB 保存:
    - save_raw_news はチャンク分割して INSERT ... ON CONFLICT DO NOTHING RETURNING id で新規挿入IDのみを取得。1トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk により記事と銘柄コードの紐付けを一括で保存（ON CONFLICT を利用）。
  - 銘柄コード抽出:
    - テキストから 4 桁コードを正規表現で抽出し、known_codes に含まれるものだけを返す extract_stock_codes。
  - 統合ジョブ:
    - run_news_collection により複数 RSS ソースから収集し、DB 保存および（known_codes が渡された場合）銘柄紐付けを行う。各ソースは独立してエラーハンドリング。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataLayer（Raw / Processed / Feature / Execution）のテーブル作成DDLを定義。
  - 主要テーブル（例: raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）を含むフルスキーマを追加。
  - インデックス定義（よく使うクエリに対する補助インデックス）を追加。
  - init_schema(db_path) によりディレクトリ生成からテーブル作成までを行い、接続を返す。get_connection は既存DBへ接続するユーティリティ。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分ETL の考え方と初期ユーティリティを実装。
    - 最小データ開始日 _MIN_DATA_DATE を定義。
    - カレンダー先読みや backfill_days による後出し修正吸収を考慮。
  - ETLResult データクラスを追加してETL の結果・品質問題・エラーを表現。
  - テーブル存在チェック、最大日付取得、営業日調整等のヘルパーを実装。
  - run_prices_etl（差分取得 & 保存）を追加（取得→保存→ログ）。（注: ファイル末尾で関数が途中で切れている可能性があるため、完全な戻り値や以降の処理は今後の実装や追加が必要）

### 修正 (Changed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### 修正(バグ) / 安全性 (Fixed / Security)
- RSS収集・HTTP処理に関して複数の安全対策を導入:
  - defusedxml による XML パース、防御的なサイズ制限、SSRF 用のリダイレクト検査、許可しないスキームの遮断。
- J-Quants クライアントに対してはリトライ・レート制御・トークン自動リフレッシュ機構を導入し、信頼性を向上。

### 既知の制限 / 注意点 (Notes)
- strategy / execution パッケージはプレースホルダのみで、実際の戦略ロジックや発注実装は含まれていません。
- pipeline.run_prices_etl はファイル末尾の時点で戻り値のタプルが途中で切れているように見えます（len(records), まで）。実行時は完全な実装（prices_saved を返すなど）が必要です。
- DuckDB スキーマは初期設計に基づくものであり、運用上の要件（パフォーマンス、パーティション、インデックス戦略など）に応じて調整が必要です。
- .env の自動ロードはプロジェクトルート検出に依存するため、ライブラリを配布して別パスで実行する場合は環境変数で制御すること（KABUSYS_DISABLE_AUTO_ENV_LOAD 等）。

### マイグレーション (Migration)
- 初回リリースのため特別な移行手順はありません。新規環境では以下手順を推奨します:
  1. settings を環境変数または .env/.env.local で設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  2. schema.init_schema(settings.duckdb_path) を呼び出して DuckDB を初期化。
  3. jquants_client.get_id_token() / pipeline の ETL 関数等を用いてデータ取得を開始。

### 今後の予定 (Future)
- strategy と execution モジュールへ具体的な戦略実装、発注制御（kabuステーション連携）、ポートフォリオ管理ロジックの追加。
- pipeline の品質チェックモジュール（quality）の実装・統合（現状は参照されるが定義は外部または今後実装予定）。
- テストカバレッジと CI の整備（HTTP/ネットワーク周りはモック化を前提に設計済み）。
- パフォーマンス最適化（DuckDB の利用パターンに応じたチューニング）。

---

開発・運用上の質問やこのCHANGELOGの補足が必要ならお知らせください。必要に応じて日付や注記の更新、より詳細なセクション分けも対応します。