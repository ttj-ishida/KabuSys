# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得、ETLパイプライン、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログなど、戦略や実行コンポーネントに必要な基盤機能を提供します。

---

## 概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- J-Quants API から株価・財務・カレンダー等の市場データを安全に取得
- DuckDB を用いたデータスキーマ定義と永続化（Raw / Processed / Feature / Execution レイヤ）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS からのニュース収集と銘柄紐付け（SSRF 対策・サイズ制限・トラッキング除去）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 環境変数による設定管理（.env 自動ロード機能あり）

設計上のポイント：
- API レート制限・リトライ・トークン自動リフレッシュを備えた堅牢なクライアント実装
- DuckDB への書き込みは冪等（ON CONFLICT / DO UPDATE）を原則
- ニュース取得はセキュリティ（defusedxml、SSRF ブロック、レスポンスサイズ制限）に配慮

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（株価・財務・カレンダー）
  - レートリミッタ、指数バックオフリトライ、401 時のトークン自動リフレッシュ
  - DuckDB へ冪等保存する save_* 関数

- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema(db_path) で初期化可能

- data.pipeline
  - 日次 ETL（run_daily_etl）
  - 差分取得・バックフィル・品質チェックの統合

- data.news_collector
  - RSS 取得、記事の前処理、ID 生成（URL 正規化 + SHA-256）
  - SSRF 対策、gzip 対応、受信サイズ制限、DuckDB への一括保存

- data.calendar_management
  - 市場カレンダーの更新、営業日判定、next/prev_trading_day、get_trading_days

- data.quality
  - 欠損・スパイク（前日比）・重複・日付不整合のチェック
  - QualityIssue 型で結果を返す

- data.audit
  - 監査ログ用スキーマ（signal_events / order_requests / executions）
  - init_audit_db による監査DB初期化

- config
  - 環境変数管理（.env/.env.local の自動読み込み、必須チェック）

---

## 要件

- Python 3.10+（一部の型注釈が利用されています）
- 主要外部ライブラリ（例）
  - duckdb
  - defusedxml

（実行環境によっては追加で標準ライブラリのみで動作する箇所がありますが、DuckDB を使う機能は duckdb が必須です）

例: requirements.txt に必要なパッケージを列挙してください（プロジェクト側で用意してください）。最低限は次のような行が必要です。
- duckdb
- defusedxml

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成する（任意）:
   ```bash
   git clone <repository-url>
   cd <repository-root>
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell 以外)
   ```

2. 依存関係をインストール:
   - requirements.txt がある場合:
     ```bash
     pip install -r requirements.txt
     ```
   - または手動で:
     ```bash
     pip install duckdb defusedxml
     ```

3. 環境変数の設定:
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと、自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで利用）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API のパスワード
     - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID : 通知先 Slack チャンネル ID
   - 任意（デフォルトあり）:
     - KABUS_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 `.env`（サンプル、実際のトークンやパスワードは別途設定）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. DuckDB スキーマ初期化:
   - data/schema.init_schema を使って DB を作成します（parent ディレクトリが無ければ自動作成されます）。
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```

5. （監査ログを別DBで運用する場合）監査DB初期化:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（基本例）

以下は Python スクリプトや対話環境から利用する簡単な例です。

- 日次 ETL を実行する:
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（既に初期化済みなら既存のファイルを指定）
  conn = init_schema("data/kabusys.duckdb")

  # 日次 ETL を実行
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 市場カレンダーの夜間バッチ更新:
  ```python
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved calendar rows: {saved}")
  ```

- RSS ニュース収集ジョブを実行（既存の known_codes セットを渡して銘柄紐付け）:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 監査スキーマの初期化（既存コネクションへ追加）:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.audit import init_audit_schema

  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=False)  # or transactional=True
  ```

- config の利用（環境変数を参照）:
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  if settings.is_live:
      print("本番モードです")
  ```

注意点:
- J-Quants クライアントは API レート制限（120 req/min）を守るため内部でスロットリングしています。
- fetch 系関数はページネーションに対応し、ID トークンはキャッシュ＋自動リフレッシュされます。
- news_collector は外部からの XML を安全に処理するため defusedxml を使用しています。

---

## ディレクトリ構成

リポジトリ内の主要なファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py       — RSS ニュース収集・前処理・保存
    - schema.py               — DuckDB スキーマ定義と初期化
    - pipeline.py             — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py  — マーケットカレンダー管理・営業日ユーティリティ
    - audit.py                — 監査ログ（signal/order/execution）スキーマ
    - quality.py              — データ品質チェック
  - strategy/
    - __init__.py             — 戦略関連（実装は別途）
  - execution/
    - __init__.py             — 発注実行関連（実装は別途）
  - monitoring/
    - __init__.py             — 監視 / メトリクス（実装は別途）

各モジュールは役割ごとに分離されており、戦略（strategy/）や実行（execution/）はこの基盤を使って実装される想定です。

---

## 運用・開発時の注意

- 環境変数管理
  - .env / .env.local はプロジェクトルート（.git または pyproject.toml のある場所）を起点に自動読み込みされます。
  - テスト時に自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- セキュリティ
  - news_collector は SSRF・XML BOM・gzip bomb 等の対策を組み込んでいますが、運用時には接続先リストの管理やタイムアウト設定を見直してください。

- 品質チェック
  - run_daily_etl は品質チェックで検出された問題（QualityIssue）を返します。エラー級の問題があれば呼び出し側で適切にアラート／停止判断を行ってください。

- テスト容易性
  - jquants_client の id_token はモジュールレベルでキャッシュされていますが、関数呼び出し時に id_token を注入可能です（テスト時は外部 API をモック可能）。

---

## 参考（実行例ワンライナー）

簡単に日次 ETL を試すワンライナー（仮想環境を有効にしたシェルで）:
```bash
python - <<'PY'
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
conn = init_schema("data/kabusys.duckdb")
res = run_daily_etl(conn)
print(res.to_dict())
PY
```

---

必要であれば、README にサンプル .env.example、requirements.txt、あるいは CLI ラッパー（管理用スクリプト）の使い方追記もできます。どの部分を拡張したいか教えてください。