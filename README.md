# KabuSys

日本株自動売買プラットフォームの一部を構成する Python パッケージ（簡易版）。  
データ取得・ETL・品質チェック・DuckDB スキーマ定義・監査ログなど、データパイプライン周りのコンポーネントを提供します。

主な目的は、J-Quants や kabuステーション 等の外部 API から市場データを取得し、DuckDB に永続化して戦略や実行ロジックへ渡すための堅牢な基盤を提供することです。

---

## 機能一覧

- 環境変数/設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須変数チェック（例: JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL 管理

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、JPX カレンダー取得
  - レート制限（120 req/min）対応（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - ページネーション対応、取得時刻（fetched_at）記録
  - DuckDB へ冪等的に保存する save_* 関数（ON CONFLICT DO UPDATE）

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義、テーブル作成の冪等初期化関数（init_schema、get_connection）

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL エントリポイント（run_daily_etl）
  - 差分更新（最終取得日からの差分取得、バックフィル設定）
  - 市場カレンダー先読み、品質チェックとの連携
  - ETL 実行結果を表す ETLResult（品質問題・エラーログを集約）

- データ品質チェック（kabusys.data.quality）
  - 欠損データ検出（OHLC 欠損）
  - スパイク検出（前日比の急騰・急落）
  - 主キー重複検出
  - 日付不整合（未来日付・非営業日のデータ）検出
  - 各チェックは QualityIssue オブジェクトを返却（error / warning）

- 監査ログ（kabusys.data.audit）
  - シグナル→発注要求→約定 を UUID 連鎖でトレース可能にする監査テーブル定義
  - 発注要求は冪等キー（order_request_id）を保持
  - init_audit_schema / init_audit_db による初期化サポート

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションの | 演算子等を使用）
- DuckDB を利用（Python パッケージ duckdb が必要）
- J-Quants API、kabuステーション（発注用）を利用する場合は各種トークン・パスワードが必要

1. リポジトリをクローン／配置（ソースは src/kabusys 以下に配置されています）  
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) または .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール  
   （本リポジトリに requirements.txt がない場合は最低限 duckdb を入れてください）
   - pip install duckdb
4. 環境変数の設定
   - プロジェクトルートに `.env` を作成すると自動的に読み込まれます（.env.local は上書き）
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
   - 必須環境変数（例）

例: .env（サンプル）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# Kabuステーション
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知等)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXXX

# DB パス（相対パスや絶対パス）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- 自動ロード順序: OS環境 > .env.local > .env
- プロジェクトルートは .git または pyproject.toml を基準に探索します。見つからない場合は自動ロードをスキップ。

---

## 使い方（主な API と実行例）

以下は基本的な使い方の例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイルに保存する DB を初期化
conn = init_schema("data/kabusys.duckdb")
```

あるいはインメモリ DB:
```python
conn = init_schema(":memory:")
```

2) J-Quants API からデータを取得して保存（個別呼び出し）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")

# トークンを settings から自動取得（.env で設定済みであること）
id_token = jq.get_id_token()

# 銘柄コード 7203（例）の日足を取得
records = jq.fetch_daily_quotes(id_token=id_token, code="7203", date_from=None, date_to=None)

# 保存
jq.save_daily_quotes(conn, records)
```

3) 日次 ETL を一括実行
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を省略すると本日（で営業日調整）
print(result.to_dict())
```
- run_daily_etl は市場カレンダー・株価・財務データの差分取得と保存、品質チェックを順に実行します。
- ETLResult に品質問題（QualityIssue のリスト）やエラーメッセージが含まれます。

4) 品質チェックのみ実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

5) 監査ログの初期化（既存の DuckDB 接続に追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```
監査専用 DB を別途作る場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabuステーション API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" をセットすると自動 .env 読み込みを無効化

必要な必須変数が欠けている場合、kabusys.config.Settings のプロパティアクセスで ValueError が発生します。

---

## ディレクトリ構成

パッケージは src/kabusys 以下に配置されています。主要ファイルを抜粋:

- src/
  - kabusys/
    - __init__.py
    - config.py                    -- 環境変数 / 設定管理、自動 .env 読み込み
    - data/
      - __init__.py
      - jquants_client.py          -- J-Quants API クライアント（取得・保存）
      - schema.py                  -- DuckDB スキーマ定義 & init_schema/get_connection
      - pipeline.py                -- ETL パイプライン（run_daily_etl 等）
      - audit.py                   -- 監査ログ（signal/order/execution テーブル）
      - quality.py                 -- 品質チェック
      - pipeline.py
    - strategy/
      - __init__.py                -- 戦略用パッケージ（骨格）
    - execution/
      - __init__.py                -- 発注／約定関連（骨格）
    - monitoring/
      - __init__.py                -- 監視用モジュール（骨格）

---

## 設計上のポイント / 注意事項

- J-Quants API のレート制限（120 req/min）を守るため固定間隔スロットリング実装が入っています。高頻度に複数スレッドから呼ぶ場合は注意してください。
- get_id_token はリフレッシュトークンから ID トークンを取得し、401 受信時に自動でリフレッシュする仕組みを持ちます（ただし無限再帰防止のため内部呼び出しでは自動リフレッシュを無効化する場面があります）。
- DuckDB スキーマのテーブルは全て冪等に作成されます。既存データは ON CONFLICT DO UPDATE で上書きされ、ETL の再実行が可能です。
- 品質チェックは Fail-Fast ではなく全件の問題を収集して返します。呼び出し元で重大度に応じた対処（警告のみ・ETL 中断等）を実装してください。
- 監査ログのタイムスタンプは UTC で保存する設計になっています（init_audit_schema は SET TimeZone='UTC' を実行）。

---

## 貢献 / 拡張案

- execution / strategy / monitoring パッケージに実際の戦略ロジックやブローカー向けコネクタ（kabuステーションの注文送信・取引照会）を実装する。
- ETL を Airflow 等のジョブスケジューラに組み込むための CLI / タスクラッパーを追加する。
- 品質チェックのカスタマイズや通知（Slack 連携）を追加して運用の自動化を強化する。

---

必要であれば README に CLI の具体的なコマンド例や、より詳細な .env.example、`pyproject.toml` / packaging の手順、ユニットテスト実行方法（pytest 等）を追記します。どの情報を追加したいか教えてください。