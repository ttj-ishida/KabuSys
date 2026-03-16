# KabuSys

日本株自動売買システムのコアライブラリ（データ取得・ETL・品質チェック・監査ログ等）

本リポジトリは、J-Quants API 等から市場データを取得して DuckDB に保存し、戦略／実行層へ渡すための基盤機能群を提供します。  
設計上の主なポイントは、レート制限遵守、リトライ・トークン自動リフレッシュ、ETL の冪等性（ON CONFLICT）、およびデータ品質チェックと監査ログの保持です。

---

## 主要機能

- 環境変数 / .env の自動読み込み（プロジェクトルート検出ベース）
- J-Quants API クライアント（株価日足、財務データ、JPX カレンダー取得）
  - レート制限（120 req/min）を遵守する内部 RateLimiter
  - 401 の際の自動トークンリフレッシュ（1回）と指数バックオフを用いたリトライ
  - 取得時刻（fetched_at）を UTC で記録して look-ahead バイアスを防止
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ用スキーマ（signal → order_request → execution のトレーサビリティ）
- ETL パイプライン（差分取得・バックフィル・保存・品質チェック）
  - 日次 ETL の一括実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  - バックフィルやカレンダー先読みの設定可能
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 各種ユーティリティ（型変換、ID トークンキャッシュなど）

---

## 要求環境 / 依存関係

- Python 3.10+
- duckdb
- （標準ライブラリ：urllib, json, logging, datetime など）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# パッケージをローカル開発モードで使う場合
pip install -e .
```

（実際の setup.py / pyproject.toml はプロジェクトに応じて用意してください）

---

## 環境変数

パッケージはプロジェクトルートの `.env` / `.env.local` を自動読み込みします（優先順: OS 環境変数 > .env.local > .env）。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（少なくともセットする必要がある主要な環境変数）:

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意・デフォルトあり:

- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト `development`
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）。デフォルト `INFO`
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する（値がセットされていれば無効）
- KABUSYS_*（必要に応じて追加）

DB 関連デフォルトパス（環境変数で上書き可能）:

- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する
2. 依存パッケージ（最低 `duckdb`）をインストールする
3. プロジェクトルートに `.env` を用意して環境変数を設定する（上記参照）
4. DuckDB スキーマを初期化する（下記「使い方」を参照）

---

## 使い方（簡単なコード例）

※ 下記はライブラリ API を直接呼ぶ例です。実運用ではジョブスケジューラや CLI ラッパーを作成してください。

- DuckDB スキーマの初期化（ファイル DB）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # Path オブジェクトも可
```

- 日次 ETL を実行してデータ取得・保存・品質チェック
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- 個別 ETL（株価 / 財務 / カレンダー）を手動実行
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
today = date.today()

# 市場カレンダー（先読みなしで当日分など）
run_calendar_etl(conn, today)

# 株価（差分 + バックフィル）
run_prices_etl(conn, today)

# 財務
run_financials_etl(conn, today)
```

- 品質チェックを個別実行
```python
from kabusys.data.quality import run_all_checks
result = run_all_checks(conn, target_date=None)
for issue in result:
    print(issue)
```

- 監査ログ（audit）スキーマを既存の DuckDB に追加
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

---

## 重要な設計・実装上の注意点

- J-Quants API は 120 req/min のレート制限を守るように設計されています（内部 RateLimiter）。
- API 呼び出しは 408/429/5xx を対象に指数バックオフで再試行します。401 を受けた場合は自動でリフレッシュして 1 回リトライします。
- データ保存は冪等（ON CONFLICT DO UPDATE）になっており、同一の (date, code) 等での上書きを許容します。
- ETL は Fail-Fast ではなく、各ステップでエラーを集約して呼び出し元に伝える作りです（ETLResult.errors / quality_issues）。
- 本ライブラリには実際の発注（kabuステーション連携）や実ポジション管理の実装は含まれていません。execution / strategy / monitoring の各モジュールは拡張ポイントとして用意されています。

注意：KABUSYS_ENV を `live` に設定して本番注文を行う場合は十分な安全対策（ドライラン、ポジション・注文ガード、監査、通知）を行ってください。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリの主要なモジュール構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 管理、Settings クラス
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存関数）
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（差分取得、日次 ETL）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ（signal / order_request / executions）
    - pipeline.py
  - strategy/
    - __init__.py            — 戦略層拡張ポイント（未実装部分）
  - execution/
    - __init__.py            — 発注/ブローカー連携拡張ポイント（未実装部分）
  - monitoring/
    - __init__.py            — 監視・メトリクス（拡張ポイント）

主要ファイルの説明:
- config.py: .env のパースロジック、プロジェクトルート探索、自動読み込み、Settings プロパティ群を提供します。
- data/jquants_client.py: API からの取得ロジックと DuckDB への保存関数（save_*）を実装。
- data/schema.py: 全テーブルの DDL を持ち、init_schema() で一括作成します。
- data/pipeline.py: 差分算出、バックフィル、ETL のオーケストレーションを行います。
- data/quality.py: 各種品質チェック（欠損・スパイク・重複・日付不整合）。
- data/audit.py: 監査ログの DDL と初期化ロジック。

---

## 開発 / テスト時のヒント

- 自動 .env ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。
- ID トークンは内部でキャッシュされます。テストで強制的にリフレッシュしたい場合は jquants_client._get_cached_token(force_refresh=True) もしくは get_id_token() を直接呼ぶことができます（非公開 API なのでテスト用途に限定してください）。
- DuckDB をメモリで使う場合は `":memory:"` を init_schema に渡せます。

---

## ライセンス / 貢献

本 README はコードベースに基づく説明書きです。実際のライセンスや貢献ルール（CONTRIBUTING.md）があればそれに従ってください。

---

README は以上です。追加で CLI の雛形、運用手順（cron / airflow などへの組み込み）、あるいは実行ログ/Slack 通知のサンプルが必要であれば教えてください。