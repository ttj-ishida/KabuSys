# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
主にデータ収集（J-Quants）、DuckDB ベースのデータスキーマと ETL、ニュース収集、ファクター計算（リサーチ用）、監査ログ（発注トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダーの取得と DuckDB への保存（冪等）
- RSS を用いたニュース収集と銘柄紐付け（SSRF/サイズ上限等の安全対策あり）
- DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）の定義と初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用ファクター（Momentum / Value / Volatility 等）と評価ツール（前方リターン、IC、統計サマリ）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計方針として「本番取引 API へは無闇にアクセスしない」「DuckDB を中心とした冪等処理」「外部依存は最小限（データ処理は標準ライブラリ + DuckDB）」を採用しています。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ、ページネーション）
  - fetch/save: 株価日足、財務データ、マーケットカレンダー
- data/schema
  - DuckDB のスキーマ定義と init_schema()
- data/pipeline
  - 日次 ETL（差分取得・バックフィル・品質チェック）
  - run_daily_etl()
- data/news_collector
  - RSS 取得・前処理・raw_news 保存・銘柄抽出と紐付け
  - SSRF/サイズ対策、gzip 解凍対応
- data/calendar_management
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
- data/quality
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats: zscore_normalize
- audit
  - 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ

---

## 要件 / 依存パッケージ

- Python 3.10+
- 必須ライブラリ
  - duckdb
  - defusedxml
- ほか（運用によって必要）
  - requests 等（現状は標準 urllib を使用しているため必須ではありません）
  - kabu API を呼ぶモジュール（発注機能を追加する場合）
  - Slack 等の通知連携ライブラリ（必要なら追加）

インストール例:

pip を使う最低限の例:
```bash
python -m pip install "duckdb" "defusedxml"
```

開発パッケージがあれば requirements.txt を用意して同様にインストールしてください。

---

## 環境変数（設定）

`kabusys.config.Settings` は環境変数から各種設定を取得します。主なキー:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須)
- kabu ステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベース
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- システム
  - KABUSYS_ENV (development / paper_trading / live、デフォルト: development)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)
- 自動 .env ロード無効化
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、config モジュールによる .env / .env.local 自動読込を無効化できます。

プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（上書きルール: OS環境 > .env.local > .env）。

---

## セットアップ手順

1. Python 環境を作成
   - python >= 3.10 を有効にしてください（venv 等を推奨）。

2. 必要パッケージをインストール
   - duckdb と defusedxml をインストール:
     pip install duckdb defusedxml

3. 環境変数を設定
   - .env または環境変数で必須キー (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID) を設定してください。

4. DuckDB スキーマ初期化
   - 初回はスキーマを作成する必要があります。Python REPL やスクリプトで init_schema を実行します。

例: スキーマ初期化（Python スクリプト）
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# 必要なら監査ログも初期化
from kabusys.data import audit
audit.init_audit_schema(conn, transactional=True)
```

5. （任意）監査用 DB を別ファイルで初期化する:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主な例）

以下はよく使うユーティリティの簡単な利用例です。

- 設定値を参照する:
```python
from kabusys.config import settings
print(settings.duckdb_path)           # Path オブジェクト
print(settings.jquants_refresh_token) # 必要なトークン
```

- DuckDB スキーマ初期化（再掲）:
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")  # テスト用にインメモリ DB
```

- 日次 ETL 実行:
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集（RSS）を実行して保存:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードセット（例: {"7203", "6758", ...}）
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)
```

- J-Quants から日足を直接取得:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from datetime import date
token = get_id_token()  # settings から refresh token を使って idToken を取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 研究用ファクター計算（例: モメンタム）:
```python
from kabusys.research import calc_momentum
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2024,2,1))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

- 前方リターン / IC 計算:
```python
from kabusys.research import calc_forward_returns, calc_ic
fwd = calc_forward_returns(conn, date(2024,2,1), horizons=[1,5])
# factor_records は calc_momentum 等の出力
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- 市場カレンダー更新ジョブ（夜間バッチ）:
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
```

---

## ディレクトリ構成

主要なソースファイル・モジュール配置（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント + 保存関数
    - news_collector.py       # RSS 取得・保存・銘柄抽出
    - schema.py               # DuckDB スキーマ定義と init_schema
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - quality.py              # データ品質チェック
    - stats.py                # zscore_normalize 等
    - calendar_management.py  # カレンダー管理（is_trading_day 等）
    - audit.py                # 監査ログ初期化
    - features.py             # features インターフェース
    - etl.py                  # ETLResult 再エクスポート
  - research/
    - __init__.py
    - feature_exploration.py  # calc_forward_returns / calc_ic / factor_summary
    - factor_research.py      # calc_momentum / calc_value / calc_volatility
  - strategy/                  # 戦略関連（拡張用）
    - __init__.py
  - execution/                 # 発注 / 実行管理（拡張用）
    - __init__.py
  - monitoring/                # 監視用（拡張用）
    - __init__.py

---

## 運用上の注意 / 開発メモ

- DuckDB を中核に据えた設計なので、性能上のチューニングや VACUUM 的な運用は環境に応じて検討してください。
- J-Quants API のレートリミット（120 req/min）や 401 リフレッシュ、429 Retry-After を考慮した実装になっていますが、長時間の大量取得は運用計画を立ててください。
- news_collector は RSS に対して SSRF 対策や受信サイズ上限を実装しています。外部フィードを追加する際は信頼性と負荷を考慮してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます。
- ログレベルは LOG_LEVEL で制御します。開発時は DEBUG、運用では INFO/ WARNING を推奨します。
- 本リポジトリには実際の発注（証券会社）連携モジュールは含まれていないため、発注機能を組み込む場合は別途ブリッジ実装が必要です（audit / orders スキーマは既に用意済み）。

---

以上が README の概要です。必要であれば次の内容を追加できます:
- 具体的な .env.example のテンプレート
- より詳しい ETL 運用手順（cron / Airflow など）
- テスト・CI のセットアップ例
- サンプルデータを使ったハンズオン手順

どれを追加しましょうか？