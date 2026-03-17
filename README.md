# KabuSys

日本株向け自動売買 / データ基盤ライブラリです。J-Quants API や RSS を用いたデータ収集、DuckDB ベースのスキーマ定義・ETL、品質チェック、監査ログ機能などを提供します。

---

## プロジェクト概要

KabuSys は日本株のデータ収集から特徴量生成、シグナル/発注（Execution）や監視までを想定したライブラリ群の基礎実装です。主に次の目的を持ちます。

- J-Quants API からの市場データ（株価日足・財務・マーケットカレンダー）取得
- RSS フィードからのニュース収集と銘柄紐付け
- DuckDB 上のスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定・次/前営業日算出）
- 監査ログ（signal→order→execution のトレース）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上、API レート制御、リトライ、冪等性、SSRF 防御、トレーサビリティ等に配慮しています。

---

## 主な機能一覧

- J-Quants クライアント（kabusys.data.jquants_client）
  - レートリミッター（120 req/min）、リトライ（指数バックオフ）、自動トークンリフレッシュ
  - fetch/save API：日足、財務、マーケットカレンダー
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（gzip対応）、XML の安全パース（defusedxml）、URL 正規化とトラッキング除去
  - SSRF対策（リダイレクト検査・プライベートIP遮断）
  - SHA256 ベースの記事ID生成、DuckDB への冪等保存（INSERT ... RETURNING）

- データスキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層の DDL を定義
  - init_schema() による初期化（ファイル作成含む）

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl(): カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分更新と backfill、品質チェックの集約（QualityIssue を返す）

- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間差分更新

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL と初期化
  - init_audit_db() で専用 DB を作成可能

- 品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合を検出
  - run_all_checks() でまとめて実行

- 設定管理（kabusys.config）
  - .env / .env.local / OS 環境変数の自動読み込み（ルート検出：.git または pyproject.toml）
  - 必須環境変数の検証 API（Settings クラス）

---

## 前提 / 必要環境

- Python 3.10 以上（typing の | None 構文などを使用）
- 推奨パッケージ（最低限）
  - duckdb
  - defusedxml

実際のプロジェクトでは requirements.txt を用意して pip install -r で依存を管理してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン（既にソースがある想定）

2. 仮想環境を作成・有効化
   - Unix / macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 環境変数を設定
   - プロジェクトルートに .env を作成すると、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

   - .env.local は .env の上書き（優先）として扱われます。OS 環境変数が最優先です。

5. DuckDB スキーマを初期化
   - Python REPL またはスクリプトで:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # ファイルを作成して全テーブルを生成

6. 監査ログ DB を別途初期化（任意）
   - from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")

---

## 使い方（簡単な例）

- 日次 ETL を実行する（J-Quants トークンは settings から利用）
  - 例:
    from kabusys.data import schema, pipeline
    from kabusys.config import settings

    conn = schema.init_schema(settings.duckdb_path)
    result = pipeline.run_daily_etl(conn)
    print(result.to_dict())

- ニュース収集ジョブを実行する
  - 例:
    from kabusys.data import schema
    from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

    conn = schema.init_schema("data/kabusys.duckdb")
    # known_codes は銘柄抽出に使用する有効なコード集合（例: {"7203","6758",...}）
    results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
    print(results)

- J-Quants の ID トークンを直接取得する
  - 例:
    from kabusys.data.jquants_client import get_id_token
    token = get_id_token()  # settings.jquants_refresh_token を使って取得

- 監査スキーマ初期化（既存接続に追加）
  - 例:
    from kabusys.data import schema
    from kabusys.data.audit import init_audit_schema

    conn = schema.init_schema("data/kabusys.duckdb")
    init_audit_schema(conn, transactional=True)

注意点:
- ETL の run_daily_etl() は内部で例外を個別に扱い、結果の ETLResult にエラー情報や品質問題（QualityIssue）を格納します。戻り値の has_errors / has_quality_errors 等をチェックして運用判断をしてください。
- settings は環境変数に依存します。必須変数が未設定だと ValueError が発生します。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略可, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (省略可, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) - デフォルト development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) - デフォルト INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化

---

## ディレクトリ構成

（リポジトリのルートは .git または pyproject.toml のある場所を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント（取得・保存）
      - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
      - pipeline.py            — ETL パイプライン（run_daily_etl など）
      - schema.py              — DuckDB スキーマ定義・初期化
      - calendar_management.py — マーケットカレンダー管理とバッチ更新
      - audit.py               — 監査ログ（signal/order/execution）テーブル
      - quality.py             — データ品質チェック
    - strategy/
      - __init__.py
      — （戦略関連モジュールを格納するためのパッケージ）
    - execution/
      - __init__.py
      — （発注/ブローカー連携に関するモジュール用）
    - monitoring/
      - __init__.py
      — （監視やメトリクス関連のモジュール用）

---

## 開発・運用上の注意

- DuckDB はシングルファイル DB を採用しており、マルチプロセス/マルチクライアントでの排他に注意してください。運用設計時は接続管理を検討してください。
- J-Quants API のレート制限やリトライ挙動は jquants_client に組み込まれていますが、別経路からの過剰呼び出しがないよう全体設計で注意してください。
- RSS 処理は外部入力を扱うため、defusedxml や SSRF 対策などを実装済みですが、実行環境のネットワーク制御やサイズ上限にも注意してください。
- 監査ログ（audit）には UTC タイムスタンプを採用しています。運用での時刻扱いは統一してください。

---

## 参考

- 主要 API のエラーハンドリングや設計方針は各モジュール（jquants_client, news_collector, pipeline, calendar_management, audit, quality）内の docstring に詳細があります。実装や拡張の際はそちらを参照してください。

---

ご要望があれば、README に含めるサンプルスクリプト、CI/デプロイ手順、より詳細な環境変数説明、あるいは requirements.txt の推奨セットアップ例などを追加します。どの情報が必要か教えてください。