# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータ取得・加工・品質検査・監査ログ・ETL パイプラインを備えた自動売買プラットフォームのコアライブラリです。J-Quants API からのマーケットデータ取得、DuckDB ベースのスキーマ管理、ETL パイプライン、品質チェック、監査ログ（発注→約定のトレース）などを提供します。

---

## 概要

主な目的は、以下を安全かつ再現性を持って行うことです。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB による階層化されたデータスキーマ（Raw / Processed / Feature / Execution / Audit）
- 差分中心の ETL パイプライン（バックフィル対応・品質チェック含む）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注要求→約定の UUID ベースのトレーサビリティ）

設計上のポイント:
- API レート制限とリトライ（指数バックオフ）を厳守
- データ取得日時（fetched_at）や監査用タイムスタンプは UTC を基本
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）を採用

---

## 機能一覧

- 環境変数/設定管理（`.env` の自動ロード、必須変数チェック）
- J-Quants クライアント
  - ID トークン取得（リフレッシュ）
  - 日足（OHLCV）取得（ページネーション対応）
  - 財務諸表取得（ページネーション対応）
  - マーケットカレンダー取得
  - レートリミッタ・リトライ・401 トークン自動リフレッシュ
  - DuckDB への保存用ユーティリティ（冪等保存）
- DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit のテーブル群）
- ETL パイプライン（差分更新、バックフィル、カレンダー先読み、品質チェック）
- 品質チェックモジュール（欠損、スパイク、重複、日付不整合）
- 監査ログ初期化（signal_events / order_requests / executions）

---

## セットアップ手順

以下は基本的なローカルセットアップ例です。リポジトリに requirements.txt や pyproject.toml があればそちらを使ってください。

1. Python 仮想環境の作成（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージのインストール
   - 最低限 DuckDB が必要です。プロジェクト固有の依存がある場合は requirements.txt に従ってください。
   ```
   pip install duckdb
   ```
   （他に requests / slack SDK 等が必要になる機能がある場合は追加でインストールしてください）

3. パッケージのインストール（編集可能なインストール）
   ```
   pip install -e .
   ```
   （プロジェクトルートが pyproject.toml / setup.cfg / setup.py を持つ場合）

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（デフォルト）。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下は Python REPL やスクリプトから呼び出す最小利用例です。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # デフォルトパスを使用
   ```

2. J-Quants トークン取得・データ取得（単体）
   ```python
   from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

   id_token = get_id_token()  # settings.jquants_refresh_token を使って自動で取得
   quotes = fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,12,31))
   ```

3. ETL（日次パイプライン）を実行する
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.config import settings
   from datetime import date

   conn = init_schema(settings.duckdb_path)
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

4. 監査ログスキーマの初期化（監査テーブルを追加）
   ```python
   from kabusys.data.audit import init_audit_schema
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   init_audit_schema(conn)
   ```

5. 環境変数自動ロードの制御
   - デフォルトではプロジェクトルート（.git または pyproject.toml を探す）から `.env` → `.env.local` を自動的に読み込みます。
   - 自動読み込みを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

注意点:
- ETL は差分更新を基本とします。run_daily_etl は市場カレンダーを先に取得し、営業日に合わせて株価・財務を差分取得します。
- 設定や環境に合わせて DB パス、ログレベル、J-Quants トークンなどを確実にセットしてください。

---

## ディレクトリ構成（主要ファイルと説明）

（パスは src/kabusys 以下を示す）

- src/kabusys/
  - __init__.py
    - パッケージ初期化。__version__ = "0.1.0"
  - config.py
    - 環境変数管理モジュール
    - .env 自動ロード、必須変数チェック、settings オブジェクトを提供
    - KABUSYS_ENV / LOG_LEVEL の検証
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レート制御・リトライ・トークン管理）
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
      - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB 保存）
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection を提供
      - Raw / Processed / Feature / Execution レイヤーのテーブル定義
    - pipeline.py
      - ETL パイプライン（差分更新・バックフィル・品質チェック）
      - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
      - ETLResult データクラス
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）の DDL と init 関数
      - トレーサビリティを担保するテーブル群
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
      - QualityIssue 型と run_all_checks
  - strategy/
    - __init__.py
    - （戦略実装はここに配置する想定）
  - execution/
    - __init__.py
    - （発注/ブローカー連携ロジックを配置する想定）
  - monitoring/
    - __init__.py
    - （監視・メトリクス用モジュールを配置する想定）

---

## 追加情報・運用メモ

- ロギング:
  - LOG_LEVEL（環境変数）によりログレベルを制御できます。
- 環境の種類:
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかで、運用モードに応じた設定分岐に利用します。
- .env のパース:
  - export KEY=val, シングル/ダブルクォート対応、行内コメント処理などの柔軟なパースを行います。
- レート制御:
  - J-Quants は 120 req/min を想定し、内部で固定間隔スロットリングを実装しています。
- 冪等性:
  - DuckDB への挿入は ON CONFLICT DO UPDATE を採用しており、再実行での上書きが可能です。

---

## 貢献・拡張案

- strategy と execution パッケージに戦略ロジックやブローカードライバを実装してフルパイプライン化する。
- Slack や監視ツールへのアラート連携を追加（monitoring モジュールを拡張）。
- 品質チェックの追加や AI スコア計算モジュールの実装（features / ai_scores 層）。
- 単体テスト、E2E テスト用のテストケース追加（KABUSYS_DISABLE_AUTO_ENV_LOAD を活用）。

---

必要であれば、README に含める具体的なサンプルスクリプト（cron 用の ETL バッチ、監査ログの利用例、戦略プラグインの雛形など）を作成します。どの部分を詳しく載せたいか教えてください。