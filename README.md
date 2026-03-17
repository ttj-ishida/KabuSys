# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。J-Quants API や RSS フィードから市場データ・ニュースを収集して DuckDB に保存し、ETL、品質チェック、監査ログ、カレンダー管理、発注・戦略インターフェースのための基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含むコードベースです。

- J-Quants API からの株価（日足）・財務データ・市場カレンダーの取得
- RSS ベースのニュース収集と銘柄紐付け
- DuckDB を用いた 3 層（Raw / Processed / Feature）データスキーマおよび初期化
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日の取得）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 発注・戦略・モニタリング用の名前空間（実装の拡張を想定）
- 環境変数ベースの設定管理（.env 自動読み込み機能あり）

設計上のポイント：
- API レート制限・リトライ・トークン自動リフレッシュ対応
- データ永続化は冪等（ON CONFLICT）で安全に
- ニュース収集は SSRF 対策・圧縮爆弾対策・トラッキングパラメータ除去など安全重視
- 品質チェックで欠損・スパイク・重複・日付不整合を検出し、呼び出し元で対処可能

---

## 主な機能一覧

- config
  - .env ファイル / 環境変数読み込み（自動読み込み: OS > .env.local > .env）
  - 必須変数未設定時はエラー通知
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能

- data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レート制御（120 req/min）、リトライ、ページネーション、UTC fetched_at 記録
  - DuckDB へ冪等保存（save_daily_quotes 等）

- data.news_collector
  - RSS フィード取得（gzip 対応、最大サイズ制限）
  - URL 正規化・トラッキング除去・記事ID は SHA-256 切り出しで冪等性
  - SSRF 防止（リダイレクト時のホスト検証）
  - DuckDB へ挿入（bulk、トランザクション、INSERT ... RETURNING）

- data.schema
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema で DuckDB を初期化（冪等）
  - idx（頻出クエリ向けインデックス）作成

- data.pipeline
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の一括処理
  - 差分更新・backfill 対応（デフォルト backfill 3 日）
  - ETLResult により詳細な結果を取得可能

- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間差分更新

- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks でまとめて実行し QualityIssue 列挙

- data.audit
  - signal_events / order_requests / executions 等の監査テーブル初期化（init_audit_schema）
  - 発注の冪等キー（order_request_id）や TIMESTAMP は UTC で保存する設計

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈の union 演算子 `|` 等を使用しているため）
- git 等の一般的なツール

1. リポジトリをクローン

   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成して有効化（推奨）

   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows (PowerShell: .venv\Scripts\Activate.ps1)

3. 依存パッケージをインストール

   pip install --upgrade pip
   pip install duckdb defusedxml

   ※他に必要なパッケージがある場合はプロジェクトの requirements.txt や pyproject.toml を参照して下さい。

4. 環境変数を設定
   - ルート（プロジェクトルート）に `.env` または `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例 (.env):

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb   # 任意、デフォルト
   SQLITE_PATH=data/monitoring.db    # 任意、デフォルト
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

5. DuckDB スキーマ初期化（例）

   Python REPL またはスクリプト内で:

   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)

   監査ログを別 DB として使う場合は init_audit_db / init_audit_schema を利用します。

---

## 使い方（主要な例）

以下は主な利用例です。実行は Python スクリプト/REPL から行えます。

- DuckDB スキーマ初期化

  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)
  # conn は duckdb.DuckDBPyConnection

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）

  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)
  print(result.to_dict())

- J-Quants API を直接使ってデータ取得

  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

  token = get_id_token()  # settings.jquants_refresh_token を使って idToken を取得
  records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- RSS ニュース収集と保存

  from kabusys.data.news_collector import run_news_collection

  known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット（必要なら）
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: saved_count}

- カレンダー夜間更新ジョブ

  from kabusys.data.calendar_management import calendar_update_job

  saved = calendar_update_job(conn)
  print(f"saved: {saved}")

- 監査ログ初期化（既存 conn に追加）

  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn)

- 品質チェック単体実行

  from kabusys.data.quality import run_all_checks

  issues = run_all_checks(conn)
  for i in issues:
      print(i)

注意点:
- API 呼び出し時のレート制御・リトライはライブラリ側で管理されますが、過度な同時実行は避けてください。
- ニュースフィード取得は外部ネットワークを利用するため、プロキシやファイアウォールの設定に注意してください。

---

## 環境変数一覧

主な環境変数（settings プロパティから取得）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略可、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (省略可、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live、デフォルト: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL、デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env の自動読込を無効化)

設定が不足していると Settings のプロパティアクセスで ValueError が投げられます（必須項目について）。

---

## ディレクトリ構成

主要ファイル／モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                - 環境変数・設定管理（.env 自動読込）
  - data/
    - __init__.py
    - jquants_client.py      - J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      - RSS ニュース収集・保存
    - schema.py              - DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py            - ETL パイプライン（差分更新・品質チェック等）
    - calendar_management.py - 市場カレンダー管理（営業日判定等）
    - audit.py               - 監査ログ（signal / order_request / executions）
    - quality.py             - データ品質チェック
  - strategy/
    - __init__.py            - 戦略用名前空間（拡張ポイント）
  - execution/
    - __init__.py            - 発注/約定/ポジション管理名前空間（拡張ポイント）
  - monitoring/
    - __init__.py            - モニタリング用名前空間（拡張ポイント）

その他:
- pyproject.toml / setup.py 等があればパッケージインストール手順に従ってください。

---

## 運用上の注意・ベストプラクティス

- 秘密情報（API トークン等）は .env に置く場合でもアクセス権に注意し、VCS にコミットしないでください。
- production（KABUSYS_ENV=live）ではログレベルやバックフィル設定、テストモードを慎重に設定してください。
- DuckDB ファイルはバックアップを定期的にとることを推奨します。
- ニュース収集・API 取得は外部サービスに負荷を与えないよう、スケジューリング間隔やレートを適切に設定してください。
- ETL の結果（ETLResult）や QualityIssue を監査・アラートに連携すると問題早期検知に有効です。

---

必要であれば、README にサンプル .env.example、より詳細な API 使用例、cron ベースの運用例、Dockerfile/Compose のテンプレートなどを追加できます。どれを追加しましょうか？