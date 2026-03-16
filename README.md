# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ。  
データ取得（J-Quants）、DuckDB スキーマ管理、データ品質チェック、監査ログなど、アルゴリズム取引基盤で必要となる共通処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株自動売買システムの基盤モジュール群を含む Python パッケージです。主な目的は次のとおりです。

- 外部データ（J-Quants）の取得と DuckDB への永続化
- DuckDB によるスキーマ定義（Raw / Processed / Feature / Execution 層）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- 環境変数／設定管理（.env 自動読み込み）

設計上の特徴として、API レート制御、リトライ（指数バックオフ）、ID トークン自動リフレッシュ、UTC タイムスタンプの記録、冪等性（ON CONFLICT を利用）などを備えています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - レートリミット（120 req/min）・リトライ・401 トークン自動更新対応
  - DuckDB への保存ユーティリティ（冪等的保存）
- data.schema
  - DuckDB のスキーマ定義 / 初期化（Raw、Processed、Feature、Execution 層）
  - 標準的なインデックス定義
- data.audit
  - 監査ログ用テーブル（signal_events、order_requests、executions 等）の初期化
  - 発注冪等キー・ステータス管理等の設計
- data.quality
  - 欠損検出、スパイク（大振幅）検出、重複チェック、日付整合性チェック
  - QualityIssue 型を返却し、呼び出し側が処理方針（停止/警告）を判断可能
- config
  - .env ファイル（.env, .env.local）または OS 環境変数から設定を読み込み
  - 必須設定の取得（不足時は例外を送出）
  - 自動 .env ロードはプロジェクトルート（.git / pyproject.toml）を基準に行う。無効化可能

---

## 動作要件

- Python 3.10+
- 必要なパッケージ例:
  - duckdb
- その他、実運用では J-Quants API アクセスや kabuステーション API への接続を行うためのネットワーク環境や認証トークンが必要です。

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン / 取得

2. 仮想環境を作成して有効化（推奨）

   - Unix/macOS
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell)
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 必要パッケージをインストール

   - 例（最低限）:
     - pip install duckdb

   - 開発用にパッケージ化されていれば:
     - pip install -e .

4. 環境変数を設定

   リポジトリルート（.git もしくは pyproject.toml があるディレクトリ）に `.env` を置くと、自動で読み込まれます（順序: OS 環境 > .env.local > .env）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（少なくともこれらは設定してください）:

   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API のパスワード
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

   任意・デフォルト値あり:

   - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

5. DuckDB スキーマの初期化（例）

   Python REPL / スクリプトで:

   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)  # ファイル作成・テーブル作成
   # 監査ログを追加する場合:
   from kabusys.data import audit
   audit.init_audit_schema(conn)

---

## 使用例

以下は代表的な使用例です。実際は例外処理やログ出力を加えて運用してください。

1) J-Quants の株価を取得して DuckDB に保存する

    from kabusys.data import jquants_client
    from kabusys.data import schema
    from kabusys.config import settings

    conn = schema.init_schema(settings.duckdb_path)
    # 全銘柄/全期間ではなく適宜 code / date_from / date_to を指定すること
    records = jquants_client.fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
    inserted = jquants_client.save_daily_quotes(conn, records)
    print(f"{inserted} 件保存しました")

挙動メモ:
- fetch 系関数はページネーション対応
- レート制御は内部で行われる（120 req/min）
- 401 が返ると自動で ID トークンを再取得して 1 回リトライする
- save_* 関数は fetched_at を UTC ISO8601 で保存し、ON CONFLICT DO UPDATE により冪等

2) データ品質チェックを実行する

    from kabusys.data import quality
    from kabusys.data import schema
    from kabusys.config import settings
    from datetime import date

    conn = schema.get_connection(settings.duckdb_path)
    issues = quality.run_all_checks(conn, target_date=date(2024,1,15))
    for issue in issues:
        print(issue.check_name, issue.severity, issue.detail)

戻り値は QualityIssue オブジェクトのリスト。呼び出し側でエラーや警告に対する挙動（ETL 停止、アラート送信等）を決定します。

3) 監査ログテーブルを初期化（独立DBも可能）

    from kabusys.data import audit
    conn_audit = audit.init_audit_db("data/audit.duckdb")

監査ログではすべての TIMESTAMP を UTC で保存する方針です。

4) 設定項目の参照

    from kabusys.config import settings
    print(settings.env, settings.log_level)

settings から必要な設定値を安全に取得できます。必須値が無い場合はエラー（ValueError）が発生します。

---

## 開発者向けノート / 設計上のポイント

- Python バージョン: 3.10+（型アノテーションに | を使用）
- .env の自動読み込みはプロジェクトルートを __file__ を起点に探索して決定するため、CWD に依存しません。
- .env パースはシェル風の export キーワードやクォート・エスケープ、インラインコメントなどに対応します。
- J-Quants クライアント:
  - レート制限: 固定間隔スロットリング
  - リトライ: 最大 3 回、408 / 429 / 5xx はリトライ対象
  - 429 の場合は Retry-After ヘッダを優先
  - JSON のデコード失敗はエラーとして扱います
- DuckDB スキーマ定義:
  - Raw → Processed → Feature → Execution の多層構造
  - ON CONFLICT / CHECK 制約でデータ品質を維持
  - インデックスは頻出クエリパターンに合わせて定義済み
- 監査ログ:
  - order_request_id を冪等キーとして二重発注を防止
  - レコードは基本的に削除されない前提（ON DELETE RESTRICT）
  - 全ての TIMESTAMP は UTC に統一

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py
      - schema.py
      - audit.py
      - quality.py

主要モジュール:
- kabusys.config: 環境設定・.env 読み込み
- kabusys.data.jquants_client: J-Quants API クライアントと保存関数
- kabusys.data.schema: DuckDB スキーマ初期化
- kabusys.data.audit: 監査ログ初期化
- kabusys.data.quality: データ品質チェック

---

## ライセンス / 責任

このパッケージはインフラ・ユーティリティを提供しますが、実運用では API キーの管理・レート制御・例外処理・注文の正確性に十分注意してください。実際の発注機能を稼働させる前にペーパー取引環境で十分な検証を行ってください。

---

必要であれば、README にサンプル .env.example、requirements.txt、または更に詳しいチュートリアル（ETL ワークフロー、運用手順、Slack 連携サンプル）を追記します。どの情報が必要か教えてください。