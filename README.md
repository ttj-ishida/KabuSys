# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
J-Quants や RSS を用いたデータ収集、DuckDB ベースのスキーマ定義、ETL パイプライン、品質チェック、監査ログなど、戦略実行に必要なデータ基盤とユーティリティを提供します。

---

## 概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API から株価（OHLCV）・財務データ・市場カレンダーを安全かつ冪等的に取得・保存する
- RSS フィードからニュース記事を収集して正規化・保存し、銘柄コードと紐付ける
- DuckDB 上のスキーマを定義・初期化し、ETL（差分取得・保存）パイプラインを実装する
- データ品質チェック（欠損、重複、スパイク、日付不整合）を実行する
- 監査ログ（signal → order → execution のトレーサビリティ）を保持する
- 市場カレンダー（JPX）の管理・営業日判定・夜間更新ジョブを提供する

設計上のポイント：
- API レート制御・リトライ・トークン自動リフレッシュ等の堅牢な HTTP ロジック
- DuckDB への保存は冪等（ON CONFLICT）で安全に上書き
- RSS 収集は SSRF・XML Bomb 等の攻撃対策や受信サイズ制限を実装

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足、財務、マーケットカレンダーの取得（ページネーション対応）
  - レートリミット、リトライ、トークン自動リフレッシュ
  - DuckDB への保存（save_*）は冪等
- RSS ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、記事ID の生成（SHA-256）、前処理、DuckDB 保存
  - SSRF・プライベートアドレス検査、gzip サイズ制限、XML 安全パーサ
  - 銘柄コード抽出・news_symbols への紐付け
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス作成と初期接続取得
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（DBの最終取得日から自動算出）、バックフィル、品質チェック、日次 ETL 実装
  - run_daily_etl により一括処理が可能
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日計算、期間内営業日列挙、夜間カレンダー更新ジョブ
- 品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合検出。QualityIssue オブジェクトで報告
- 監査ログ（kabusys.data.audit）
  - signal / order_request / executions テーブルでトレーサビリティ確保

---

## セットアップ手順

推奨 Python バージョン: 3.10+

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存ライブラリをインストール  
   （本コードで明示している依存の例：duckdb, defusedxml。実プロジェクトでは requirements.txt / pyproject.toml に従ってください）
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数を設定  
   プロジェクトルートの `.env`（と必要なら `.env.local`）に以下を設定してください（例）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   注意:
   - パッケージ起動時にプロジェクトルート（.git または pyproject.toml）を基準に自動で `.env` を読み込みます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. データベースの初期化（DuckDB）
   Python REPL やスクリプトから:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ファイルパスまたは ":memory:"
   ```

---

## 簡単な使い方（代表的な例）

- J-Quants の ID トークン取得（自動的に settings.jquants_refresh_token を使用）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings で指定したリフレッシュトークンから取得
  ```

- 日次 ETL の実行
  ```python
  from kabusys.data import pipeline, schema

  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
  result = pipeline.run_daily_etl(conn)  # 引数で target_date, id_token などを指定可能
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data import news_collector, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # デフォルトソースを使う場合
  res = news_collector.run_news_collection(conn)
  print(res)  # {source_name: 新規保存件数}
  ```

- DuckDB スキーマ初期化（監査ログも含める）
  ```python
  from kabusys.data import schema, audit

  conn = schema.init_schema("data/kabusys.duckdb")
  # 監査ログテーブルを追加
  audit.init_audit_schema(conn, transactional=True)
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data import quality, schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  ```

---

## 必要な環境変数

必須（未設定時は Settings が例外を投げます）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注系を使う場合）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack の投稿先チャンネル ID

任意（デフォルト値あり）:
- KABUSYS_ENV: 環境 (development | paper_trading | live)。既定: development
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)。既定: INFO
- DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（既定: data/monitoring.db）

.env の読み込み仕様:
- プロジェクトルート（.git または pyproject.toml を起点）から `.env` → `.env.local` の順で読み込みます。
- `.env.local` は `.env` を上書きします（ただし OS 環境変数は保護されます）。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

主要なファイル・モジュールの一覧（簡易ツリー）

- src/kabusys/
  - __init__.py
  - config.py                 # 環境設定・.env ロード・Settings
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント（fetch / save）
    - news_collector.py       # RSS 収集・正規化・保存・銘柄抽出
    - schema.py               # DuckDB スキーマ定義・初期化
    - pipeline.py             # ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py  # マーケットカレンダー更新・営業日判定
    - audit.py                # 監査ログスキーマ（signal / order / execution）
    - quality.py              # データ品質チェック
  - strategy/
    - __init__.py             # 戦略関連モジュール用プレースホルダ
  - execution/
    - __init__.py             # 発注 / 実行関連モジュール用プレースホルダ
  - monitoring/
    - __init__.py             # 監視用モジュール用プレースホルダ

各モジュールは用途別に分離されており、ETL / データ保存 / 品質チェック / 監査ログなどを個別に呼び出せます。

---

## 運用上の注意・ベストプラクティス

- 機密情報（API トークン等）は .env に保存する際も適切に管理してください。CI に入れる場合はシークレットストア推奨。
- DuckDB ファイルはバックアップ/スナップショットを検討してください（長期間の保持や監査要件に依存）。
- J-Quants のレート制限（120 req/min）を考慮して、並列呼び出しやスケジューラの設定に注意してください。jquants_client は固定間隔スロットリングを実装していますが、システム全体の呼び出し量は運用で監視してください。
- RSS 取得は外部ネットワーク依存のためタイムアウトや例外を適切にハンドルし、個別ソースの障害が全体を停止させない設計を保ってください（run_news_collection はソース単位でエラーを隔離します）。
- DuckDB のトランザクションは十分に理解した上で audit.init_audit_schema(... transactional=True) を使ってください（ネストトランザクションに注意）。

---

必要でしたら README に加える具体的なコマンド例（systemd 型のスケジューラや cron での定期実行設定、Slack 通知の使い方、CI/CD 用のセットアップ手順など）も作成します。どの情報を追加しましょうか？