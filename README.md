# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ / コンポーネント群

このリポジトリは、データ取得、データベーススキーマ、品質チェック、監査ログなど、自動売買システムの基盤となるモジュール群を提供します。J-Quants API からのデータ取得、DuckDB によるデータ永続化、監査ログ（発注 → 約定のトレーサビリティ）、データ品質チェックなどを含みます。

## 特徴（概要）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）に準拠する固定間隔スロットリング
  - リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアス防止
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ定義＆初期化
  - Raw / Processed / Feature / Execution の多層スキーマを定義
  - インデックスや外部キーを含むDDLを備え、初期化関数を提供
- 監査ログ（audit）
  - signal → order_request → execution のトレーサビリティを保証するテーブル群
  - order_request_id を冪等キーとして二重発注を防止
  - 全 TIMESTAMP を UTC で保存する設計
- データ品質チェック
  - 欠損データ、スパイク（前日比閾値）、重複（主キー重複）、日付不整合（未来日、非営業日）を検出
  - QualityIssue オブジェクトのリストを返し、呼び出し元で判定可能

## 動作環境 / 要件
- Python 3.10+
- 依存パッケージ（最低限）:
  - duckdb
- ネットワーク接続（J-Quants API 利用時）
- （任意）kabuステーション API 連携時は KABU API のエンドポイントが必要

## セットアップ手順（開発環境）
1. リポジトリをクローン
   ```
   git clone <repository_url>
   cd <repository>
   ```

2. 仮想環境を作成して有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 依存パッケージをインストール
   ```
   pip install duckdb
   ```
   （開発パッケージがある場合は requirements.txt や pyproject.toml を参照してインストールしてください）

4. 環境変数の準備
   - プロジェクトルート（.git か pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（デフォルト有効）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: 環境（development / paper_trading / live）デフォルト: development
     - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）デフォルト: INFO

   - サンプル `.env`（最小）
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```

## 使い方（クイックスタート）
以下は主要機能の簡単な使用例です。実際はエラーハンドリングやログ設定を行ってください。

- DuckDB スキーマの初期化
  ```
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")  # ファイル DB
  # あるいはインメモリ:
  # conn = init_schema(":memory:")
  ```

- J-Quants から日足データを取得して DuckDB に保存
  ```
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(code="7203")  # 例: トヨタの銘柄コード（任意）
  inserted = save_daily_quotes(conn, records)
  print(f"{inserted} 件保存しました")
  ```

- 財務データ・カレンダー取得
  ```
  from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
  from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

  fin = fetch_financial_statements(code="7203")
  save_financial_statements(conn, fin)

  cal = fetch_market_calendar()
  save_market_calendar(conn, cal)
  ```

- 監査スキーマの初期化（既存 DuckDB 接続へ追加）
  ```
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)  # conn は init_schema の戻り値を想定
  ```

- 監査専用 DB を作る場合
  ```
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- データ品質チェックを実行
  ```
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for issue in issues:
      print(issue.check_name, issue.severity, issue.detail)
      for row in issue.rows:
          print("  ", row)
  ```

## 主要モジュール説明（簡易 API）
- kabusys.config
  - settings: Settings インスタンス。環境変数を取得するプロパティを提供。
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev
  - .env 自動読み込み:
    - プロジェクトルート（.git または pyproject.toml がある場所）から `.env` と `.env.local` を自動読み込みします。
    - 読込順: OS 環境 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- kabusys.data.jquants_client
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - get_id_token(refresh_token=None)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - レート制御、リトライ、ページネーション対応。取得時刻は UTC の fetched_at に記録。

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
  - DuckDB に必要なテーブル・インデックスを作成する関数を提供。

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)
  - 監査ログ（signal_events, order_requests, executions）を定義・初期化。

- kabusys.data.quality
  - check_missing_data(conn, target_date=None)
  - check_spike(conn, target_date=None, threshold=0.5)
  - check_duplicates(conn, target_date=None)
  - check_date_consistency(conn, reference_date=None)
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - 各チェックは QualityIssue のリストを返す。

## ディレクトリ構成
以下は主要ファイルのツリー（抜粋）です。実際のリポジトリに合わせて拡張してください。

- src/
  - kabusys/
    - __init__.py
    - config.py                        — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py              — J-Quants API クライアント（取得・保存ロジック）
      - schema.py                      — DuckDB スキーマ定義 / 初期化
      - audit.py                       — 監査ログスキーマ（signal/order_request/execution）
      - quality.py                     — データ品質チェック
      - (その他 data モジュール)
    - strategy/
      - __init__.py
      - (戦略関連モジュールを配置)
    - execution/
      - __init__.py
      - (発注・ブローカー連携モジュールを配置)
    - monitoring/
      - __init__.py
      - (監視・アラート関連モジュールを配置)

## 運用上の注意
- J-Quants API のレート制限（120 req/min）を守る設計になっていますが、大規模取得や複数プロセスからの同時アクセス時は運用でさらに制御が必要です。
- DuckDB はファイルロックや同時アクセスに制約があります。複数プロセスが同一ファイルへ頻繁に書き込む用途では運用設計（専用 DB / アクセス制御）を検討してください。
- 監査ログは削除しない前提です。監査テーブルの設計は ON DELETE RESTRICT 等で履歴保全を意識しています。
- すべてのタイムスタンプは UTC で扱うことを前提にしています。アプリケーション側でも UTC を使用するよう統一してください。

## 例: 開発時のワークフロー（例）
1. DuckDB スキーマ初期化（init_schema）
2. J-Quants からデータ取得（fetch_*）
3. 取得データを save_* で保存（冪等）
4. run_all_checks でデータ品質を確認
5. features/ai_scores を作成（別モジュール）
6. signals を生成し signal_queue → 発注（execution モジュール）
7. 発注結果を audit.executions に保存してトレーサビリティ確保

---

詳細な API ドキュメントや運用ガイド、データモデル（DataSchema.md / DataPlatform.md）などは別ドキュメントで管理することを推奨します。README にない具体的な使い方や拡張方法、CI/CD 設定などについては必要に応じて追記してください。