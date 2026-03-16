# KabuSys

日本株向けの自動売買システム基盤 (KabuSys)。  
データ収集（J‑Quants）、ETL パイプライン、データ品質チェック、DuckDB によるスキーマ定義、監査ログ（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を主眼に設計されたライブラリです。

- J-Quants API からの時系列・財務・マーケットカレンダーの取得
- DuckDB を用いた層状データスキーマ（Raw / Processed / Feature / Execution）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- 監査ログ（シグナル→発注→約定のトレースを UUID で連鎖）
- 冪等性・レート制御・リトライロジック等の実運用向け配慮

設計上のポイント：
- API レート制限（120 req/min）を順守する固定間隔のレートリミッタ
- リトライ（指数バックオフ、最大 3 回）、401 時は自動トークンリフレッシュ
- ETL は差分更新かつ冪等（ON CONFLICT DO UPDATE）で実装
- 品質チェックは Fail‑Fast とせず問題を全件収集して呼び出し元が判断可能

---

## 機能一覧

- 環境設定読み込み（.env / .env.local / OS 環境変数、自動ロード機構）
- J-Quants クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - トークン管理（リフレッシュ・キャッシュ）
- DuckDB スキーマ定義・初期化
  - raw_prices / raw_financials / market_calendar / features / signals / orders / trades / positions / 監査ログ等
- ETL パイプライン
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得・バックフィル（デフォルト 3 日）
- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付不整合チェック
- 監査ログ（signal_events / order_requests / executions）
- ユーティリティ（データ型変換、レートリミット、ログ出力）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に `|` を使用しているため）
- pip が利用可能

1. リポジトリをクローン（もしくはパッケージ配布に従ってインストール）:

   git clone <your-repo-url>
   cd <your-repo>

2. 仮想環境を作成・有効化（任意）:

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール:

   pip install duckdb

   （本リポジトリに setup/requirements ファイルがあれば `pip install -e .` または `pip install -r requirements.txt` を使用）

4. 環境変数を設定する（.env ファイルをプロジェクトルートに置くと自動で読み込まれます）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等）。

例: .env（最低限必須の変数）

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb      # 任意（デフォルト）
   SQLITE_PATH=data/monitoring.db       # 任意（デフォルト）
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

注意: 必須項目はコードの Settings で _require() されます（未設定だと ValueError）。

---

## 使い方

基本的なワークフロー例（DuckDB スキーマ初期化 → 日次 ETL 実行）を示します。

1) DuckDB スキーマ初期化

Python スクリプト例:

   from kabusys.config import settings
   from kabusys.data import schema

   conn = schema.init_schema(settings.duckdb_path)
   # これで全テーブルとインデックスが作成されます（既存ならスキップ）。

監査ログのみを追加する場合:

   from kabusys.data import audit
   audit.init_audit_schema(conn)

2) 日次 ETL 実行

   from kabusys.config import settings
   from kabusys.data import schema, pipeline

   # DB 初期化（まだなら）
   conn = schema.init_schema(settings.duckdb_path)

   # 日次 ETL を実行（省略すると target_date は today）
   result = pipeline.run_daily_etl(conn)
   print(result.to_dict())

ETL の返り値は ETLResult（target_date, fetched/saved 件数, quality_issues, errors）です。
quality_issues は詳細（check_name, severity, message, rows のサンプル）を含みます。

3) J-Quants API を直接使う（必要に応じて）

   from kabusys.data import jquants_client as jq
   # トークンを明示的に渡すか、モジュールキャッシュを使う
   data = jq.fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))

4) ログレベルの調整

環境変数 `LOG_LEVEL` を設定してログ出力の閾値を変更します（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

5) 自動 .env 読み込みの動作

- プロジェクトルートはこのパッケージファイルから上方向に `.git` または `pyproject.toml` を探索して決定します。
- 見つかれば `.env` を読み込み、続けて `.env.local`（存在すれば上書き）を読み込みます。
- OS 環境変数は保護され、.env の値で上書きされません（`.env.local` は上書き可）。
- 自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

主要なファイル/モジュール（src/kabusys 以下）:

- __init__.py
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]

- config.py
  - 環境変数の読み込み（.env サポート）、Settings クラス（必要な環境設定をプロパティで取得）

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・リトライ・レート制御・保存関数）
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - schema.py
    - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）
    - init_schema(db_path), get_connection(db_path)
  - pipeline.py
    - ETL パイプライン（差分更新・バックフィル・品質チェック）
    - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - QualityIssue データクラス、run_all_checks
  - audit.py
    - 監査ログ（signal_events, order_requests, executions）DDL と初期化
    - init_audit_schema, init_audit_db
  - (将来的なファイル) raw news / executions などに対応するテーブル DDL

- strategy/
  - __init__.py
  - （戦略ロジックを配置するためのプレースホルダ）

- execution/
  - __init__.py
  - （実際のブローカー発注・約定処理を実装するモジュール群向けプレースホルダ）

- monitoring/
  - __init__.py
  - （監視・アラート用のコードを配置）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ('development' | 'paper_trading' | 'live')（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化するには 1 を設定

---

## サンプル: 最小実行スクリプト

save as run_etl.py:

   #!/usr/bin/env python3
   from kabusys.config import settings
   from kabusys.data import schema, pipeline

   def main():
       conn = schema.init_schema(settings.duckdb_path)
       result = pipeline.run_daily_etl(conn)
       print(result.to_dict())

   if __name__ == "__main__":
       main()

実行:

   python run_etl.py

---

## トラブルシューティング / 注意点

- 必須の環境変数が未設定だと Settings プロパティが ValueError を投げます。ログや例外メッセージを確認してください。
- J-Quants の API レート制限（120 req/min）を踏まえ、fetch は内部でスロットリングします。大量のリクエストを並列で投げる実装は避けてください。
- DuckDB のファイルパスの親ディレクトリが存在しない場合、init_schema が自動で作成します。
- audit.init_audit_schema() は既存の接続に監査テーブルを追加します。監査テーブルは削除しない前提です。
- テスト時などに .env の自動読み込みを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 今後の拡張案 / TODO（参考）

- strategy と execution モジュールに具体的な戦略・証券会社 API アダプタを実装
- Slack 通知やモニタリングの標準化
- CI/CD 用の DB 初期化・マイグレーション機能
- 分散処理・メトリクス収集との統合

---

ライセンスやコントリビュート情報はプロジェクトに合わせて追記してください。必要であれば README に実行例（より詳細なコマンドや Docker サポート等）を追加します。