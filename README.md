# KabuSys

日本株自動売買システムのモジュール群（ライブラリ）。データ収集（J‑Quants）、DuckDBスキーマ管理、ETLパイプライン、ニュース収集、ファクター計算、品質チェック、監査ログ等の基盤機能を提供します。

---

## 概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。主な目的は以下のとおりです。

- J‑Quants API からの市場データ取得と DuckDB への冪等保存
- 市場カレンダー管理、差分 ETL（バックフィル対応）、データ品質チェック
- RSS によるニュース収集と銘柄抽出
- ファクター（Momentum / Value / Volatility など）計算、IC/統計解析ユーティリティ
- 発注/監査データ構造（スキーマ）と監査ログ初期化
- 設定は環境変数（.env）で管理し、自動ロード対応

ライブラリは「データレイヤ（Raw / Processed / Feature）」および「実行（Execution）」「監査（Audit）」のスキーマを備え、研究・戦略開発から運用までの基盤を提供します。

---

## 主な機能一覧

- data/jquants_client
  - J‑Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ、ページネーション対応）
  - fetch/save 系関数（株価、財務、マーケットカレンダー）
- data/schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）と初期化関数
- data/pipeline
  - 日次差分ETL（run_daily_etl）・個別ETL（prices, financials, calendar）
  - バックフィル・品質チェック連携
- data/news_collector
  - RSS 取得・前処理・raw_news への冪等保存、銘柄抽出・紐付け
  - SSRF / XML Bomb / レスポンスサイズ制限等の安全対策
- data/quality
  - 欠損、スパイク、重複、日付不整合などの品質チェック（QualityIssue を返却）
- research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、統計サマリー（factor_summary）
  - data.stats の zscore_normalize をエクスポート
- audit
  - 監査ログ用スキーマと初期化（signal_events, order_requests, executions 等）
- config
  - .env / 環境変数読み込み、必須キーチェック、環境/ログレベルフラグ

---

## 動作要件（想定）

- Python 3.10+
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml

（必要に応じて pyproject.toml / requirements.txt を用意して pip install してください）

---

## インストール（開発環境）

リポジトリルートに `pyproject.toml` や setup の定義がある前提でローカルインストール例：

```bash
# 仮想環境作成（推奨）
python -m venv .venv
source .venv/bin/activate

# パッケージのインストール（プロジェクトを編集して使う場合）
pip install -e .
# 依存の追加インストール（例）
pip install duckdb defusedxml
```

---

## 設定（環境変数 / .env）

KabuSys は環境変数を使用して設定を管理します。プロジェクトルートの `.env` / `.env.local` を自動で読み込みます（優先順位: OS 環境 > .env.local > .env）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（Settings で参照されるキー）:

- JQUANTS_REFRESH_TOKEN — 必須（J‑Quants のリフレッシュトークン）
- KABU_API_PASSWORD — 必須（kabu ステーション API パスワード）
- KABU_API_BASE_URL — 省略可（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — 必須（Slack 通知用）
- SLACK_CHANNEL_ID — 必須（Slack 通知先チャネル）
- DUCKDB_PATH — 省略可（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 省略可（デフォルト: data/monitoring.db）
- KABUSYS_ENV — (development|paper_trading|live)、デフォルト development
- LOG_LEVEL — (DEBUG|INFO|WARNING|ERROR|CRITICAL)、デフォルト INFO

例（.env）:

```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

未設定の必須キーにアクセスすると Settings が ValueError を発生させます。

---

## セットアップ手順（DB 初期化など）

1. DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema

# ファイル DB を作成してスキーマを初期化
conn = init_schema("data/kabusys.duckdb")

# ':memory:' を渡すとインメモリ DB
# conn = init_schema(":memory:")
```

2. 監査ログスキーマ（必要な場合）

```python
from kabusys.data.audit import init_audit_schema, init_audit_db
# 既存 connection に追加
init_audit_schema(conn)
# あるいは監査専用 DB を初期化
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要ユースケース）

以下は代表的な利用例です。

- 日次 ETL（市場カレンダー・株価・財務の差分取得と品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- News（RSS）収集と保存

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# known_codes があれば銘柄抽出して news_symbols に紐付けする
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄セット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- J‑Quants からのデータ取得（低レベル）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

# id_token を明示提供するかモジュールキャッシュを利用
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(records))
```

- 研究用ファクター計算（DuckDB 接続を渡して利用）

```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
target = date(2024, 3, 1)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# 結果を zscore 正規化
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- 将来リターン・IC 計算

```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=target, horizons=[1,5,21])
# factor_records は例えば calc_momentum の結果
ic = calc_ic(factor_records=mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

---

## 主要 API の概要

- kabusys.config.settings: 環境変数から設定を取得
- kabusys.data.schema.init_schema(db_path): DuckDB スキーマを作成して接続を返す
- kabusys.data.jquants_client.fetch_* / save_*: データ取得・DB保存の低レベル関数
- kabusys.data.pipeline.run_daily_etl: 日次 ETL の一括実行（品質チェック含む）
- kabusys.data.news_collector.run_news_collection: RSS 収集 -> raw_news 保存 -> news_symbols 紐付け
- kabusys.data.quality.run_all_checks: 品質チェックのラッパー
- kabusys.research.*: ファクター計算・解析ユーティリティ

---

## ディレクトリ構成

主要ファイル・モジュールは以下の階層です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                        # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py               # J‑Quants API クライアント（取得・保存）
    - news_collector.py               # RSS 収集・保存・銘柄抽出
    - schema.py                       # DuckDB スキーマ定義・初期化
    - pipeline.py                     # ETL パイプライン（run_daily_etl 等）
    - features.py                     # 特徴量ユーティリティの公開
    - stats.py                        # 正規化・統計ユーティリティ
    - calendar_management.py          # 市場カレンダー管理
    - audit.py                         # 監査ログスキーマ初期化
    - etl.py                           # ETL 型などの公開（簡易）
    - quality.py                      # データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py          # forward returns, IC, summary
    - factor_research.py              # momentum / value / volatility 計算
  - strategy/
    - __init__.py                     # 戦略関連のエントリ（将来拡張）
  - execution/
    - __init__.py                     # 発注実行関連（将来拡張）
  - monitoring/
    - __init__.py                     # 監視・メトリクス（将来拡張）

---

## 開発・運用上の注意

- J‑Quants API のレート制限（120 req/min）やエラー応答（429/408/5xx）に対する処理を実装済みですが、運用時はさらに監視やバックオフポリシーの調整を行ってください。
- DuckDB のバージョン差異により一部の外部キー/ON DELETE オプションがサポートされないため、設計上の注記が各DDLに含まれています。運用手順で削除順序を守ってください。
- news_collector は外部 RSS を取得します。SSRF 対策や XML パース対策、レスポンスサイズ制限を実装していますが、信頼できる RSS のみをソースに追加することを推奨します。
- 設定値・シークレット（トークン等）は安全に管理してください。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用して自動読み込みを抑止できます。

---

## 貢献・拡張

- strategy / execution / monitoring モジュールは将来的な拡張ポイントです。戦略モデルや実取引ロジック、監視・アラートの追加はここに実装してください。
- 単体テスト・統合テストの追加、CI の導入、ドキュメントの充実を歓迎します。

---

以上がプロジェクト概要と基本的な使い方です。必要に応じて README にサンプルスクリプトや CLI、Docker 化手順、詳しい env.example を追加できます。必要なら追記しますので教えてください。