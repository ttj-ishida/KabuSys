KabuSys
=======

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）の軽量コア実装です。
本リポジトリはデータ取得・永続化（DuckDB）、監査ログ（監査スキーマ）、データ品質チェック、環境設定ユーティリティなど、自動売買システムの基盤となるコンポーネント群を提供します。

主な特徴
-------
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - API レート制御（120 req/min）とリトライ（指数バックオフ、401 の自動トークンリフレッシュ等）対応
  - 取得タイムスタンプ（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を排除

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution の多層スキーマ定義
  - テーブル作成・インデックス作成を行う init_schema(db_path) を提供
  - 監査ログ（signal_events / order_requests / executions）用の init_audit_schema も提供

- 監査ログ（Audit）
  - ビジネス日・戦略ID・シグナル・発注要求・証券会社約定まで UUID 連鎖で完全トレース
  - 発注要求は冪等キー（order_request_id）を持ち、二重発注を防止
  - すべての TIMESTAMP は UTC 保存を前提

- データ品質チェック
  - 欠損データ検出（OHLC 欠損）
  - スパイク検出（前日比の急騰/急落）
  - 主キー重複チェック
  - 日付不整合チェック（未来日付・非営業日データ）
  - 全チェックをまとめて実行する run_all_checks(conn, ...)

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定は .git または pyproject.toml）
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - 必須環境変数のラッパ（settings オブジェクト）

動作環境
-------
- Python 3.10 以上（型ヒントに | を用いているため）
- 必要パッケージ（抜粋）
  - duckdb
  - 標準ライブラリ（urllib, logging, json, datetime, pathlib 等）

セットアップ手順
--------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。

   - Unix/macOS:
     python -m venv .venv
     source .venv/bin/activate

   - Windows (Powershell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1

2. 依存パッケージをインストールします（例: duckdb）。

   pip install duckdb

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください）

3. 開発インストール（任意）

   pip install -e .

4. 環境変数の設定
   プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定している場合は無効化）。

   サンプル（.env.example）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_api_password
   # KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルトは上記）

   # Slack (通知等に使用)
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id

   # データベースパス (任意)
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development  # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

- 必須環境変数（アプリ内で _require() によって必須扱い）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

使い方（基本的なコード例）
-----------------------
以下は代表的な利用例です。すべて Python スクリプトから利用できます。

- DuckDB スキーマ初期化

  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成されます

- J-Quants から日足を取得して保存

  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  # トークンは settings またはモジュールキャッシュを使って自動で処理されます
  records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
  inserted = save_daily_quotes(conn, records)
  print(f"保存件数: {inserted}")

- 監査スキーマの初期化（既存の DuckDB 接続に追加）

  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn)

- 監査専用 DB を新規作成する場合

  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")

- データ品質チェックの実行

  from kabusys.data.quality import run_all_checks

  issues = run_all_checks(conn, target_date=None)
  for issue in issues:
      print(issue.check_name, issue.table, issue.severity, issue.detail)
      for row in issue.rows:
          print("  ", row)

主な API / 関数一覧
------------------
- kabusys.config
  - settings: 設定オブジェクト（jquants_refresh_token, kabu_api_password, duckdb_path, env, log_level 等）
  - 自動 .env ロード機能（.env → .env.local の優先度）と KABUSYS_DISABLE_AUTO_ENV_LOAD

- kabusys.data.jquants_client
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - get_id_token(refresh_token=None) — リフレッシュトークンから ID トークンを取得

  設計上の注意:
  - API レートは 120 req/min（モジュール内 RateLimiter が保障）
  - リトライ: 最大 3 回、408/429/5xx はリトライ対象、429 の場合は Retry-After を優先
  - 401 受信時はリフレッシュして 1 回のみ再試行

- kabusys.data.schema
  - init_schema(db_path) — DuckDB のスキーマ作成（冪等）
  - get_connection(db_path) — 既存 DB への接続取得

- kabusys.data.audit
  - init_audit_schema(conn) — 監査ログテーブルの初期化
  - init_audit_db(db_path) — 監査専用 DB の初期化

- kabusys.data.quality
  - check_missing_data(conn, target_date=None)
  - check_spike(conn, target_date=None, threshold=0.5)
  - check_duplicates(conn, target_date=None)
  - check_date_consistency(conn, reference_date=None)
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

ディレクトリ構成（主要ファイル）
------------------------------
src/
  kabusys/
    __init__.py                # パッケージ定義（__version__ 等）
    config.py                  # 環境変数・設定管理（.env 自動ロード、settings）
    data/
      __init__.py
      jquants_client.py        # J-Quants API クライアント（取得・保存ロジック）
      schema.py                # DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
      audit.py                 # 監査ログスキーマ（signal_events / order_requests / executions）
      quality.py               # データ品質チェックモジュール
      # その他: news / executions などに関するプレースホルダテーブル定義あり
    strategy/
      __init__.py              # 戦略関連モジュール（本リポジトリでは空）
    execution/
      __init__.py              # 注文・ブローカー連携モジュール（本リポジトリでは空）
    monitoring/
      __init__.py              # 監視・メトリクス関連（本リポジトリでは空）

設計上の考慮点 / 運用上の注意
---------------------------
- すべての TIMESTAMP / fetched_at は UTC を基本とします。監査スキーマ初期化時に SET TimeZone='UTC' が実行されます。
- 環境変数の自動ロードはプロジェクトルートの判定に .git または pyproject.toml を用いるため、配布後・インストール後も想定通りに動作します。テスト時などで自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API の利用には有効なリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必要です。API 利用時はレート制限・リトライ挙動を満たしているため、クライアント側での追加のレート制御は通常不要です。
- save_* 系関数は ON CONFLICT DO UPDATE を使用するため冪等に保存できますが、外部からの直接挿入などで主キー重複が起きる可能性を排除するために、品質チェック（check_duplicates）も用意しています。

ライセンス / コントリビューション
-------------------------------
本リポジトリのライセンスやコントリビューションルールはリポジトリルートの LICENSE / CONTRIBUTING.md を参照してください（存在しない場合はリポジトリ管理者に問い合わせてください）。

補足（例: よくある質問）
-----------------------
Q. なぜ DuckDB を採用しているのですか？
A. DuckDB は組み込み型の列指向 DB であり、分析クエリ（時系列・集計）が高速に動作します。ETL / バッチ処理用途に適しています。

Q. API キーが流出した場合は？
A. 環境変数や .env ファイルは適切に管理してください。公開リポジトリに機密情報を含めないでください。

---

その他、導入や運用に関する具体的なユースケース（シグナル→発注のフロー実装、kabuステーションとの送受信、Slack 通知など）については別途ドキュメントを作成できます。必要であれば用途にあわせてサンプルスクリプトや運用ガイドを追加します。