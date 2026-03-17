# KabuSys

日本株向け自動売買基盤（ライブラリ） — データ収集・ETL・品質チェック・監査ログ・発注基盤の基礎を提供します。

Version: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築のための共通ライブラリ群です。主に以下を提供します。

- J-Quants API を用いた株価・財務・マーケットカレンダーの取得クライアント（レート制御・リトライ・トークン自動更新対応）
- RSS からニュースを安全に収集して DuckDB に保存するニュースコレクタ（SSRF対策・サイズ制限・トラッキング除去）
- DuckDB 用のスキーマ定義および初期化ユーティリティ（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェックの実行）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- マーケットカレンダー管理（営業日判定・前後営業日取得・夜間更新ジョブ）
- 監査（signal → order → execution のトレーサビリティ）用スキーマ

設計上の主な特徴:
- 冪等性（DBINSERT は ON CONFLICT で上書き/スキップ）
- Look-ahead bias 防止のため取得時刻（fetched_at）を記録
- API レート制御・指数バックオフ・トークン自動リフレッシュ
- セキュリティ対策（XMLパース防御、SSRF対策、レスポンスサイズ制限）

---

## 機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンから id_token 取得）
  - save_* 系関数で DuckDB へ冪等保存
- data.news_collector
  - RSS 取得（gzip 対応）、記事正規化、記事ID生成、DuckDB への保存
  - SSRF、Gzip bomb、トラッキングパラメータ除去、安全な XML パース
- data.schema
  - DuckDB の全テーブル定義（Raw / Processed / Feature / Execution）と index の作成
  - init_schema() / get_connection()
- data.pipeline
  - run_daily_etl(): 市場カレンダー・株価・財務の差分取得と品質チェックの統合
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job(): 夜間での JPX カレンダー差分更新
- data.quality
  - 欠損・スパイク・重複・日付不整合のチェック、QualityIssue で結果を返す
- data.audit
  - 監査ログ用テーブル（signal_events / order_requests / executions）と初期化関数
- config
  - 環境変数ロード（.env / .env.local）と Settings オブジェクト（必須キー検査・型変換）

---

## 前提（Prerequisites）

- Python 3.10+
  - 型アノテーション（PEP 604）のため 3.10 以上を想定しています
- 主要依存パッケージ（最低限）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発用依存やパッケージ化されている場合は適宜 requirements.txt / setup.py を参照
```

---

## 環境変数 / 設定

config.Settings を通じて環境変数を参照します。プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）にある `.env` / `.env.local` を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能）。

主な環境変数（例）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネルID
- DUCKDB_PATH — デフォルトデータベースパス（例: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（例: data/monitoring.db）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）

README 等に `.env.example` を置くことを推奨します。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存ライブラリをインストール
   ```bash
   pip install duckdb defusedxml
   # その他に必要なパッケージがあれば追加でインストール
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` を作成（または CI に環境変数を設定）
   - 必須例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data import schema
     from kabusys.config import settings
     conn = schema.init_schema(settings.duckdb_path)
     ```

---

## 使い方（簡易ガイド）

以下は代表的なプログラム的利用例です。

- DuckDB を初期化して日次 ETL を実行する
  ```python
  from kabusys.data import schema, pipeline
  from kabusys.config import settings

  # DB 初期化（存在しないディレクトリは自動作成）
  conn = schema.init_schema(settings.duckdb_path)

  # 日次 ETL を実行（target_date を指定しなければ今日）
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース収集を実行する
  ```python
  from kabusys.data import news_collector, schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  # sources を渡すことでデフォルト以外の RSS も処理可能
  counts = news_collector.run_news_collection(conn, sources=None, known_codes=None)
  print(counts)  # {source_name: saved_count, ...}
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data import calendar_management, schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  saved = calendar_management.calendar_update_job(conn)
  print("saved calendar records:", saved)
  ```

- 監査スキーマ（audit）を追加する
  ```python
  from kabusys.data import audit, schema
  conn = schema.get_connection(settings.duckdb_path)
  audit.init_audit_schema(conn)
  ```

- J-Quants API を直接呼ぶ（トークンは Settings から自動で取得される）
  ```python
  from kabusys.data import jquants_client as jq

  # 直近の銘柄コード7203の株価を取得
  records = jq.fetch_daily_quotes(code="7203", date_from=..., date_to=...)
  ```

注意点:
- run_daily_etl や run_* ジョブは内部で例外を捕捉して処理を継続する設計ですが、戻り値の ETLResult.errors / quality_issues を必ず確認してください。
- 本ライブラリは「実行環境としての本番接続（証券会社への実注文など）」を含む場合は十分な事前検証と運用上の安全策が必要です。

---

## ディレクトリ構成

主要なファイル / モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得＆保存）
    - news_collector.py      — RSS ニュース収集・保存
    - schema.py              — DuckDB スキーマ定義 / 初期化
    - pipeline.py            — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py — マーケットカレンダー管理・ヘルパー
    - audit.py               — 監査ログスキーマと初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — （戦略モジュールのプレースホルダ）
  - execution/
    - __init__.py            — （実行/発注周りのプレースホルダ）
  - monitoring/
    - __init__.py            — （監視用モジュールのプレースホルダ）

（実際のリポジトリには README に掲載している以外のファイルやメタ情報があるかもしれません）

---

## 運用上の注意 / ベストプラクティス

- 環境変数は CI/CD や運用環境で安全に管理してください。`.env` をリポジトリにコミットしないこと。
- J-Quants のレート制限を尊重してください（実装では 120 req/min を想定）。
- DuckDB ファイルは定期的にバックアップを取ることを推奨します。
- ETL 実行時はログ（LOG_LEVEL）の確認と ETLResult の内容確認を自動化してください（例えば Slack 通知等）。
- 本ライブラリを証券会社 API と接続して自動発注する場合は、必ずペーパートレード（paper_trading）モードで十分なテストを行ってください。

---

必要であれば、README にサンプル .env.example、CI 用のジョブ定義、実運用用の推奨 crontab / systemd ユニット例、さらに詳細な API 使用例（パラメータの説明など）を追加します。どの情報が欲しいか教えてください。