# KabuSys

日本株向けの自動売買／データパイプライン基盤ライブラリ。J-Quants や RSS など外部データソースからデータを取得し、DuckDB に蓄積・品質チェック・監査ログを行うためのモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買やデータプラットフォーム構築を支援するライブラリ群です。主に以下を目的としています。

- J-Quants API から株価（OHLCV）、財務データ、マーケットカレンダーを取得して DuckDB に保存
- RSS フィードからニュースを収集して記事と銘柄紐付けを行う
- データ品質チェック（欠損・重複・スパイク・日付不整合）を実行
- 市場カレンダー管理（営業日判定、next/prev trading day など）
- 監査ログ用スキーマ（シグナル→注文→約定のトレーサビリティ）を提供

設計上のポイント:
- API レート制限やリトライ、トークン自動リフレッシュ対応（J-Quants クライアント）
- DuckDB への保存は冪等（ON CONFLICT）でデータ整合を保持
- RSS の取得では SSRF 対策、XML の安全パース、サイズ制限等を実施

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（トークン取得・自動リフレッシュ・レート制限・リトライ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB へ保存する save_* 関数（冪等）
- data.news_collector
  - RSS フィード取得、前処理、記事ID生成（正規化 URL → SHA-256）、DuckDB へ保存
  - 銘柄コード抽出・news_symbols への紐付け
- data.schema
  - DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - init_schema(), get_connection()
- data.pipeline
  - 日次 ETL 実行 run_daily_etl()（差分取得、backfill、品質チェックの統合）
  - 個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
- data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job()（夜間バッチでカレンダー差分更新）
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks()
- data.audit
  - 監査ログ用スキーマ（signal_events / order_requests / executions）
  - init_audit_schema(), init_audit_db()

その他: 環境設定を管理する config.Settings（.env 自動ロード機能、必須環境変数チェック）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントの union 型や構文に依存）
- Git がある環境（.git または pyproject.toml をプロジェクトルート判定に使用）

1. リポジトリをクローンしてワークディレクトリへ移動
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（例）
   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml

   ※ packaging / setup に requirements ファイルがあればそれに従ってください。最低限 DuckDB と defusedxml が必要です。

4. パッケージを開発モードでインストール（任意）
   python -m pip install -e .

5. 環境変数の設定
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。読み込み順は:
   OS 環境変数 > .env.local > .env

   必須環境変数の例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡易例）

以下は主要な操作例です。Python REPL やスクリプトから関数を呼び出して利用します。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を作成してテーブルを初期化
conn = init_schema("data/kabusys.duckdb")
```

2) 監査ログスキーマを追加（既存の conn を利用）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

または監査専用 DB を初期化:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- run_daily_etl は市場カレンダー→株価→財務→品質チェックの順に実行します。
- id_token を外部で発行して注入することも可能（テスト時など）。

4) RSS ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# sources を省略するとデフォルトの RSS ソースを使用
# known_codes に有効な銘柄コード集合を渡すと記事と銘柄を紐付ける
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

5) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved", saved)
```

6) データ品質チェックだけ実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date.today())
for issue in issues:
    print(issue)
```

---

## 環境変数と設定（config.Settings）

主に以下の環境変数が参照されます（Settings クラス経由）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略可、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (省略可、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

自動読み込みは .git または pyproject.toml をプロジェクトルートの指標として .env / .env.local を探します。プロジェクトルートが見つからない場合は自動読み込みをスキップします。

---

## 実装上の注意点 / 動作設計

- J-Quants クライアントは 120 req/min のレート制限を遵守するため、内部で固定間隔のレートリミッタを使用します。またリトライ（指数バックオフ）と 401 時のトークン自動リフレッシュに対応しています。
- DuckDB への保存は基本的に ON CONFLICT（DO UPDATE / DO NOTHING）で冪等に設計されています。
- RSS 取得は XML の安全パーサ（defusedxml）を使い、SSRF・gzip bomb・大容量レスポンス対策を実装しています。
- カレンダーやトレード関連のヘルパーは market_calendar が存在しない場合に曜日ベースでフォールバックしますが、DB データがあればそれを優先します。
- 品質チェックは Fail-Fast 型ではなく、検出された問題の一覧を返して呼び出し元で対処する方針です。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント + DuckDB 保存
    - news_collector.py            # RSS 収集・前処理・DB保存
    - schema.py                    # DuckDB スキーマ定義・初期化
    - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py       # マーケットカレンダー管理
    - audit.py                     # 監査ログ（signal/order/execution）スキーマ
    - quality.py                   # データ品質チェック
  - strategy/
    - __init__.py                  # 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                  # 発注・約定処理（拡張ポイント）
  - monitoring/
    - __init__.py                  # 監視関連（拡張ポイント）

その他: pyproject.toml 等（プロジェクトルートに存在する想定）

---

## 開発 / 拡張ポイント

- strategy と execution パッケージは拡張ポイントとして空の __init__.py を置いています。独自戦略やブローカー連携はここに実装してください。
- RabbitMQ / Redis / 外部ジョブスケジューラとの連携は、run_daily_etl や calendar_update_job をラップすることで容易に実行可能です。
- Slack 通知や監視のフックは config.Settings でトークンを取得し、event 発火時に呼び出す実装を追加してください。

---

## ライセンス / 貢献

（プロジェクトに合わせてライセンス情報やコントリビュートルールをここに記載してください）

---

不明点や README に追加したい実例・コマンド等があれば教えてください。README を用途（運用者向け / 開発者向け）に合わせてさらに詳細化できます。