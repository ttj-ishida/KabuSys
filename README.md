# KabuSys

日本株向け自動売買 / データ基盤ライブラリ KabuSys のリポジトリ用 README（日本語）

概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、DuckDB を用いたデータスキーマ・ETL、ニュース収集、特徴量計算、監査（発注→約定のトレーサビリティ）などを備えた自動売買／リサーチ用のライブラリ群です。  
設計上のポイント：

- DuckDB をデータレイク／分析 DB として使用（冪等な INSERT、トランザクション管理あり）
- J-Quants API を用いた株価・財務・カレンダー取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- RSS からのニュース収集（SSRF対策、トラッキングパラメータ除去、記事IDは正規化URLのSHA-256）
- リサーチ用にファクター計算（Momentum / Volatility / Value 等）と IC / 統計サマリー
- データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）

---

## 主な機能一覧

- 環境設定管理（.env 自動読み込み、環境変数のラッパー）
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
- J-Quants クライアント（fetch / save の冪等操作、ページネーション、レート制御、リトライ）
- ETL パイプライン（日次 ETL：カレンダー・株価・財務の差分取得・保存）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集（RSS フィードの取得、前処理、DB保存、銘柄抽出）
- 監査ログ（signal_events / order_requests / executions テーブルにより完全トレース）
- リサーチユーティリティ（ファクター計算、forward returns、IC、z-score 正規化 等）

---

## 必要条件（Prerequisites）

- Python 3.9+（型注釈に union 型など使用）
- 必須パッケージ（少なくとも実行に必要なもの）：
  - duckdb
  - defusedxml
- （J-Quants API を利用する場合）J-Quants のリフレッシュトークン
- ネットワークアクセス（J-Quants / RSS フィード）

インストール例（pip）:
```bash
pip install duckdb defusedxml
```

---

## 環境変数 / .env

自動でプロジェクトルート（.git または pyproject.toml を探す）から `.env` と `.env.local` を読み込みます（優先順位: OS 環境 > .env.local > .env）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネルID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ('development' | 'paper_trading' | 'live'), デフォルト 'development'
- LOG_LEVEL — ('DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL'), デフォルト 'INFO'

Settings は `kabusys.config.settings` からアクセスできます。

---

## セットアップ手順（Quickstart）

1. リポジトリをクローン／プロジェクトに追加
2. 必要パッケージをインストール:
   ```bash
   pip install duckdb defusedxml
   ```
3. `.env` をプロジェクトルートに作成し、必要な環境変数を設定
   - 例: `.env`（簡易）
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=zzzz
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     ```
4. DuckDB スキーマの初期化（Python REPL またはスクリプトで実行）:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # デフォルトパスを使う場合
   conn.close()
   ```
5. 監査ログ専用 DB を初期化する（任意）の場合:
   ```python
   from kabusys.data import audit
   conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
   conn_audit.close()
   ```

---

## 使い方（主要な API と例）

ここでは代表的な操作のコード例を示します。詳細は各モジュールの Docstring を参照してください。

- 日次 ETL 実行（市場カレンダー→株価→財務→品質チェック）:
```python
from datetime import date
import duckdb
from kabusys.data import pipeline, schema

# DB 初期化済みの前提
conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- 単体の ETL ジョブ（株価差分）:
```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- カレンダー更新の夜間バッチ:
```python
from kabusys.data import calendar_management, schema
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved={saved}")
```

- ニュース収集ジョブ（RSS → DuckDB）:
```python
from kabusys.data import news_collector, schema
conn = schema.get_connection("data/kabusys.duckdb")
# known_codes を渡すと抽出した銘柄と紐付けます（set of "7203" 等）
res = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
print(res)
```

- J-Quants から日足を取得して保存（テスト的に）:
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,10))
saved = jq.save_daily_quotes(conn, records)
print(saved)
```

- ファクター計算 / リサーチ関数:
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

# 例: mom の mom_1m と fwd_1d の IC
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
conn.close()
```

---

## 主要モジュールと役割（簡易説明）

- kabusys.config — 環境変数 / .env 読み込み、Settings ラッパー
- kabusys.data
  - schema.py — DuckDB スキーマ定義 & init_schema / get_connection
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - pipeline.py — 日次 ETL の Orchestrator（run_daily_etl など）
  - news_collector.py — RSS 取得・前処理・保存・銘柄抽出
  - quality.py — データ品質チェック群
  - calendar_management.py — 市場カレンダー取得／営業日判定ユーティリティ
  - audit.py — 監査ログ（signal / order_request / executions）の定義・初期化
  - stats.py — zscore_normalize 等の統計ユーティリティ
- kabusys.research
  - factor_research.py — Momentum / Volatility / Value の計算
  - feature_exploration.py — forward returns / IC / factor summary / rank
- kabusys.execution, kabusys.strategy, kabusys.monitoring — 発注・ストラテジ・監視に関するパッケージ領域（実装は拡張対象）

---

## ディレクトリ構成

（リポジトリ内の主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - schema.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - audit.py
    - news_collector.py
    - quality.py
    - stats.py
    - features.py
    - calendar_management.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

各モジュールの詳細は各ファイル先頭の Docstring を参照してください（設計方針・入出力仕様が記載されています）。

---

## 注意点 / 実運用に関する補足

- J-Quants API のレート制限（120 req/min）を遵守するため内部でレートリミッタを実装しています。大量フェッチ時は時間がかかります。
- J-Quants の 401 エラーに対する自動トークンリフレッシュや指数バックオフ・リトライを備えていますが、API 側の障害等は運用側でログ監視・アラートを設定してください。
- ニュース収集では SSRF 対策や受信サイズ上限、XML の安全パース (defusedxml) を行っていますが、外部入力の取り扱いには注意してください。
- DuckDB のバージョン差異により一部機能（ON DELETE CASCADE 等）が制約されている箇所があります（コード内コメント参照）。

---

## 開発・貢献

- コーディング規約、テスト、CI 等はプロジェクトの方針に従ってください。  
- テスト時に自動 .env 読み込みを抑えたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して下さい。

---

以上がこのコードベースの README です。必要であれば「使い方」のスニペットを脚本化した CLI 例や、より詳細な環境変数のサンプル `.env.example` を追加できます。どの情報を追加したいか教えてください。