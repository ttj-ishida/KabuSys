# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。市場データの取得（J-Quants）、DuckDB ベースのデータスキーマ、ファクター計算・特徴量作成、シグナル生成、ニュース収集、カレンダー管理、ETL パイプラインなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含む Python パッケージです。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution 層）のスキーマ定義と初期化
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量（features）作成、AIスコア統合によるシグナル生成
- RSS ベースのニュース収集および銘柄紐付け
- 日次 ETL パイプライン、カレンダー更新バッチ、監査ログ（発注/約定トレーサビリティ）
- 環境変数に依存する設定管理（.env の自動読み込み機能あり）

設計方針は「ルックアヘッドバイアスを避ける」「冪等性（idempotency）」および「外部 API 呼び出しは抽象化してテストしやすくする」ことを重視しています。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / 環境変数読み込み、自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須設定の検証

- kabusys.data.jquants_client
  - J-Quants からのデータ取得（株価日足、財務、マーケットカレンダー）
  - ページネーション対応、レートリミット管理、リトライ・トークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ（save_*）

- kabusys.data.schema
  - DuckDB 用スキーマ定義・初期化（init_schema）
  - get_connection ユーティリティ

- kabusys.data.pipeline
  - 日次 ETL（run_daily_etl）、差分取得／バックフィル／品質チェック

- kabusys.data.news_collector
  - RSS フィード収集、前処理、raw_news 保存、銘柄抽出・紐付け

- kabusys.data.calendar_management
  - JPX カレンダー管理、営業日判定・前後営業日の取得、calendar_update_job

- kabusys.research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン / IC / 統計サマリー等の研究ユーティリティ

- kabusys.strategy
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals）

- kabusys.data.stats
  - Z スコア正規化など統計ユーティリティ

---

## 前提条件

- Python 3.10 以上
- DuckDB
- defusedxml
- （必要に応じて他の標準パッケージ）

pip でインストールする場合の例（開発環境）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージを開発モードでインストールする場合プロジェクトルートに setup/pyproject があれば：
# pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

---

## 環境変数（必須 / 推奨）

KabuSys は環境変数から設定を読み込みます（プロジェクトルートの `.env` / `.env.local` を自動読み込み、ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

最低限設定が必要な環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション（ブローカーAPI）パスワード（必須、利用する場合）
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン（必須、Slack を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須、Slack を使う場合）

その他（任意・デフォルトあり）:

- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト development）
- LOG_LEVEL — "DEBUG" / "INFO" / ...（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）

例（.env）:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（最小）

1. リポジトリをクローン / 取得
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール（例: duckdb, defusedxml）
4. 必要な環境変数を `.env` に設定（または OS 環境変数）
5. DuckDB スキーマを初期化

例:

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml

# .env を作成（上の例を参考）
# DB 初期化（Python REPL またはスクリプト）
python - <<'PY'
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
print("DB initialized")
conn.close()
PY
```

---

## 使い方（主要な操作例）

以下は最小限の利用フロー例です。実運用ではログ、エラーハンドリング、ジョブスケジューラ等を組み合わせてください。

- DuckDB スキーマ初期化:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" でも可
```

- 日次 ETL の実行（市場カレンダー→株価→財務→品質チェック）:

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量（features）作成:

```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 1))
print(f"features upserted: {n}")
```

- シグナル生成:

```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 1))
print(f"signals written: {count}")
```

- ニュース収集ジョブ実行（既知銘柄セットを渡して紐付け）:

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー更新バッチ:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- 設定自動読み込みを無効化（テスト等）:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
# もしくは .env に設定しない / テストコードでモックする
```

---

## 注意点 / 実装上のヒント

- 自動 .env 読み込みの探索はパッケージファイル位置からプロジェクトルート（.git または pyproject.toml を探索）を決定します。CWD に依存しません。
- settings（kabusys.config.settings）は環境変数を遅延で取得するプロパティ実装で、必須変数が欠けている場合は ValueError を発生させます。
- J-Quants クライアントはレート制限・リトライ・トークン自動リフレッシュ等を備えます。API トークンは JQUANTS_REFRESH_TOKEN（リフレッシュトークン）をセットしてください。
- DuckDB に対する INSERT は冪等性を保つため ON CONFLICT .. DO UPDATE / DO NOTHING を利用しています。
- research モジュールは外部ライブラリ（pandas 等）に依存せず、純粋な SQL + 標準ライブラリ実装です。テストしやすく設計されています。

---

## ディレクトリ構成（抜粋）

以下はコードベースに含まれる主要ファイルの構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - stats.py
      - calendar_management.py
      - audit.py
      - features.py
      - execution/ (発注関連の空パッケージ等)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py

（README のために代表的なファイルのみ列挙しています。実際のリポジトリでは他の補助モジュールやテスト、ドキュメントが含まれる可能性があります。）

---

## 開発 / テスト

- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動的な .env 読み込みを無効化できます（ユニットテスト環境など）。
- 各モジュールは外部 API 依存部分を抽象化しているため、HTTP 呼び出しやネットワークはモックしやすく設計されています。
- DuckDB の ":memory:" を利用するとインメモリ DB で高速に単体テストできます。

---

## 免責 / 最後に

本 README はソースコード（modules）からのリバースドキュメントです。運用前に設定値（API トークンやパスワード）、ログ設定、バックアップ方針、リスク管理ルールを十分に確認してください。質問や追加のドキュメント（API 仕様書、DataSchema.md、StrategyModel.md 等）へのリンクが必要であればお知らせください。