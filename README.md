KabuSys
=======

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。本リポジトリはデータ取得・スキーマ定義・監査ログ・環境設定等、売買ロジックを支える基盤コンポーネントを提供します。

主な目的
- J-Quants API などからの市場データ取得・永続化（DuckDB）
- データレイヤ（Raw / Processed / Feature / Execution）のスキーマ管理
- 発注・約定に関する監査ログ（トレーサビリティ）管理
- 環境設定の自動ロード／管理

機能一覧
- 環境変数管理（.env, .env.local の自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- J-Quants API クライアント
  - 日次株価（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制限の自動制御（120 req/min）
  - リトライ（指数バックオフ、最大 3 回。408/429/5xx を対象）
  - 401 受信時の自動トークンリフレッシュ（1 回）
  - fetched_at による取得時刻記録（UTC）で Look-ahead Bias を抑制
  - ページネーション対応
- DuckDB スキーマ定義・初期化（init_schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義 + インデックス
  - :memory: モード対応
- 監査ログ（audit）モジュール
  - signal_events / order_requests / executions テーブル
  - 発注フローの UUID 連鎖によるトレーサビリティ
  - TIMESTAMP は UTC 保存（init_audit_schema により SET TimeZone='UTC' を実行）
- データ永続化ユーティリティ
  - fetch_* 系で取得したデータを raw_* テーブルへ冪等的に保存（ON CONFLICT DO UPDATE）

セットアップ手順（開発向け）
1. Python と依存ライブラリを用意
   - Python 3.9+（コードは型ヒントで Union 型などを利用）
   - 主要依存: duckdb（その他 HTTP 周りは標準ライブラリを使用）

   例（pip）:
   pip install duckdb

   （プロジェクト配布時に requirements.txt / pyproject.toml を参照してください）

2. .env ファイルをプロジェクトルートに作成
   - 自動的に .env → .env.local の順でロードします（OS 環境変数が優先）
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

   必須の環境変数
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabuステーション API のパスワード
   - SLACK_BOT_TOKEN : Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID : Slack チャンネル ID

   任意（デフォルトあり）
   - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動ロード無効化（1 等）

3. DuckDB スキーマを初期化
   - 初回は init_schema() を利用してテーブルを作成します。

使い方（基本例）
- 簡単なワークフロー: DB 初期化 → データ取得 → 保存

  Python スニペット例:
  from datetime import date
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  # DB 初期化（file path は settings.duckdb_path から取得可能）
  conn = init_schema(settings.duckdb_path)

  # 日次株価を取得して保存（例: 銘柄コード 7203, 2022 年）
  records = fetch_daily_quotes(code="7203", date_from=date(2022,1,1), date_to=date(2022,12,31))
  saved = save_daily_quotes(conn, records)
  print(f"保存レコード数: {saved}")

- ID トークンの明示取得:
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使ってトークンを取得

- 監査ログ初期化（監査専用 DB を別に作る場合）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- 自動環境読み込みの挙動
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml が基準）を探索し、
    .env を読み込み、続けて .env.local を上書きで読み込みます。
  - OS 環境変数は保護され、.env ファイルにより上書きされません（.env.local は上書き）
  - テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

重要な設計上の注意
- J-Quants API 呼び出しはモジュール内でレート制御されます（_RateLimiter）。
- ネットワーク／HTTP エラーに対するリトライや 401 リフレッシュは組み込まれていますが、
  大量取得を行う場合はシステム全体のレート制御やバックプレッシャーを考慮してください。
- DuckDB の INSERT は冪等性を考慮して ON CONFLICT ... DO UPDATE を使用しています。
- 監査ログは削除しない前提で設計されています（FK は ON DELETE RESTRICT）。

ディレクトリ構成
- src/kabusys/
  - __init__.py              パッケージエントリ（バージョン・公開 API）
  - config.py                環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py      J-Quants API クライアント（取得・保存ロジック・リトライ・レート制御）
    - schema.py              DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution 層）
    - audit.py               監査ログテーブル定義・初期化（signal_events, order_requests, executions）
    - audit の初期化用関数（init_audit_schema / init_audit_db）
    - その他データモジュール（raw_news などのテーブル定義を含む）
  - strategy/
    - __init__.py            戦略関連モジュール（拡張ポイント）
  - execution/
    - __init__.py            発注実行・約定処理関連（拡張ポイント）
  - monitoring/
    - __init__.py            監視・メトリクス関連（拡張ポイント）

バージョン
- 現在のパッケージバージョン: 0.1.0（src/kabusys/__init__.py に定義）

よくある質問
- Q: .env のフォーマットは？
  - A: POSIX 互換の単純な KEY=VALUE 形式に対応しています。export KEY=val、シングル／ダブルクォート、インラインコメント等に対応しています。
- Q: トークンの自動リフレッシュはどのように動作しますか？
  - A: J-Quants API 呼び出しで 401 を受けた場合、1 回だけ get_id_token() を呼んでキャッシュを更新し、再試行します。ページネーション中はモジュールレベルでトークンを共有します。

拡張・開発メモ
- strategy/、execution/、monitoring/ ディレクトリは拡張ポイントです。戦略や発注ロジックはこれらのモジュールに実装してください。
- DuckDB スキーマは DataSchema.md（リポジトリ外にある設計ドキュメント）を元に設計されています。スキーマを変更する場合は既存データの移行方針を検討してください。

問題報告・貢献
- 不具合・要望があれば Issue を立ててください。プルリクエストは歓迎します。

以上を参考に、KabuSys を基盤として戦略実装や監査付きの自動売買システムを構築してください。必要であれば README にサンプル .env.example や詳細な API 使用例を追加します。どの情報を補足しますか？