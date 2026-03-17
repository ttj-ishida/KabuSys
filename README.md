# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）のリポジトリです。  
このリードミーは、コードベースに含まれる主要モジュールの概要、セットアップ手順、使い方、ディレクトリ構成などをまとめたものです。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に格納する ETL パイプライン
- RSS フィードからのニュース収集・前処理・銘柄紐付け
- マーケットカレンダー管理（営業日判定、次営業日の取得等）
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- 監査ログ（シグナル→発注→約定のトレース）用スキーマ
- （将来的に）戦略層・発注実行層・モニタリングとの連携を想定したモジュール構成

設計上の特徴：
- API レート制限とリトライ（指数バックオフ）に対応
- データの冪等保存（ON CONFLICT / DO UPDATE / DO NOTHING）
- SSRF や XML Bomb などの安全対策（ニュース収集）
- 時刻は UTC ベースでトレースを残す（fetched_at/created_at 等）

---

## 主な機能一覧

- 環境変数・設定の自動読み込み（.env / .env.local、必要変数チェック）
- J-Quants クライアント（株価日足・財務・マーケットカレンダー取得）
  - レート制限（120 req/min）、リトライ、トークン自動リフレッシュ
  - ページネーション対応、取得時刻（fetched_at）の記録
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集：RSS フェッチ、URL 正規化、本文前処理、記事ID（SHA-256）生成、DB への冪等保存、銘柄抽出・紐付け
- マーケットカレンダー管理（営業日判定、next/prev/get_trading_days、夜間バッチ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査スキーマ（signal_events / order_requests / executions）と初期化ユーティリティ

---

## システム要件 / 依存関係

- Python 3.10 以上（型ヒントに Union `|` を利用）
- 主要ランタイム依存パッケージ（最低限）:
  - duckdb
  - defusedxml

インストールはプロジェクトがパッケージ配布可能な状態であれば以下のどちらかを推奨します：

- 開発インストール（プロジェクトルートに pyproject.toml がある場合）:
  ```
  pip install -e .
  ```

- 必要パッケージを個別にインストールする場合:
  ```
  pip install duckdb defusedxml
  ```

ロギングや HTTP 通信に標準ライブラリ（logging, urllib）を使用しています。

---

## 環境変数

自動的に .env と .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑制可）。主な環境変数：

必須（実行に応じて必須）:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API パスワード
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack チャンネル ID

その他:
- KABUSYS_ENV            : 実行環境（development / paper_trading / live）※デフォルト development
- LOG_LEVEL              : ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）※デフォルト INFO
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            : (監視用) SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env 読み込みを無効化する場合に 1 を設定

注意: Settings クラスは必須のキーが未設定だと例外を投げます。

---

## セットアップ手順

1. リポジトリをクローン / 取得
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 環境を用意（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 依存パッケージをインストール
   - パッケージ配布設定があれば:
     ```
     pip install -e .
     ```
   - 最低依存だけ入れる場合:
     ```
     pip install duckdb defusedxml
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` を作成してください（.env.example があれば参照）。
   - 必須トークン類（JQUANTS_REFRESH_TOKEN 等）を設定します。

5. DuckDB スキーマ初期化
   - Python REPL / スクリプトで以下を実行して DB とテーブルを初期化します:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # デフォルトパス
     conn.close()
     ```

6. 監査ログ用スキーマ（任意）
   ```python
   from kabusys.data.schema import get_connection
   from kabusys.data.audit import init_audit_schema
   conn = get_connection("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（主要ユースケースの例）

以下はライブラリの主要機能を呼び出す最小例です。実際はログ設定やエラーハンドリング、スケジューラ（cron/airflow 等）との連携を考慮してください。

- ETL（デイリーパイプライン）実行例:
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（なければ作成）
  conn = init_schema(settings.duckdb_path)

  # ETL 実行（settings で指定したトークンを自動使用）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース収集（RSS）と銘柄紐付け例:
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  known_codes = {"7203", "6758"}  # 事前に有効銘柄リストを構築して渡す
  result = run_news_collection(conn, known_codes=known_codes)
  print(result)  # {source_name: saved_count}
  ```

- J-Quants からの株価取得（低レベル）:
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)

  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  jq.save_daily_quotes(conn, records)
  ```

- カレンダーの夜間バッチ更新:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved", saved)
  ```

- 品質チェック実行:
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

---

## 開発時のヒント

- 自動で .env を読み込む挙動はテストなどで邪魔になる場合があります。その場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- jquants_client は内部でレートリミッタとリトライを持っています。並列リクエストを行う際はそれを考慮してください（API 限度に注意）。
- news_collector はデフォルトで Yahoo Finance のビジネス RSS を参照します。ソースは引数で差し替え可能です。
- DuckDB のファイルはデフォルトで `data/kabusys.duckdb` に作成されます。`settings.duckdb_path` で変更可能です。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主なファイル一覧（src/kabusys 以下）です：

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定管理（.env 読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - news_collector.py             — RSS 取得・前処理・DB 保存・銘柄紐付け
    - schema.py                     — DuckDB スキーマ定義・初期化ユーティリティ
    - pipeline.py                   — ETL パイプライン（差分更新・バックフィル・品質チェック）
    - calendar_management.py        — マーケットカレンダーの管理ロジックとジョブ
    - audit.py                      — 監査ログ用スキーマ（signal/order/execution）
    - quality.py                    — データ品質チェックモジュール
  - strategy/
    - __init__.py                   — 戦略層（将来の拡張ポイント）
  - execution/
    - __init__.py                   — 発注実行層（将来の拡張ポイント）
  - monitoring/
    - __init__.py                   — モニタリング用モジュール（将来の拡張ポイント）

---

## 注意事項 / 制限

- 本パッケージは実際の発注処理や証券会社 API のラッパーを直接含んでいません。execution 層は拡張ポイントとして用意されています。実取引を行う際は十分なテストと安全対策（冗長性、冪等性、リスク制御）を実装してください。
- 環境変数や API トークンの管理は慎重に行ってください。公開リポジトリにトークンを置かないでください。
- DuckDB のトランザクションモデルやファイルロックの扱いについては運用環境の要件に合わせて検討してください（複数プロセスで同一 DB を同時書きする場合など）。

---

必要であれば README により詳しいチュートリアル（ETL のスケジューリング例、Docker 化、CI/CD、ユニットテストの実行方法等）を追加できます。どのトピックを優先して追加しますか？