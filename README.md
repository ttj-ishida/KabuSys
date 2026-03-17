KabuSys — 日本株自動売買プラットフォーム
=================================

概要
---
KabuSys は日本株の自動売買プラットフォーム向けに設計された Pythonパッケージです。  
主にデータ取得（J-Quants 等）、ETL（差分更新・品質チェック）、ニュース収集、マーケットカレンダー管理、監査ログ（発注→約定トレーサビリティ）を提供します。  
設計上、冪等性（ON CONFLICT）、Look‑ahead bias の防止（fetched_at の記録）、API レート制御・リトライ、SSRF 対策など実運用を意識した実装がなされています。

主な機能
---
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得（ページネーション対応）
  - レート制限（120 req/min）を守る RateLimiter、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存関数（ON CONFLICT を利用）
- ニュース収集（RSS）
  - RSS フィード取得、URL 正規化、トラッキングパラメータ除去、記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証、プライベートIP 規制、リダイレクト時の検査）、XML パースの安全化（defusedxml）、受信サイズ制限
  - DuckDB への冪等保存（INSERT ... RETURNING を利用）と銘柄コード抽出・紐付け
- ETL パイプライン
  - 市場カレンダー・株価・財務データの差分更新（バックフィル対応）、品質チェックとの統合実行
  - 品質チェック（欠損・重複・スパイク・日付不整合）を実施し QualityIssue を返す
- カレンダー管理
  - market_calendar テーブルの夜間更新ジョブ、営業日判定/前後営業日の取得/期間内営業日リスト取得など
- 監査ログ（Audit）
  - signal → order_request → execution の階層でトレーサビリティを保証するテーブル群と初期化機能
- スキーマ管理
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution / Audit）と初期化ユーティリティ

セットアップ手順
---
1. リポジトリを取得
   - git clone してプロジェクトルートへ移動します（.git または pyproject.toml がルート検出に使われます）。

2. 必要なパッケージをインストール
   - 例（pip）:
     - python >= 3.10 を想定
     - pip install duckdb defusedxml
   - 開発用セットアップがあれば pyproject.toml / requirements.txt に従ってください。

3. 環境変数の準備
   - プロジェクトルートに .env を置くか、OS 環境変数を設定します。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID — 通知先 Slack チャネル ID（必須）
   - 任意 / デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - 自動ロード: config モジュールはプロジェクトルートの .env を自動で読み込みます（.env.local は上書き）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. DuckDB スキーマ初期化
   - Python コンソールまたはスクリプトで実行:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")
   - 監査ログ用テーブルを分離 DB に作成する場合:
     - from kabusys.data import audit
     - conn_audit = audit.init_audit_db("data/audit.duckdb") または audit.init_audit_schema(conn)

使い方（主要 API と実行例）
---
- スキーマ初期化（DuckDB）
  - 例:
    - from kabusys.data import schema
    - conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を渡すことも可能
  - result は ETLResult オブジェクト（取得数／保存数／品質問題／エラー情報を保持）

- 市場カレンダーの夜間更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)

- RSS ニュース収集（全ソース）
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, known_codes=set(["7203", "6758", ...]))

- 個別 API（J-Quants）
  - from kabusys.data import jquants_client as jq
  - token = jq.get_id_token()  # リフレッシュトークンから id_token を取得
  - records = jq.fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
  - jq.save_daily_quotes(conn, records)

- 品質チェックの単体実行
  - from kabusys.data import quality
  - issues = quality.run_all_checks(conn, target_date=..., reference_date=...)

注意点 / トラブルシューティング
---
- 環境変数が未設定の場合、Settings のプロパティは ValueError を投げます（必須変数をチェックしてください）。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml の親ディレクトリ）を基準に行われます。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB ファイルの親ディレクトリが存在しない場合、init_schema / init_audit_db が自動で作成します。
- RSS 取得では SSRF/巨大レスポンス対策が組み込まれています。内部ネットワークや file: スキームなどは拒否されます。
- J-Quants API のレート制限（120 req/min）を守るためモジュール内でスロットリングを行います。大量の並列リクエストは避けてください。
- KABUSYS_ENV の有効値: development, paper_trading, live（それ以外はエラーになります）。

ディレクトリ構成（主要ファイル）
---
- src/kabusys/
  - __init__.py              — パッケージ定義とバージョン（__version__ = "0.1.0"）
  - config.py                — 環境変数・設定管理（.env 自動読み込み、Settings）
  - data/
    - __init__.py
    - schema.py              — DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
    - jquants_client.py      — J-Quants API クライアント（fetch/save、認証、レート制御）
    - pipeline.py            — ETL パイプライン（差分更新・品質チェック統合）
    - news_collector.py      — RSS ニュース収集・保存・銘柄紐付け（SSRF対策・gzip限界）
    - calendar_management.py — マーケットカレンダー管理（営業日判定、更新ジョブ）
    - quality.py             — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py               — 監査ログ（signal / order_request / executions テーブル、初期化）
  - strategy/
    - __init__.py            — 戦略関連のエントリ（拡張領域）
  - execution/
    - __init__.py            — 発注/約定/ブローカー連携（拡張領域）
  - monitoring/
    - __init__.py            — 監視・メトリクス（拡張領域）

設計上のポイント（補足）
---
- 冪等性: DB への保存は ON CONFLICT を使用し重複を避ける実装です。
- トレーサビリティ: audit モジュールにより signal→order→execution の全履歴を保存可能です（UUID ベース）。
- 品質管理: ETL 内で品質チェックを実行し、発見された問題は呼び出し元に返します（Fail‑Fast ではなく全件収集）。
- セキュリティ: RSS の XML パースに defusedxml を使い、SSRF 対策・受信サイズ制限・リダイレクト検査を実装しています。

開発・拡張
---
- strategy, execution, monitoring パッケージは拡張ポイントです。戦略ロジック、ポートフォリオ最適化、ブローカー連携（kabu/station）や Slack 通知などをここに実装してください。
- テスト時は config の自動 .env 読み込みを無効化し、必要な環境変数をテスト内で注入することを推奨します。

バージョン
---
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）。

問い合わせ・貢献
---
- バグや機能要望は issue を立ててください。プルリクエスト歓迎です。ドキュメントや型注釈、テストの拡充も助かります。

以上が KabuSys の概要と使い方のサマリです。必要であれば、具体的な実行スクリプト（systemd / cron / CI）や Docker 化、運用手順（ロギング・アラート設定）に関するテンプレートも作成します。どの情報が欲しいか教えてください。