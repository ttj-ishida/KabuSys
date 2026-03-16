# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。  
データ取得・ETL、データ品質チェック、DuckDBスキーマ定義、監査ログ管理などを提供します。本リポジトリはライブラリ形式で、戦略・発注・監視などの上位モジュールと組み合わせて使用します。

## 主な特徴
- J-Quants API クライアント
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - API レート制限（120 req/min）対応のレートリミッタ
  - リトライ（指数バックオフ、最大 3 回）と 401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）をUTCで記録し、Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution の多層スキーマを定義
  - インデックスと制約込みでの初期化関数を提供
- ETL パイプライン
  - 差分更新（バックフィル対応）、市場カレンダー先読み、品質チェック統合
  - ETL 結果を ETLResult として返却（品質問題やエラーの集約）
- データ品質チェック
  - 欠損、スパイク（前日比）、主キー重複、日付不整合（未来日・非営業日）検出
  - 問題は QualityIssue オブジェクトで集約（severity: error/warning）
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティ用テーブルを定義
  - 発注の冪等性、ステータス管理、UTCタイムスタンプの方針を採用
- 環境変数ベースの設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検知）
  - 必須環境変数の明示と簡単なAPI（kabusys.config.settings）

---

## 必要な環境変数（主なもの）
以下はライブラリ内で参照・必須となる設定項目です。プロジェクト直下に `.env`（または `.env.local`）を置くと自動読み込みされます（自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須:
- JQUANTS_REFRESH_TOKEN  — J-Quants の refresh token
- KABU_API_PASSWORD      — kabuステーション API のパスワード
- SLACK_BOT_TOKEN        — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID       — Slack 通知先チャンネルID

オプション（デフォルトあり）:
- KABUS_API_BASE_URL     — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            — 実行環境 (development / paper_trading / live)、デフォルト: development
- LOG_LEVEL              — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)、デフォルト: INFO

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（開発向け）
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なライブラリをインストール
   - 要件ファイルがある場合: pip install -r requirements.txt
   - 最小で DuckDB を使うため: pip install duckdb

   （プロジェクトの pyproject.toml / requirements.txt を参照して依存を整えてください。）

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、必要な環境変数を OS に設定します。
   - 自動読み込みは `.git` または `pyproject.toml` を起点にプロジェクトルートを検出します。

4. DuckDB スキーマ初期化（例）
   - 以下の Python スニペットで DB を初期化できます。

   ```
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

5. 監査ログを別DBで作る場合:
   ```
   from kabusys.data import audit
   conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要 API と例）
- J-Quants クライアント直接利用
  ```
  from kabusys.data import jquants_client as jq
  token = jq.get_id_token()  # settings.jquants_refresh_token を利用して id_token を取得
  records = jq.fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))
  ```

- DuckDB へ保存
  ```
  conn = schema.init_schema("data/kabusys.duckdb")
  saved = jq.save_daily_quotes(conn, records)
  ```

- 日次 ETL の実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
  ```
  from kabusys.data import pipeline
  result = pipeline.run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

  run_daily_etl は品質チェックの結果（QualityIssue のリスト）やエラー情報を ETLResult にまとめて返します。

- 品質チェックのみ実行
  ```
  from kabusys.data import quality
  issues = quality.run_all_checks(conn, target_date=date(2026,1,15))
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- 設定取得
  ```
  from kabusys.config import settings
  print(settings.is_live, settings.duckdb_path)
  ```

注意点:
- jquants_client は内部でレート制御・リトライを行います。大量連続リクエスト時は API 制限に注意してください。
- ETL は差分更新を行うため、初回ロード時は過去全期間を取得します（最小開始日: 2017-01-01）。バックフィル期間で後出し修正を吸収します。

---

## 主要モジュール概要
- kabusys.config
  - 環境変数の読み込みと settings オブジェクト提供
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
- kabusys.data.jquants_client
  - J-Quants API とのやり取り（fetch / save / get_id_token）
  - レート制御、リトライ、ページネーション対応
- kabusys.data.schema
  - DuckDB の DDL 定義と init_schema / get_connection
- kabusys.data.pipeline
  - 差分 ETL（prices, financials, calendar）と run_daily_etl
- kabusys.data.quality
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- kabusys.data.audit
  - 監査ログ用テーブル定義と初期化関数
- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - 補助モジュール（実装の拡張ポイント）

---

## ディレクトリ構成
リポジトリの src 配下の主要ファイルは次のようになっています:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - schema.py
      - audit.py
      - quality.py
      - pipeline.py
      - audit.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主な機能は `kabusys.data` 配下にまとまっています。`config.py` は環境設定、`schema.py` は DuckDB スキーマ管理、`pipeline.py` が ETL の入り口です。

---

## 運用上の注意 / ベストプラクティス
- 本ライブラリは本番発注（live）とペーパートレード（paper_trading）を区別する設定が可能です。`KABUSYS_ENV` を適切に設定してください。
- 環境変数は機密情報を含むため、`.env` をバージョン管理に含めないでください。`.env.example` をリポジトリに置き、実運用環境では安全なシークレット管理を利用してください。
- DuckDB ファイルは定期的にバックアップを推奨します。監査ログは削除しない設計のため、容量や保持ポリシーも計画してください。
- API レート制限・リトライの方針は jquants_client に組み込まれていますが、外側でのスケジューリングや並列実行には注意してください。
- テスト実行時に自動 .env 読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

もし README に追加したい具体的な実行例（cron設定、Airflow 連携、Slack 通知サンプル）や、pyproject/requirements の情報があれば、その内容を反映してより詳細なセットアップ手順を作成します。必要な情報を教えてください。