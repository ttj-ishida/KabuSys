# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
J-Quants API から市場データを取得して DuckDB に格納し、データ品質チェックや監査ログ、ETL パイプラインを提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした小型のフレームワーク／ライブラリです。

- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを取得
- DuckDB に対するスキーマ定義・初期化・差分 ETL（冪等保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ
- レート制限／リトライ／トークン自動リフレッシュなどの堅牢な HTTP クライアント

設計上のポイント：
- API レート制限遵守（120 req/min）と指数バックオフリトライ
- 取得時刻（fetched_at）による Look-ahead Bias 対策
- DuckDB への保存は ON CONFLICT DO UPDATE による冪等化

---

## 機能一覧

- データ取得
  - 日足株価（OHLCV）の取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）の取得
  - JPX マーケットカレンダー取得
- データ保存（DuckDB）
  - raw / processed / feature / execution 層のテーブル定義と初期化
  - 冪等的な保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得）
  - バックフィル（後出し修正を吸収するための再取得）
  - 品質チェック実行（複数チェックを収集）
- データ品質チェック
  - 欠損（OHLC 欠損）検出
  - スパイク（前日比閾値）検出
  - 重複（主キー重複）検出
  - 日付不整合（未来日付・非営業日のデータ）検出
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルとインデックス
  - 発注系の冪等キー（order_request_id）サポート

---

## 必要条件

- Python 3.10 以上（| 型注釈、match などを使った構文に依存）
- 依存ライブラリ
  - duckdb

（HTTP クライアントは標準ライブラリの urllib を使用しているため追加の外部 HTTP ライブラリは必須ではありません）

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得
2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate
3. 依存パッケージをインストール
   - pip install duckdb
   - （パッケージ化されている場合）pip install -e .

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` を置くと自動で読み込まれます。
   - テスト等で自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 環境変数一覧

KabuSys は Settings クラスを通じて環境変数を参照します。主要なキーは以下の通りです。

必須（未設定時は ValueError）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注機能等で使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化（1 を設定）

.env の読み込み順序:
- OS 環境変数 ＞ .env.local ＞ .env
- プロジェクトルートが検出できない場合、自動ロードをスキップします

---

## 使い方（簡単なコード例）

以下は主要な利用例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN）を設定してください。

1) DuckDB スキーマ初期化

- 全スキーマ（raw / processed / feature / execution）を作成して接続を得る：

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルがなければ自動でディレクトリ作成
```

- 監査ログ（audit）テーブルを既存接続に追加する：

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

または監査専用 DB を初期化：

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

2) J-Quants の認証トークン取得

```python
from kabusys.data import jquants_client as jq

id_token = jq.get_id_token()  # settings.jquants_refresh_token を使って POST で idToken を取得
```

3) 日次 ETL 実行（最も簡単な呼び出し）

```python
from kabusys.data.pipeline import run_daily_etl
# init_schema で得た conn を渡す
result = run_daily_etl(conn)
print(result.to_dict())
```

run_daily_etl は以下を順に実行します：
- 市場カレンダー ETL（先読み）
- 株価日足 ETL（差分 + backfill）
- 財務データ ETL（差分 + backfill）
- 品質チェック（デフォルトで実行）

オプション例（品質チェックをスキップ、または独自の id_token を渡す）：

```python
result = run_daily_etl(
    conn,
    id_token="自前の id_token",
    run_quality_checks=False,
    backfill_days=5,
)
```

4) 個別ジョブの実行

- 株価差分 ETL（特定日を指定）:

```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl

fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 1))
```

- 財務データ ETL / カレンダー ETL も同様に run_financials_etl / run_calendar_etl を利用可能。

5) 品質チェックを直接実行

```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

---

## 注意事項 / 運用メモ

- API レート制限はモジュール内の RateLimiter（120 req/min）で保護されていますが、大量並列呼び出しを行う場合は呼び出し間隔・並列数にも注意してください。
- get_id_token は 401 を受け取った場合に自動でリフレッシュし、1 回だけ再試行します。
- DuckDB の INSERT は ON CONFLICT DO UPDATE を用いて冪等性を保っています。ただし外部から直接テーブルを操作すると一貫性が損なわれる可能性があります。
- KABUSYS_ENV を `live` にすると実際の発注処理等を有効にする想定です（発注実装はこのコードベースの範囲を超える場合があります）。本番稼働前に `paper_trading` で十分な検証を行ってください。

---

## ディレクトリ構成（リポジトリ内の主要ファイル）

- src/kabusys/
  - __init__.py              — パッケージ定義（version）
  - config.py                — 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 / 保存ロジック）
    - schema.py              — DuckDB のスキーマ定義 & 初期化
    - pipeline.py            — ETL パイプライン（差分更新・品質チェック等）
    - audit.py               — 監査ログ用スキーマ（signal/order_request/execution）
    - quality.py             — データ品質チェック（欠損/スパイク/重複/日付不整合）
  - strategy/
    - __init__.py            — 戦略層（プレースホルダ）
  - execution/
    - __init__.py            — 発注 / 実行層（プレースホルダ）
  - monitoring/
    - __init__.py            — 監視用モジュール（プレースホルダ）

---

## 追加情報 / 今後の拡張点

- 発注周り（kabu API）やポジション管理ロジックの実装（execution パッケージ）
- Slack や監視システムへの通知機能（monitoring）
- ETL のスケジューリング（Airflow / cron などとの連携）
- 単体テストや CI の追加（KABUSYS_DISABLE_AUTO_ENV_LOAD を活用）

---

README に関する補足・修正の依頼や、使用例（実際にどのようにジョブを運用するか）をもっと詳しく載せたい場合は、お知らせください。