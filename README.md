# KabuSys

日本株向け自動売買システムの基盤ライブラリです。  
データ取得・ETL、データ品質チェック、DuckDBスキーマ、監査ログ、戦略・発注・モニタリングの骨組みを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含むライブラリです。

- J-Quants API からの市場データ（OHLCV / 財務 / マーケットカレンダー）取得
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得、バックフィル、保存、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）
- 環境変数ベースの設定管理（.env 自動読み込み）

設計上のポイント:
- API レート制御（J-Quants: 120 req/min）とリトライ（指数バックオフ、401 は自動トークンリフレッシュ）
- データ取得時に fetched_at を記録して Look-ahead Bias を防止
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で上書き安全
- 品質チェックは Fail-Fast ではなく全件収集して呼び出し元が判断可能

---

## 機能一覧

- kabusys.config
  - .env ファイル自動読み込み（プロジェクトルート自動検出）
  - 必須設定の取得とバリデーション
- kabusys.data.jquants_client
  - get_id_token: リフレッシュトークンから ID トークンを取得
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - 保存用関数: save_daily_quotes / save_financial_statements / save_market_calendar
  - レートリミット制御、リトライ、401 自動リフレッシュ
- kabusys.data.schema
  - DuckDB のスキーマ定義（複数レイヤー）と初期化関数 init_schema/get_connection
- kabusys.data.pipeline
  - run_daily_etl: 日次 ETL（カレンダー取得 → 株価取得 → 財務取得 → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl（差分更新・バックフィル対応）
- kabusys.data.quality
  - 欠損、スパイク、重複、日付不整合のチェック（QualityIssue を返す）
  - run_all_checks による一括実行
- kabusys.data.audit
  - 監査用テーブルの定義・初期化（signal_events / order_requests / executions）
  - init_audit_schema / init_audit_db
- その他の名前空間: strategy, execution, monitoring（拡張ポイント）

---

## 動作要件

- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - （HTTP 標準ライブラリを使用しているため追加ライブラリは必須ではありませんが、実運用では requests 等を使うことがあります）
- データベース用ディスク領域（デフォルト: data/kabusys.duckdb）

※ 実際のセットアップ時は requirements.txt / pyproject.toml を確認して依存をインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン／配置

2. Python 仮想環境の作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb
   - （パッケージ化されている場合）pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を配置すると自動的に読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数（必須と省略時のデフォルト）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabu API のパスワード
   - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN (必須) — Slack 通知に使う Bot トークン
   - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
   - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH (任意) — デフォルト: data/monitoring.db
   - KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
   - LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで以下を実行して DB とテーブルを作成します。

   例:
   ```python
   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)
   ```

6. 監査ログテーブルの初期化（任意）
   ```python
   from kabusys.data import audit, schema
   conn = schema.get_connection(settings.duckdb_path)  # 既存 DB 接続
   audit.init_audit_schema(conn)
   ```

---

## 使い方（簡易ガイド）

以下は代表的な利用例です。

1. ID トークンの取得
   ```python
   from kabusys.data import jquants_client as jq
   id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
   ```

2. 市場データの取得と保存（単発）
   ```python
   import duckdb
   from kabusys.data import jquants_client as jq
   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.get_connection(settings.duckdb_path)
   records = jq.fetch_daily_quotes(code="7203", date_from=...)
   jq.save_daily_quotes(conn, records)
   ```

3. 日次 ETL 実行（推奨）
   ```python
   from kabusys.data import pipeline, schema
   from kabusys.config import settings

   conn = schema.get_connection(settings.duckdb_path)
   result = pipeline.run_daily_etl(conn)  # 引数で target_date, id_token, backfill_days 等を指定可
   print(result.to_dict())
   ```

   run_daily_etl の流れ:
   - market calendar を先に取得（lookahead）
   - 株価（差分 + backfill）
   - 財務（差分 + backfill）
   - 品質チェック（run_quality_checks=True がデフォルト）

4. 品質チェック単体実行
   ```python
   from kabusys.data import quality, schema
   conn = schema.get_connection("data/kabusys.duckdb")
   issues = quality.run_all_checks(conn, target_date=None)
   for i in issues:
       print(i)
   ```

5. 監査 DB を別途初期化する場合
   ```python
   from kabusys.data import audit
   conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 設計上の注意点 / 運用メモ

- J-Quants のレート制限（120 req/min）を守るため内部で固定間隔スロットリングを実装しています。極端な並列呼び出しは避けてください。
- HTTP リトライは 408, 429, 5xx、およびネットワークエラーに対して実施します。401 を受けた場合は refresh token による再取得を行い1回だけ再試行します。
- ETL は各ステップを独立してハンドリングし、あるステップが失敗しても他は継続します。最終的な結果は ETLResult に集約されます。
- DuckDB ファイルはデフォルトで repo 内の `data/kabusys.duckdb` に保存されます。永続化用のディレクトリは自動作成されます。
- 品質チェックで severity="error" の問題が見つかった場合は運用側で ETL を停止するか、アラートを上げるなどの判断を行ってください（run_all_checks はチェック結果を返すのみ）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数・設定管理（.env 自動読み込み・必須チェック）
    - data/
      - __init__.py
      - jquants_client.py — J-Quants API クライアント（取得 / 保存 / 認証 / レート制御）
      - schema.py — DuckDB スキーマ定義と init/get_connection
      - pipeline.py — ETL パイプライン（差分取得・バックフィル・品質チェック）
      - audit.py — 監査ログテーブルの定義・初期化
      - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - strategy/
      - __init__.py  — 戦略関連の拡張ポイント（実装はここに追加）
    - execution/
      - __init__.py  — 発注 / ブローカー連携の拡張ポイント
    - monitoring/
      - __init__.py  — モニタリング関連の拡張ポイント

---

## 開発 / 貢献

- 新しいチェックや ETL ステップ、戦略・実行ロジックは各モジュール下に追加してください。
- テスト用に .env の自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト実行時に外部環境に依存しないために有用）。

---

## 参考 / 追加情報

- DuckDB のテーブル定義は data/schema.py に全て記載されています。外部キーやインデックス、チェック制約を丁寧に設計しています。
- 監査ログはトレーサビリティ重視で削除しない運用を想定しており、すべて UTC タイムスタンプで保存します。
- 実際のブローカー連携（kabu STATION API の呼び出しや注文送信）は execution モジュールに実装できます（このリポジトリの骨組みを利用）。

---

必要であれば、README にサンプル .env.example の内容、より詳しい API リファレンス、または運用フロー（cron／Airflow での日次実行例）を追記します。どの情報が欲しいか教えてください。