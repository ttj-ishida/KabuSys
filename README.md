# KabuSys

KabuSys は日本株の自動売買 / データプラットフォーム向けのライブラリ群です。  
J-Quants API から市場データを取得して DuckDB に保存し、ETL（差分更新・バックフィル）、品質チェック、監査ログ（シグナル→発注→約定のトレーサビリティ）を提供することを目的としています。戦略実行・発注連携・監視周りのコンポーネントも想定された構成になっています。

主な設計方針:
- データ取得は冪等（ON CONFLICT DO UPDATE）で保存
- API レート制限・リトライ（指数バックオフ）を考慮
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログでシグナルから約定までトレース可能にする

---

## 主な機能一覧

- J-Quants API クライアント（株価日足・財務・マーケットカレンダー取得）
  - レートリミッタ（120 req/min）
  - リトライ（408/429/5xx、指数バックオフ）
  - 401 時に自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
- ETL パイプライン（差分更新 / バックフィル / 品質チェック）
  - 市場カレンダー取得 → 株価日足取得 → 財務取得 → 品質チェック
  - 差分自動計算（DB の最終取得日から必要な範囲のみ取得）
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義を含む初期化関数
- 監査（Audit）テーブル（signal_events, order_requests, executions）
  - 発注冪等キー / ステータス管理 / UTC タイムスタンプ
- データ品質チェックモジュール
  - 欠損データ、スパイク、重複、日付不整合を検出し QualityIssue を返す

---

## 要件（代表）

- Python 3.10+
- duckdb
- （J-Quants API 利用のため）インターネット接続
- 必要な環境変数（下記参照）

※ 実際のプロジェクトで使用する際は requirements.txt / poetry 等で依存関係管理してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（例: duckdb）。
   - pip install duckdb

   （プロジェクトで requirements.txt を用意している場合はそれを利用してください）

3. 環境変数ファイル（.env）をプロジェクトルートに作成します。  
   自動読み込みについて:
   - パッケージ起動時に .git または pyproject.toml の位置を探索してプロジェクトルートを特定し、.env → .env.local の順で読み込みます。
   - OS 環境変数が優先され、.env.local は .env を上書きします。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. DuckDB の初期化はコードから行います（下記 Usage 参照）。

---

## 環境変数

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack のチャンネル ID

オプション / デフォルトあり:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化（任意）

注意:
- Settings クラス経由で環境変数を取得します。未設定の必須変数を要求すると ValueError を送出します。

---

## 使い方（Quickstart）

以下は代表的な利用例です。実行は Python コンソールやスクリプトから行います。

1) DuckDB スキーマを初期化して接続を取得する
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 監査ログテーブルを追加で初期化する
```python
from kabusys.data import audit
# 既に init_schema() で取得した conn を渡す
audit.init_audit_schema(conn)
# または監査専用 DB を初期化する
conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
# conn は init_schema() で得た DuckDB 接続
result = run_daily_etl(conn)
print(result.to_dict())
```

4) J-Quants からデータを直接取得する（トークン自動管理あり）
```python
from kabusys.data import jquants_client as jq
# 全銘柄の指定期間の株価を取得
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
# 保存
jq.save_daily_quotes(conn, records)
```

5) 品質チェックを実行する
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

---

## 実装上のポイント / 動作注意点

- API クライアント:
  - レート制限を守るため固定間隔スロットリングを実装（120 req/min）。
  - 408/429/5xx に対して指数バックオフで最大リトライ（デフォルト 3 回）。
  - 401 を受信した場合はリフレッシュトークンから ID トークンを取得して 1 回リトライ。
  - ページネーション対応（pagination_key を利用）。

- ETL:
  - 差分更新を行い、未取得データのみを取得する。backfill_days を指定すると最終取得日の数日前から再取得して API の後出し修正に備えます。
  - 各ステップはエラーハンドリングされ、1 ステップが失敗しても他は継続（エラーは ETLResult に集約）。
  - 市場カレンダーは先読み（lookahead）して取得します。カレンダー取得後に target_date を営業日に調整してから株価・財務の取得を行います。

- DuckDB スキーマ:
  - Raw / Processed / Feature / Execution 層を定義。
  - ON CONFLICT DO UPDATE を用いて冪等性を担保。
  - audit モジュールでは UTC タイムゾーン強制など監査要件に配慮。

- データ品質チェック:
  - Fail-Fast ではなく、すべてのチェックを実行して QualityIssue のリストを返す（呼び出し元が方針を決定）。
  - スパイク判定はデフォルトで前日比 50% を閾値とするがパラメータで変更可能。

---

## ディレクトリ構成

以下は主なファイルとモジュールの概観です（リポジトリの src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数読み込み・自動 .env ロード）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch/save 関数、認証・リトライ・レート制御）
    - schema.py
      - DuckDB の DDL 定義と init_schema / get_connection
    - pipeline.py
      - 日次 ETL のメイン処理（run_daily_etl 等）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログ用テーブル定義・初期化
    - (その他: audit/schemas など)
  - strategy/
    - __init__.py (戦略関連は拡張ポイント)
  - execution/
    - __init__.py (発注 / 執行関連は拡張ポイント)
  - monitoring/
    - __init__.py (監視 / アラート周りは拡張ポイント)

---

## 開発・拡張ポイント

- strategy と execution パッケージはプレースホルダになっており、戦略の実装、リスク管理、ブローカー API 連携などを実装する想定です。
- 監視（monitoring）モジュールは、Slack 通知・メトリクス・健全性チェックを実装するための拡張ポイントです。Settings に Slack トークンの設定があるため、通知実装が容易です。
- テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効にできます。
- DuckDB はファイルベースなので CI では ":memory:" を使った接続でテスト可能です。

---

## 付記

この README はコードベースの現状実装（src/kabusys 以下）に基づいて作成しています。実運用では依存パッケージ管理、資格情報の安全な保管、監査ログの保存先ポリシー、ブローカーとの接続テスト、バックテスト・サンドボックス実行などを整備してください。

ご不明点や README に追記したい内容があれば教えてください。