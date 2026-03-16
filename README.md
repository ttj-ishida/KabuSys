# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買システムのコアライブラリ（データ基盤・ETL・監査ログ・API クライアント等）です。J-Quants API から市場データ・財務データ・マーケットカレンダーを取得して DuckDB に格納し、データ品質チェックや監査ログ（発注 → 約定のトレーサビリティ）を提供します。

## 機能一覧
- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）準拠のスロットリング
  - 再試行（指数バックオフ、最大 3 回）、HTTP 401 時の自動トークンリフレッシュ
  - ページネーション対応、取得時刻（fetched_at）を UTC で保存
- DuckDB スキーマ定義 / 初期化
  - Raw / Processed / Feature / Execution の多層スキーマ
  - インデックスと制約を含む冪等な DDL
- ETL パイプライン（差分更新）
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - バックフィル（日次の再取得）を考慮した差分取得ロジック
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- データ品質チェック
  - QualityIssue による問題収集（error / warning）
  - Fail-Fast ではなく全件収集して呼び出し元が判断可能
- 監査ログ（audit）
  - signal_events / order_requests / executions の監査テーブル
  - 発注フローを UUID 連鎖で完全トレース（冪等キーのサポート）
  - UTC タイムスタンプ保証

---

## セットアップ手順

前提:
- Python 3.10+（typing のユニオン記法や型ヒントを利用）
- ネットワークから J-Quants API にアクセス可能

1. リポジトリをクローン／配置
2. 依存パッケージをインストール
   - このコードベースで外部ライブラリとして使用しているものは duckdb です。インストール例:
     ```
     pip install duckdb
     ```
   - 必要に応じて仮想環境を作成してください（venv / pyenv 等）。

3. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（デフォルトで自動ロードされます）。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（このライブラリで _require() により必須とされるもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 任意の設定:
     - KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
     - LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

   - 例 `.env`（必要な環境変数だけを示す）:
     ```
     JQUANTS_REFRESH_TOKEN="xxxxxxxxxxxxxxxx"
     KABU_API_PASSWORD="your_kabu_password"
     SLACK_BOT_TOKEN="xoxb-..."
     SLACK_CHANNEL_ID="C01234567"
     DUCKDB_PATH="data/kabusys.duckdb"
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データベースディレクトリの作成はライブラリ側で自動作成されます（init_schema / init_audit_db が親ディレクトリを作成）。

---

## 使い方（短いガイド）

基本的なワークフローは以下の通りです。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   監査ログテーブルも追加する場合:
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```
   監査専用 DB を別に作る場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

2. J-Quants トークン取得（必要に応じて）
   ```python
   from kabusys.data.jquants_client import get_id_token
   id_token = get_id_token()  # settings.JQUANTS_REFRESH_TOKEN を使用して取得
   ```

3. 日次 ETL 実行（最も簡単な例）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を省略すると今日
   print(result.to_dict())
   ```
   引数で id_token やバックフィル日数、品質チェックの閾値を調整可能:
   ```python
   result = run_daily_etl(conn, id_token=id_token, backfill_days=5, spike_threshold=0.4)
   ```

4. ETL 内部機能を個別に呼ぶ
   - 株価だけ差分更新したい場合:
     ```python
     from datetime import date
     from kabusys.data.pipeline import run_prices_etl
     fetched, saved = run_prices_etl(conn, target_date=date.today())
     ```
   - 財務データ、カレンダー ETL も同様に run_financials_etl/run_calendar_etl を使用。

5. 品質チェック
   ```python
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn, target_date=None)  # 全日または target_date 指定
   for i in issues:
       print(i)
   ```

6. J-Quants API の直接呼び出し
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
   quotes = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
   financials = fetch_financial_statements(code="7203")
   ```

注意点 / 実装上のポイント:
- jquants_client は内部でレート制御（120 req/min）、リトライ、401 の自動トークンリフレッシュ、ページネーション処理を行います。
- 保存関数（save_*）は DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）します。
- データ品質チェックは重大度付きの QualityIssue を返し、ETL は重大な品質問題があっても全チェックを行ってから呼び出し元へ返します（呼び出し元での判断を想定）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なソースは `src/kabusys` 配下にあります。ここでは主要なモジュールを列挙します。

- src/
  - kabusys/
    - __init__.py  — パッケージ定義（バージョン: 0.1.0）
    - config.py    — 環境変数/設定の読み込み、Settings クラス（.env の自動読み込み含む）
    - data/
      - __init__.py
      - jquants_client.py  — J-Quants API クライアント（取得・ページネーション・保存関数）
      - schema.py         — DuckDB スキーマ定義と init_schema / get_connection
      - pipeline.py       — ETL パイプライン（差分更新、run_daily_etl 他）
      - audit.py          — 監査ログ（signal_events, order_requests, executions）
      - quality.py        — データ品質チェック（欠損、スパイク、重複、日付不整合）
    - strategy/
      - __init__.py  — 戦略層（拡張用）
    - execution/
      - __init__.py  — 発注/実行層（拡張用）
    - monitoring/
      - __init__.py  — 監視用モジュール（拡張用）

---

## 環境変数（一覧）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意:
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env の自動ロードを無効化)

---

## テスト・ローカル開発におけるヒント
- テスト時に .env の自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。
- DuckDB をインメモリで使うには `db_path=":memory:"` を指定して init_schema を呼べます。
- jquants_client の get_id_token は allow_refresh=False を内部で利用している呼び出しがあるため、無限再帰を避ける設計になっています。テストでは明示的に get_id_token の戻り値をモックするのが簡単です。

---

必要に応じて README を拡張して、CI/CD、デプロイ手順、運用ガイド（モニタリング、Slack 通知の使い方）や戦略層・発注層の実装例を追加できます。追加したい内容があれば指示してください。