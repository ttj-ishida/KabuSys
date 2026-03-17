# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ収集（J-Quants・RSS）、ETL、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定トレーサビリティ）、DuckDBスキーマ初期化などの基盤機能を提供します。

---

## 概要

KabuSys は日本株の自動売買システム構築に必要な「データ基盤」「ETL」「監査ログ」を中心に実装された Python パッケージです。  
主な設計方針は次の通りです。

- J-Quants API からの時系列・財務・カレンダーの差分取得（レート制御・リトライ・自動トークン更新）
- RSS フィードからのニュース収集（SSRF対策・XML攻撃対策・トラッキング除去・冪等保存）
- DuckDB を用いた階層化されたデータスキーマ（Raw / Processed / Feature / Execution / Audit）
- ETL は差分更新・バックフィル・品質チェックを備え、冪等性を重視
- 監査ログはシグナル→発注要求→約定までの完全トレースを保証

---

## 主な機能一覧

- 環境設定管理（.env / OS 環境変数の自動読み込み）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化
- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務、JPX カレンダーの取得
  - レート制限（120 req/min）・リトライ・トークン自動更新
  - 取得時刻（fetched_at）の記録、Look-ahead バイアス対策
  - DuckDB への冪等保存（ON CONFLICT で更新）
- ニュース収集モジュール
  - RSS フィード取得・前処理（URL除去・空白正規化）
  - URL 正規化と SHA-256 ベースの冪等記事 ID 生成
  - SSRF / XML 攻撃対策（defusedxml, リダイレクト検査, プライベートIP除外）
  - DuckDB へのトランザクション単位での保存（INSERT ... RETURNING）
  - テキストから銘柄コード抽出（既知コードに対して）
- ETL パイプライン
  - カレンダー・株価・財務データの差分更新（バックフィル対応）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL 実行結果を ETLResult に集約
- マーケットカレンダー管理
  - 営業日判定、次/前営業日取得、期間内営業日列挙
  - 夜間バッチでカレンダー差分更新
- DuckDB スキーマ初期化
  - Raw / Processed / Feature / Execution / Audit 各レイヤーのテーブル定義とインデックス
- 監査ログ（audit）
  - signal_events, order_requests, executions 等によるトレーサビリティ
  - UTC タイムゾーン設定や冪等性のための制約・インデックス

---

## セットアップ手順

前提
- Python 3.10 以上（コード内での型アノテーション（|）を使用しています）
- 要件ライブラリ（最低限）:
  - duckdb
  - defusedxml

1. リポジトリクローン / パッケージ配置
   - この README が置かれたプロジェクトルートを利用してください（.git または pyproject.toml によりルート検出）。

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージインストール
   例:
   ```bash
   pip install duckdb defusedxml
   ```
   （運用で Slack 等を使う場合は slack-sdk 等を追加してください）

4. 環境変数設定
   プロジェクトルートに `.env`（あるいは `.env.local`）を作成するか、OS 環境変数として設定します。  
   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL : kabu API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN : Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV : 実行環境 (development | paper_trading | live)（デフォルト: development）
   - LOG_LEVEL : ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. 自動 env ロードの無効化（テスト等で）
   - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env 自動読み込みを無効化します。

---

## 使い方（基本例）

以下は Python スクリプトや対話環境での利用例です。適宜ロギング設定を行ってください。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema

  # ファイル DB を初期化（親ディレクトリを自動作成）
  conn = schema.init_schema("data/kabusys.duckdb")
  # またはインメモリ
  # conn = schema.init_schema(":memory:")
  ```

- 監査ログスキーマ初期化（既存接続へ追加）
  ```python
  from kabusys.data import audit

  # conn は schema.init_schema の返り値を想定
  audit.init_audit_schema(conn)
  # もしくは監査専用 DB を初期化
  # audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
  ```

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data import pipeline
  from kabusys.data import schema

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn)  # target_date を指定することも可能
  print(result.to_dict())
  ```

- ニュース収集（RSS）と保存
  ```python
  from kabusys.data import news_collector
  from kabusys.data import schema

  conn = schema.init_schema("data/kabusys.duckdb")

  # 既定ソースを使って収集
  stats = news_collector.run_news_collection(conn)
  print(stats)

  # カスタムソースと既知銘柄コードセットを渡す例
  sources = {"my_site": "https://example.com/rss"}
  known_codes = {"7203", "6758"}
  stats = news_collector.run_news_collection(conn, sources=sources, known_codes=known_codes)
  ```

- カレンダー夜間バッチ更新
  ```python
  from kabusys.data import calendar_management, schema

  conn = schema.init_schema("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- J-Quants の ID トークンを明示的に取得
  ```python
  from kabusys.data import jquants_client as jq

  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
  ```

---

## 主要モジュール / ディレクトリ構成

簡略化したプロジェクト構成:

- src/kabusys/
  - __init__.py
  - config.py              : 環境変数と設定管理
  - data/
    - __init__.py
    - jquants_client.py    : J-Quants API クライアント（取得・保存）
    - news_collector.py    : RSS ニュース収集・保存・銘柄抽出
    - pipeline.py          : ETL パイプライン（差分更新・品質チェック）
    - schema.py            : DuckDB スキーマ定義・初期化
    - calendar_management.py : カレンダー判定・バッチ更新
    - audit.py             : 監査ログ（signal, order_request, executions）
    - quality.py           : データ品質チェック
  - strategy/
    - __init__.py          : 戦略関連（拡張ポイント）
  - execution/
    - __init__.py          : 発注/実行関連（拡張ポイント）
  - monitoring/
    - __init__.py          : 監視関連（拡張ポイント）

各ファイルの役割は README 上部の「主な機能一覧」参照。

---

## 設計上の注意 / ヒント

- DuckDB に対する DDL は冪等（CREATE IF NOT EXISTS）で記述されています。既存 DB がある場合は上書きされません。
- jquants_client は API レート制御（120 req/min）を内部で実施します。大量取得時は注意してください。
- ニュース収集は外部 RSS を扱うため SSRF 対策や最大レスポンスサイズ制限など安全性を考慮しています。 production での拡張時もこれらの方針を踏襲してください。
- 環境変数が足りない場合、Settings のプロパティで ValueError が発生します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用して明示的に環境を用意してください。
- Python の型アノテーションや設計はテスト容易性を考慮しており、id_token 等は引数で注入してモック可能です。

---

必要であれば README に「運用手順（cron/CI での ETL 実行例）」「テストの書き方（モックの差し替えポイント）」などを追加できます。追加希望があれば教えてください。