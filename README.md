# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（プロトタイプ）

短い概要:
- J-Quants / kabuステーション 等から市場データを取得し、DuckDB に保存・管理するためのモジュール群
- ETL（差分取得・バックフィル・品質チェック）、スキーマ（Raw/Processed/Feature/Execution 層）、監査ログ（発注～約定トレーサビリティ）を提供
- 戦略・実行・監視のための基盤を構築することを目的とする

---

## 主な機能一覧

- データ取得（J-Quants API）
  - 日次株価（OHLCV）のページネーション対応取得
  - 四半期財務データ（BS/PL）
  - JPX マーケットカレンダー（祝日・半日・SQ）
  - レートリミット（120 req/min）の遵守、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ等の堅牢化

- データ保存（DuckDB）
  - Raw / Processed / Feature / Execution 層のDDLを定義
  - 冪等な保存（INSERT ... ON CONFLICT DO UPDATE）による二重登録回避
  - 監査ログ（signal_events / order_requests / executions）用スキーマ

- ETL パイプライン
  - 差分更新・バックフィル（デフォルト 3 日）・カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損、スパイク、重複、日付不整合）を実行し、問題は QualityIssue として収集

- 品質チェック
  - 欠損データ検出（OHLC 欠損）
  - スパイク検出（前日比閾値 50% をデフォルト）
  - 主キー重複検出
  - 将来日付 / 非営業日のデータ検出

---

## セットアップ手順

前提: Python 3.9+（コードは型アノテーション等を使用）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - duckdb 等をインストールします（本プロジェクトは最低限 duckdb が必要です）。
     - pip install duckdb
   - 本パッケージを開発モードでインストールする場合:
     - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を配置することで自動読み込みされます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境変数で設定します。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token でIDトークンを取得するために使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を指定すると .env 自動ロードを無効化
- KABUSYS_API_BASE_URL: kabu API ベース URL（デフォルト内蔵値あり）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: monitoring 用 SQLite パス（デフォルト: data/monitoring.db）

サンプル .env（例）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

Python API を用いた基本的なワークフロー例を示します。

1) スキーマ初期化（DuckDB）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# 設定で指定されたパスに DB を作成・テーブル作成
conn = init_schema(settings.duckdb_path)
```

2) J-Quants からデータを取得して保存（単発）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
import duckdb

# connection は init_schema で作成したものを使う
conn = duckdb.connect(str(settings.duckdb_path))

# ID トークンは settings から自動取得され、期限切れ時に自動リフレッシュされる
records = jq.fetch_daily_quotes(code="7203", date_from=None, date_to=None)
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

3) 日次 ETL（差分更新 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)
print(result.to_dict())
```

ETL の戻り値は ETLResult オブジェクトで、各種取得数や品質問題（QualityIssue のリスト）、エラーメッセージ等を含みます。

4) 監査ログ（発注～約定トレーサビリティ）初期化
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)   # 既存の DuckDB 接続に監査テーブルを追加
# または別 DB を使う場合:
# from kabusys.data.audit import init_audit_db
# audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 重要な設計上の注意点（運用メモ）

- J-Quants API のレートリミットは 120 req/min。内部で固定間隔スロットリングを実装しているため、同一プロセスからの連続呼び出しではこれを超えないよう制御されます。
- ネットワークエラーや 429/408/5xx でリトライ（指数バックオフ、最大 3 回）。401 受信時はリフレッシュトークンで自動的に ID トークンを更新して再試行します（ただし無限再帰防止あり）。
- データ保存は冪等（ON CONFLICT DO UPDATE）で実装しているため再実行でも安全に上書きされます。
- 取得したデータは fetched_at（UTC）でトレースされます。監査ログの TIMESTAMP も UTC で保存される方針です。
- ETL は Fail-Fast ではなく、各ステップでエラーを捕捉して処理を継続し、結果オブジェクトに問題を集約します。呼び出し側で停止や通知の判断を行ってください。

---

## ディレクトリ構成

（パッケージの主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py                 # パッケージエントリ（version 等）
    - config.py                   # 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py         # J-Quants API クライアント（取得 / 保存ロジック）
      - schema.py                 # DuckDB スキーマ定義・初期化関数
      - pipeline.py               # ETL パイプライン（差分取得・保存・品質チェック）
      - audit.py                  # 監査ログ（発注→約定トレース）DDL と初期化
      - quality.py                # データ品質チェック
    - strategy/
      - __init__.py               # 戦略関連（未実装ファイル群のエントリ）
    - execution/
      - __init__.py               # 発注・実行関係（未実装ファイル群のエントリ）
    - monitoring/
      - __init__.py               # 監視・メトリクス（将来実装予定）

ファイル単位の役割（要約）
- config.py: .env の自動ロード、必須設定の取得、環境（development/paper_trading/live）判定、ログレベルチェック。
- data/jquants_client.py: API 呼び出し、ページング、トークン管理、取得データの DuckDB への保存関数。
- data/schema.py: Raw → Processed → Feature → Execution のテーブル定義と初期化（init_schema）。
- data/pipeline.py: 差分計算、バックフィル、市場カレンダー先読み、品質チェックを含む ETL の上位関数（run_daily_etl）。
- data/quality.py: 各種品質チェック（欠損・スパイク・重複・日付整合性）の実装。
- data/audit.py: 発注～約定の監査テーブル定義と初期化（init_audit_schema / init_audit_db）。

---

## 開発・運用上のヒント

- テスト時は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して .env の自動読み込みを無効化できます。
- DuckDB のインメモリを使う場合は `db_path=":memory:"` を渡すことで一時 DB を利用できます（CI のユニットテスト等で有用）。
- 品質チェックの閾値（スパイク閾値など）は pipeline.run_daily_etl の引数から調整可能です。
- 監査ログは削除しない想定で設計されています。FK は ON DELETE RESTRICT としており、発注履歴の完全性を担保します。

---

もし README に含めたいサンプルの .env.example、CI 用の起動コマンド、あるいは具体的な戦略実装のテンプレート等があれば、追加で記載します。