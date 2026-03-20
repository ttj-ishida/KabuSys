# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。  
データ収集（J-Quants / RSS）、DuckDB ベースのスキーマ管理、ファクター計算・特徴量生成、シグナル生成、ETL パイプライン、ニュース収集、マーケットカレンダー管理、監査ログなどを含むモジュール群を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムの基盤コンポーネント群です。主な目的は次の通りです。

- J-Quants API からの市場データ・財務データ取得（ページネーション／リトライ／レート制御対応）
- RSS フィードからのニュース収集と銘柄紐付け
- DuckDB を使った階層化されたデータスキーマ（Raw / Processed / Feature / Execution）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量（features）構築と正規化（Z スコア）
- シグナル生成（戦略の重み付け、Bear レジーム抑制、エグジット判定）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（signal → order → execution のトレース）

設計は「ルックアヘッドバイアスの排除」「冪等性」「外部 API のレート制御」「テスト可能性」を重視しています。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API から株価・財務・カレンダー取得（リトライ、トークン自動リフレッシュ、レート制御）
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
- data/news_collector
  - RSS フィード取得、XML の安全パース（defusedxml）、トラッキングパラメータ削除、記事の正規化、raw_news 保存、銘柄抽出と紐付け
- data/schema
  - DuckDB のスキーマ定義と初期化（init_schema）
  - get_connection（既存 DB への接続）
- data/pipeline
  - 日次 ETL（run_daily_etl）、株価/財務/カレンダーの差分取得・保存
- data/calendar_management
  - 営業日判定、next/prev_trading_day、カレンダーの夜間更新ジョブ
- data/stats
  - zscore_normalize（クロスセクション Z スコア正規化）
- research
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic（Spearman）、factor_summary
- strategy
  - feature_engineering: build_features（ファクター合成・ユニバースフィルタ・正規化・features 保存）
  - signal_generator: generate_signals（最終スコア計算、BUY/SELL シグナル生成、signals テーブルへの保存）
- config
  - .env / 環境変数の自動読み込み、Settings クラスによる設定アクセス（トークン・DB パス・Slack 等）
- audit / execution / monitoring
  - 監査ログ・発注関連スキーマ（監査テーブルの DDL が定義されています）

---

## セットアップ手順

必要条件（推奨）
- Python 3.10+
- pip
- DuckDB（Python パッケージ duckdb）
- defusedxml

例: 仮想環境作成と依存インストール

```bash
git clone <リポジトリ>
cd <リポジトリ>
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb defusedxml
# またはパッケージ化されていれば:
# pip install -e .
```

環境変数 / .env
- プロジェクトルートに `.env` と `.env.local`（任意）を配置すると自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 必須の環境変数（config.Settings が要求するもの）:

  - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
  - KABU_API_PASSWORD — kabu API パスワード（発注連携時）
  - SLACK_BOT_TOKEN — Slack 通知用トークン
  - SLACK_CHANNEL_ID — Slack チャンネル ID

- 任意の設定:

  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — DEBUG/INFO/...
  - DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

例 .env（簡易）

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

DB 初期化

Python REPL もしくはスクリプトで DuckDB スキーマを作成します。

```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# settings.duckdb_path からパスを取る
conn = init_schema(settings.duckdb_path)
# 既存 DB に接続する場合:
# conn = get_connection(settings.duckdb_path)
```

---

## 使い方（主要な呼び出し例）

以下は主要なモジュールの使い方例です。実運用ではログ設定やエラーハンドリングを適切に追加してください。

1) 日次 ETL の実行（市場カレンダー取得 → 株価/財務差分取得 → 品質チェック）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量（features）ビルド

```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

3) シグナル生成

```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
num_signals = generate_signals(conn, target_date=date.today())
print(f"signals written: {num_signals}")
```

4) ニュース収集ジョブ（RSS を取得し raw_news に保存、銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

# known_codes は既知の銘柄コードセット（prices_daily などから取得）
rows = conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall()
known_codes = {r[0] for r in rows}

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

5) カレンダー更新ジョブ（夜間バッチ）

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn, lookahead_days=90)
print(f"calendar rows saved: {saved}")
```

6) J-Quants からのデータ取得（直接利用）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, get_id_token

token = get_id_token()
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 設定・構成（環境変数の要点）

- .env 自動読み込み:
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探索し `.env` と `.env.local` を読み込みます。
  - 上書き優先度: OS 環境変数 > .env.local > .env
  - テスト等で自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- Settings API（import 例）:

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

- KABUSYS_ENV の有効値: "development", "paper_trading", "live"
- LOG_LEVEL の有効値: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"

---

## ディレクトリ構成

（src/kabusys 以下の主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - pipeline.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/
      - (監視関連モジュール: 実装ファイルがある場合)

README に記載されたものの他、細かなユーティリティや補助モジュールが含まれます。主要な機能は上記モジュール群に実装されています。

---

## 開発・テスト

- 単体テスト・統合テストは DuckDB のインメモリモード（db_path=":memory:"）を利用して実行できます。
- config の自動読み込みをテストの影響から切り離す場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、必要な環境値をテスト内で注入してください。
- 外部 API（J-Quants / RSS / 証券会社等）呼び出しはモック化してテストすることを推奨します（例: kabusys.data.jquants_client._request や news_collector._urlopen の差し替え）。

---

## 依存関係（主なもの）

- duckdb
- defusedxml

その他は標準ライブラリ（urllib, json, datetime, logging, math, re, hashlib 等）で実装されています。実際のプロジェクトでは requirements.txt / pyproject.toml を用意して依存管理してください。

---

## ライセンス・貢献

- ライセンス情報や貢献ガイドラインはリポジトリのルートに LICENSE / CONTRIBUTING.md を配置してください（本テンプレートでは含まれていません）。

---

不明点や README に追加してほしい具体的な使用例（例えば Slack 通知フロー、kabu ステーション発注のサンプルなど）があれば教えてください。必要に応じてサンプルスクリプトや運用手順を追記します。