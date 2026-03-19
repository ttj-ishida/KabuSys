# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群。データ収集（J-Quants）→ETL→特徴量生成→シグナル生成→発注／監視までのデータ基盤および戦略ロジック（実行層とは分離）を提供します。

主な設計方針：
- ルックアヘッドバイアス対策（各処理は target_date 時点までの情報のみを使用）
- 冪等性（DB への挿入は ON CONFLICT 等で安全）
- DuckDB によるローカルデータレイヤ（Raw / Processed / Feature / Execution）
- テスト容易性を考慮したトークン注入・自動 env 読込制御

---

## 機能一覧

- データ取得（J-Quants API クライアント）
  - 株価日足（OHLCV）、財務データ、JPX カレンダーのページネーション対応取得
  - レート制限管理、リトライ、トークン自動リフレッシュ
- DuckDB スキーマ定義と初期化（init_schema）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ、features テーブルへの保存）
- シグナル生成（特徴量 + AI スコア統合 → BUY/SELL シグナル生成）
- ニュース収集（RSS フィード、URL 正規化、SSRF 対策、raw_news 保存・銘柄紐付け）
- マーケットカレンダー管理（営業日判定、前後営業日取得、夜間カレンダー更新ジョブ）
- 監査ログ（signal_events / order_requests / executions 等の監査テーブル設計）

---

## 前提 / 要件

- Python 3.10 以上（型注記に | を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード等）
- 環境変数（下記参照）

---

## 環境変数

自動でプロジェクトルート（.git または pyproject.toml）を探索し、`.env` / `.env.local` を読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注層を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルト:
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト `development`）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト `INFO`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — monitoring 用 SQLite（デフォルト `data/monitoring.db`）

サンプル `.env`（プロジェクトルート）:
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

## セットアップ手順（開発用）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存インストール
   - 例: pip
     ```
     pip install duckdb defusedxml
     ```
   - パッケージ化されている場合:
     ```
     pip install -e .
     ```

4. `.env` を作成して必要な環境変数を設定

---

## 初期化（DuckDB スキーマ）

DuckDB ファイルを初期化してスキーマを作成します。Python REPL やスクリプトから:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# ":memory:" を渡せばインメモリ DB になります（テスト用）
```

既存の DB に接続するだけなら:
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

---

## 基本的な使い方（主要ワークフロー例）

以下は代表的な日次バッチの流れです。

1) 日次 ETL を実行してデータを取得・保存・品質チェック:

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量（features）を作成:

```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

3) シグナル生成:

```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
num_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {num_signals}")
```

4) ニュース収集ジョブ（RSS）:

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

5) カレンダー更新ジョブ（夜間バッチ）:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print(f"calendar saved: {saved}")
```

---

## 追加のユーティリティ / 注意点

- settings（kabusys.config.settings）を通して環境設定を参照できます。
- K-Quants API の呼び出しは内部でレートリミット・リトライを行います。トークンが 401 で無効になった場合、自動でリフレッシュを試みます（設定された JQUANTS_REFRESH_TOKEN が必要）。
- news_collector は SSRF 対策（ホストチェック、リダイレクト検査）と XML 攻撃対策（defusedxml）を組み込んでいます。
- ETL / DB 操作はトランザクションを利用して原子性を担保しています。異常時は ROLLBACK が試みられます。
- テスト実行時などで自動 .env 読込を無効にしたい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント + 保存ロジック
    - news_collector.py          — RSS ニュース取得・保存
    - schema.py                  — DuckDB スキーマ定義・初期化
    - stats.py                   — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py     — マーケットカレンダー管理
    - features.py                — data.stats の再エクスポート
    - audit.py                   — 監査ログ用 DDL（signal_events 等）
    - (その他)
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（mom/vol/value 等）
    - feature_exploration.py     — IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py     — features テーブル作成（正規化・ユニバースフィルタ）
    - signal_generator.py        — final_score 計算・BUY/SELL 判定
  - execution/                    — 発注・監視のインターフェース（空パッケージ）
  - monitoring/                   — 監視用ユーティリティ（存在想定）
- pyproject.toml or setup.cfg（プロジェクトルートに配置されている想定）
- .env, .env.local（プロジェクトルート: 環境変数定義）

---

## 開発上のヒント

- DuckDB のインメモリ接続（":memory:"）を使えば単体関数のユニットテストが容易です。
- J-Quants API を使った統合テストでは、get_id_token や _request の挙動をモックしてトークン注入を行うと良いです。
- news_collector._urlopen や jquants_client._request はテスト用にモックしやすい設計になっています。
- 設定ファイル（.env）に機密情報を保存する際はアクセス制御に注意してください。

---

## ライセンス / 貢献

この README はコードベースの説明用です。実際のライセンスやコントリビューションガイドについてはリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください。

---

README に不足している点や、実行スクリプト（CLI）や CI 設定の追加など要望があれば教えてください。必要に応じてサンプルスクリプトや .env.example を作成します。