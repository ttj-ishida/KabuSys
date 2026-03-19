# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（KabuSys）。  
DuckDB を用いたデータ層、J-Quants API 経由のデータ取得、ニュース収集、品質チェック、ファクター計算（リサーチ用）などを含むモジュール群を提供します。

---

## 概要

KabuSys は以下を主目的とした内部ライブラリです。

- J-Quants API からの株価・財務・マーケットカレンダー取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集とテキスト前処理、銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター（Momentum / Value / Volatility）計算と研究用ユーティリティ
- DuckDB 上に定義されたスキーマ（Raw / Processed / Feature / Execution / Audit）
- 発注・監査ログ（Audit）テーブルの初期化ユーティリティ

設計方針として、本ライブラリは以下を重視しています。

- DuckDB を中心とした冪等的データ永続化（ON CONFLICT を利用）
- Look-ahead bias 回避のため取得時刻（fetched_at）を記録
- 外部ライブラリへの依存を必要最小限に（ただし DuckDB / defusedxml 等は使用）
- テストしやすいようトークン注入や自動ロード無効化オプションを用意

---

## 主な機能一覧

- 環境設定管理
  - .env 自動ロード（プロジェクトルート検出）、必須環境変数取得 API（kabusys.config.settings）
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- データ取得（J-Quants クライアント）
  - 株価日足、財務データ、マーケットカレンダーのページネーション対応取得
  - レート制限管理・リトライ（指数バックオフ）・トークン自動リフレッシュ
  - DuckDB への冪等保存（save_* 関数）

- ETL パイプライン
  - 差分更新、バックフィル、品質チェックを組み合わせた日次 ETL（run_daily_etl）
  - 個別 ETL（株価 / 財務 / カレンダー）も提供

- データスキーマ管理
  - DuckDB 用スキーマ定義と初期化（init_schema）
  - Audit 用スキーマ（init_audit_schema / init_audit_db）

- ニュース収集
  - RSS 取得（SSRF 対策、gzip サイズ制限、XML 脆弱性対策）
  - URL 正規化、ID 生成（SHA-256）、テキスト前処理、銘柄抽出、DB 保存（save_raw_news, save_news_symbols）

- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出（run_all_checks）

- 研究用ユーティリティ（research）
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算・IC（Information Coefficient）計算（calc_forward_returns, calc_ic）
  - Zスコア正規化ユーティリティ（zscore_normalize）

---

## 必要条件

- Python 3.10 以上（| 型等の構文を利用しているため）
- 推奨パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトに requirements.txt がある場合はそちらに従ってください）

インストール例（仮）:
```
python -m pip install "duckdb" "defusedxml"
# またはプロジェクトに合わせて pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを入手

2. Python 仮想環境を作成・有効化（任意）
```
python -m venv .venv
source .venv/bin/activate    # Unix / macOS
.venv\Scripts\activate       # Windows
```

3. 依存パッケージをインストール
```
pip install duckdb defusedxml
# その他プロジェクト依存があれば追加でインストール
```

4. 環境変数の設定（.env）
- ルートに `.env` または `.env.local` を置くと自動読み込みされます（kabusys.config がプロジェクトルートを検出した場合）。
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード（発注周りで使用）
  - SLACK_BOT_TOKEN — Slack 通知用トークン
  - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- 任意 / デフォルト:
  - KABUSYS_ENV — development / paper_trading / live（default: development）
  - LOG_LEVEL — DEBUG/INFO/...
  - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（default: data/monitoring.db）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

5. DuckDB スキーマ初期化
Python REPL またはスクリプトから:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

監査ログ用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（代表的な例）

- 日次 ETL 実行（市場カレンダー / 株価 / 財務 / 品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集ジョブ実行
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コード
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

- J-Quants から日足を取得して保存（内部はページネーション対応）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")
records = fetch_daily_quotes(date_from=None, date_to=None)  # 引数を指定して絞る
saved = save_daily_quotes(conn, records)
```

- 研究用のファクター計算
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
today = date(2025, 1, 31)
mom = calc_momentum(conn, today)
vol = calc_volatility(conn, today)
val = calc_value(conn, today)
```

- 設定参照（環境変数経由）
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

注意:
- 環境変数が不足していると settings の必須プロパティは ValueError を投げます。
- 自動 .env 読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys/）

- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（取得 & 保存）
  - news_collector.py       — RSS ニュース収集と DB 保存
  - schema.py               — DuckDB スキーマ定義と init_schema
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - features.py             — 特徴量ユーティリティ（再エクスポート）
  - calendar_management.py  — マーケットカレンダー管理（is_trading_day 等）
  - quality.py              — データ品質チェック
  - stats.py                — 統計ユーティリティ（zscore_normalize）
  - audit.py                — 監査ログ（order/signals/executions テーブル）
  - etl.py                  — ETL 用公開型（ETLResult 再エクスポート）
- research/
  - __init__.py
  - feature_exploration.py  — 将来リターン / IC / summary
  - factor_research.py      — Momentum/Value/Volatility 計算
- strategy/
  - __init__.py
  - (戦略モデルやポートフォリオ最適化はここに実装想定)
- execution/
  - __init__.py
  - (発注・証券会社インターフェース想定)
- monitoring/
  - __init__.py

---

## 実運用上の注意点

- DuckDB のファイルパス権限やバックアップを考慮してください。デフォルトは `data/kabusys.duckdb`。
- J-Quants API のレート制限（120 req/min）に配慮して実行頻度を設定してください。クライアントは内部でスロットリングを行います。
- ETL の差分戦略（backfill）や品質チェックポリシーは運用状況に合わせてパラメータを調整してください。
- Audit テーブル初期化時にタイムゾーンを UTC に固定します。アプリケーションで日時管理を統一してください。
- news_collector は外部 HTTP を多数叩くため SSRF / XML 脆弱性等の対策を施していますが、追加のネットワーク制限（プロキシ / FW）も検討してください。

---

README は必要に応じてプロジェクトの README.md に貼り付け、実際の運用手順や CI/CD、テスト手順、依存ファイル（requirements.txt / pyproject.toml）を追記してください。質問や追加したいセクションがあれば教えてください。