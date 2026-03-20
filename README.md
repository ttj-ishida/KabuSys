# KabuSys

日本株向けの自動売買システム向けライブラリ群（研究・データプラットフォーム・戦略・実行・監査を含む）です。  
このリポジトリはデータの取得・保存（DuckDB）、ファクター計算、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、ETLパイプライン、監査ログなど、システム全体の主要コンポーネントを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要なユースケース例）
- ディレクトリ構成
- 環境変数一覧と設定方法
- 開発メモ / 注意事項

---

## プロジェクト概要

KabuSys は以下の層で構成された自動売買システムの基盤ライブラリです。

- Data Layer: J-Quants API などから取得した生データを DuckDB に保存・整形する（raw → processed → feature）。
- Research Layer: ファクター計算・特徴量探索・IC 計算などを提供。
- Strategy Layer: 正規化済み特徴量と AI スコア等を統合して売買シグナルを生成する。
- Execution / Audit Layer: シグナル・発注・約定・ポジション・監査ログ等のスキーマを定義。
- Utilities: RSS ニュース収集、安全なネットワークリクエスト、環境変数読み込みなど。

設計上、ルックアヘッドバイアスを避けるべく「target_date 時点」でのデータのみを用いる方針が各モジュールに反映されています。また、DuckDB へは冪等（ON CONFLICT）で保存する設計です。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）
  - 環境変数取得ラッパ（必須チェックなど）

- kabusys.data
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・リトライ・トークンリフレッシュ）
  - schema: DuckDB 用スキーマ定義と初期化（init_schema）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）
  - news_collector: RSS からのニュース収集と記事→銘柄紐付け
  - calendar_management: JPX カレンダー管理、営業日判定、カレンダー更新ジョブ
  - stats: zscore_normalize 等の統計ユーティリティ
  - features: zscore_normalize の公開インターフェース

- kabusys.research
  - factor_research: momentum/value/volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリ

- kabusys.strategy
  - feature_engineering.build_features: 生ファクターの正規化と features テーブルへの書き込み
  - signal_generator.generate_signals: final_score 計算、BUY/SELL シグナル生成と signals テーブルへの書き込み

- Kabusys は監査ログ（signal_events / order_requests / executions 等）と実行層テーブルを備えています。

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の union 型表記や型ヒントの利用のため推奨）
- pip, venv 等

推奨インストール手順（開発環境）

1. リポジトリをクローンして仮想環境を作る
```bash
git clone <this-repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
```

2. 依存パッケージをインストール
- 本コードが直接参照する外部依存は最低限以下です（環境によって追加が必要な場合あり）:
  - duckdb
  - defusedxml

例:
```bash
pip install duckdb defusedxml
# （必要に応じて）pip install -e .
```

3. 環境変数の準備
プロジェクトルートに `.env` （と `.env.local` は任意）を置くことで自動的に読み込まれます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。詳しくは「環境変数一覧」を参照。

4. DuckDB スキーマ初期化
Python REPL またはスクリプトから schema を初期化します:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path はデフォルト "data/kabusys.duckdb"
conn = init_schema(settings.duckdb_path)
```
`:memory:` を指定するとインメモリ DB を使えます（テスト用途）。

---

## 使い方（主要なユースケース）

以下は代表的な操作例です。各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ることが多いです。

1) スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # デフォルト target_date = today
print(result.to_dict())
```

3) 研究用: ファクター計算
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
```

4) 特徴量生成（features テーブルへの書き込み）
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, date(2024, 1, 31))
print(f"features upserted: {n}")
```

5) シグナル生成（signals テーブルへの書き込み）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, date(2024, 1, 31), threshold=0.6)
print(f"signals written: {count}")
```

6) ニュース収集ジョブ（RSS から raw_news に保存）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使う有効なコードのセット（例: 全上場銘柄リスト）
known_codes = {"7203", "6758", "9984", ...}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

7) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

---

## ディレクトリ構成（主要ファイル）

省略せずに主要モジュールを示します（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                       # 環境変数管理・自動読み込み
  - data/
    - __init__.py
    - jquants_client.py              # J-Quants API クライアント
    - schema.py                      # DuckDB スキーマ定義 & 初期化
    - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
    - news_collector.py              # RSS 収集・保存
    - calendar_management.py         # JPX カレンダー管理
    - features.py                    # features の再エクスポート（zscore）
    - stats.py                       # 統計ユーティリティ（zscore_normalize）
    - audit.py                       # 監査ログ用 DDL
    - ...（quality 等が別途存在する想定）
  - research/
    - __init__.py
    - factor_research.py             # momentum/value/volatility の計算
    - feature_exploration.py         # IC, forward returns, summary
  - strategy/
    - __init__.py
    - feature_engineering.py         # build_features
    - signal_generator.py            # generate_signals
  - execution/                        # 実行層（発注ラッパ等、拡張想定）
    - __init__.py
  - monitoring/                       # 監視 / メトリクス（拡張想定）

他に docs や DataPlatform.md / StrategyModel.md 等の設計ドキュメントが参照される想定です（実装内の docstring で参照）。

---

## 環境変数一覧

設定は `.env` / `.env.local` または OS 環境変数から読み込まれます。自動ロードはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（settings エントリ）

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants API のリフレッシュトークン。get_id_token の取得に使用。

- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード（execution 層で使用）。

- KABU_API_BASE_URL (任意)  
  kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）。

- SLACK_BOT_TOKEN (必須)  
- SLACK_CHANNEL_ID (必須)  
  通知用 Slack 設定（監視モジュール等で利用）。

- DUCKDB_PATH (任意)  
  DuckDB ファイルパス（例: data/kabusys.duckdb）。デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)  
  監視用 SQLite パス（例: data/monitoring.db）。デフォルト: data/monitoring.db

- KABUSYS_ENV (任意)  
  実行環境。allowed: development / paper_trading / live。デフォルト: development

- LOG_LEVEL (任意)  
  ログレベル。DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例 .env（最小）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 開発メモ / 注意事項

- 型ヒントで Python 3.10 の union 型（A | B）を利用しているため、Python 3.10 以上を推奨します。
- J-Quants API のレートリミット（120 req/min）に合わせて内部でスロットリングを行っています。大量の並列リクエストは避けてください。
- jquants_client は 401 でトークンを自動更新し 1 回リトライします。get_id_token は settings.jquants_refresh_token を使用します。
- DuckDB のバージョンや SQL 構文（ON CONFLICT、RETURNING 等）の差異に注意してください。推奨バージョンは最新の安定版を想定しています。
- ニュース収集は外部 HTTP を扱うため SSRF・ZIP Bomb 等の対策を実装しています（_is_private_host / MAX_RESPONSE_BYTES / defusedxml 等）。
- 各モジュールの docstring に重要な設計仕様（StrategyModel.md、DataPlatform.md 等）や注意点が記載されています。実運用前にこれらの仕様とテストを十分に行ってください。
- ETL パイプラインやシグナル→発注の実行部分は、paper_trading / live と environment に応じた十分な検証・安全制御（order limit、risk checks、監査ログ）の実装・テストが必要です。

---

不明点や README に追記してほしい実例（cron ジョブ例、CI 設定、より詳細な env.example など）があれば教えてください。必要に応じてサンプルスクリプトも追加します。