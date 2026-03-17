# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、ETL パイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定トレース）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤のための内部ライブラリ群です。主な目的は以下です。

- J-Quants API から株価・財務・カレンダー等の市場データを安全かつ冪等に取得・保存する
- RSS（ニュース）を収集して記事を正規化・保存し、銘柄との紐付けを行う
- DuckDB をデータベースとして用いたスキーマ管理と ETL パイプラインを提供する
- データ品質チェック、マーケットカレンダー判定ロジック、監査ログ（シグナル→発注→約定のトレーサビリティ）を備える
- 発注実行（execution）や戦略（strategy）の拡張ポイントを想定したモジュール構成

設計上のポイント：
- API レート制限、リトライ、トークン自動更新、Look-ahead Bias 防止（fetched_at 記録）
- RSS／XML の安全処理（defusedxml、SSRF 対策、レスポンス上限）
- DuckDB への冪等保存（ON CONFLICT）とトランザクション管理
- 品質チェックは Fail-Fast せず、問題を集めて呼び出し元が判断できるようにする

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（株価日足、財務指標、マーケットカレンダー）
  - レートリミッタ、指数バックオフリトライ、401 時のトークン自動リフレッシュ
  - DuckDB へ冪等に保存する save_* 関数

- data/news_collector.py
  - RSS 取得・テキスト前処理（URL除去・空白正規化）
  - 記事IDは正規化 URL の SHA-256（先頭32文字）
  - SSRF/ローカル接続防止、gzip サイズチェック、defusedxml 使用
  - raw_news / news_symbols への保存（INSERT ... RETURNING、トランザクション）

- data/schema.py / data/audit.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema() / init_audit_schema() による初期化

- data/pipeline.py
  - 差分 ETL（市場カレンダー → 株価 → 財務）と品質チェックを統合した run_daily_etl()
  - run_prices_etl(), run_financials_etl(), run_calendar_etl() 単体実行可能

- data/quality.py
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue オブジェクトで結果を返す）
  - run_all_checks() で一括実行

- data/calendar_management.py
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job() による夜間バッチ更新（J-Quants から差分取得）

- config.py
  - 環境変数管理（.env 自動ロード：.env → .env.local）
  - Settings オブジェクト経由で設定を取得（必須変数は例外を投げる）
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## セットアップ手順

必要な Python バージョンや依存関係はプロジェクト方針に合わせてください。最低限このライブラリを動作させるために必要なパッケージは次のとおりです（例）：

必須パッケージ（一例）
- duckdb
- defusedxml

仮想環境を作成して依存をインストールする例：

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# またはプロジェクトで requirements.txt があれば pip install -r requirements.txt
```

パッケージとしてセットアップ（開発インストール）:

```bash
pip install -e .
```

環境変数（.env）:
プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を配置すると自動読み込みされます。自動読み込みを無効にする場合は環境変数を設定してください:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

重要な環境変数（例）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — デフォルト "http://localhost:18080/kabusapi"
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — デフォルト "data/kabusys.duckdb"
- SQLITE_PATH (任意) — デフォルト "data/monitoring.db"
- KABUSYS_ENV (任意) — {"development", "paper_trading", "live"}（デフォルト development）
- LOG_LEVEL (任意) — {"DEBUG","INFO","WARNING","ERROR","CRITICAL"}

簡易的な .env.example:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は主要機能の使い方のサンプルです。ロギングの設定や例外処理は適宜追加してください。

- DuckDB スキーマ初期化:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルを自動作成して全テーブルを作成
```

- 監査スキーマ初期化（既存接続に追加）:

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）:

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

- 個別 ETL ジョブ:

```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl

fetched, saved = run_prices_etl(conn, target_date=date.today())
```

- カレンダー夜間更新ジョブ:

```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
```

- RSS ニュース収集ジョブ（既知銘柄リストを与えて紐付けまで実行）:

```python
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数, ...}
```

- J-Quants から直接データ取得（テストやユーティリティ用途）:

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

id_token = get_id_token()  # settings から refresh_token を使って取得
records = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 品質チェックの単体実行:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## 設計と注意点（運用/開発者向け）

- 環境変数は優先順位: OS 環境 > .env.local > .env。プロジェクトルートの自動検出を行うため、コードを別の場所から実行しても正しく読み込まれる設計。
- J-Quants API 呼び出しはレート制御（120 req/min）とリトライを備えているため、過剰な同時実行は避けること。
- RSS 取得は SSRF・XML Bomb・大量レスポンス対策を実装しているが、社内運用ではホワイトリストやタイムアウト設定の見直しを推奨。
- DuckDB のスキーマは冪等に作成／更新される。複数プロセスから同時にスキーマ操作する場合は注意（ロックや接続管理）。
- 品質チェックは警告/エラーを返すが、自動停止は行わない。CI/監視やオペレーション側で結果に応じた対応を行うこと。
- audit テーブル群は発注・約定の監査証跡を目的とするため削除しない運用が前提。全 TIMESTAMP は UTC で保存。

---

## ディレクトリ構成

（リポジトリの src/kabusys 以下を中心に記載）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py           — RSS 取得・記事正規化・DB保存・銘柄抽出
    - schema.py                   — DuckDB スキーマ定義と init_schema()
    - pipeline.py                 — ETL パイプライン（差分更新、run_daily_etl）
    - calendar_management.py      — マーケットカレンダー管理・営業日判定
    - audit.py                    — 監査ログ（シグナル・注文・約定のトレーサビリティ）
    - quality.py                  — データ品質チェック（欠損・スパイク等）
  - strategy/
    - __init__.py                 — 戦略置き場（拡張ポイント）
  - execution/
    - __init__.py                 — 発注実行関連（拡張ポイント）
  - monitoring/
    - __init__.py                 — モニタリング用ユーティリティ（拡張）

---

## 開発・拡張ポイント

- strategy/ と execution/ は拡張点として空のパッケージが用意されています。独自戦略やブローカーの実装はここに追加してください。
- ニュースの銘柄抽出は単純に 4 桁数字パターンと known_codes の突合せです。より高度な NER や NLP を導入することも可能です。
- ETL のテストでは Settings の自動 .env ロードを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使えます。

---

## ライセンス・貢献

本 README ではライセンス情報は含めていません。実際のリポジトリには LICENSE ファイルを追加してください。バグ修正や機能追加は Pull Request を歓迎します。貢献前にコーディングスタイルやテスト方針を共有してください。

---

必要であれば README の英語版、例となる .env.example、簡単な運用手順（cron / Airflow でのスケジューリング例）、あるいは各モジュールの API リファレンス（関数一覧と引数説明）を追加で作成します。どれを優先しますか？