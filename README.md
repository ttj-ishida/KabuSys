# KabuSys

日本株向けの自動売買およびデータプラットフォームライブラリです。データ取得（J-Quants API）、DuckDB を用いたデータ格納・スキーマ、ファクター計算・特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、ETL パイプラインなどを含むモジュール群を提供します。

## 特徴（概要）
- J-Quants API クライアント（ページネーション・レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター計算（モメンタム / バリュー / ボラティリティ / 流動性）
- 特徴量エンジニアリング（Z スコア正規化・ユニバースフィルタ）
- シグナル生成（ファクター + AI スコア統合、BUY/SELL の判定）
- ニュース収集（RSS フィード・SSRF 対策・記事正規化・銘柄抽出）
- マーケットカレンダー管理（営業日判定、next/prev/trading days）
- 監査用テーブル（シグナル → 発注 → 約定 のトレースを想定）

---

## 機能一覧（主要モジュール）
- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルート検出）と環境変数アクセス
  - 必須設定の取得ユーティリティ
- kabusys.data
  - jquants_client: J-Quants API 取得（株価・財務・カレンダー）、DuckDB 保存ユーティリティ
  - schema: DuckDB スキーマ定義 / init_schema(), get_connection()
  - pipeline: 日次・差分 ETL（run_daily_etl(), run_prices_etl(), …）
  - news_collector: RSS 取得・前処理・DB 保存（save_raw_news(), run_news_collection()）
  - calendar_management: is_trading_day(), next_trading_day(), calendar_update_job()
  - stats / features: 統計ユーティリティ（zscore_normalize）
  - audit: 監査テーブル DDL（signal_events / order_requests / executions）
- kabusys.research
  - factor_research: calc_momentum(), calc_volatility(), calc_value()
  - feature_exploration: calc_forward_returns(), calc_ic(), factor_summary(), rank()
- kabusys.strategy
  - feature_engineering.build_features(conn, target_date)
  - signal_generator.generate_signals(conn, target_date, ...)
- kabusys.execution (発注層のためのプレースホルダ)
- kabusys.monitoring (モニタリング用インターフェースを想定)

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（例）
```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.\.venv\Scripts\activate   # Windows (PowerShell)
```

2. 必要パッケージをインストール
（本リポジトリに requirements ファイルがない場合は最低限以下をインストール）
```bash
pip install duckdb defusedxml
```
※ 実運用では HTTP ライブラリやロギング設定、Slack 連携など必要に応じて追加してください。

3. 環境変数を用意する
プロジェクトルート（.git または pyproject.toml を基準）に `.env` を置くと自動で読み込まれます（自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

推奨される最小の .env（例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. DuckDB スキーマ初期化
Python REPL またはスクリプトからスキーマを作成します。

例: init_schema を実行するスクリプト
```python
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
```

---

## 使い方（簡単な例）

- DuckDB 接続とスキーマ初期化
```python
from kabusys.data.schema import init_schema, get_connection

conn = init_schema("data/kabusys.duckdb")
# 以降 conn を渡して各処理を行う
```

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量作成（features テーブルの構築）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date.today())
print("features upserted:", count)
```

- シグナル生成（signals テーブルへ登録）
```python
from datetime import date
from kabusys.strategy import generate_signals

total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("signals written:", total_signals)
```

- ニュース収集（RSS から raw_news に保存）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ（夜間バッチ想定）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

---

## 環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（監視用、デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live)。不正値は例外
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みをスキップ

設定は .env, .env.local または OS 環境変数から読み込まれます。読み込み優先度は OS 環境 > .env.local > .env です。

---

## 注意点 / 実装上の留意事項
- J-Quants API のレートリミット（120 req/min）を遵守するため内部でスロットリングを行っています。
- API 呼び出しはリトライ処理（指数バックオフ）、401 時のトークン自動リフレッシュを備えています。
- DuckDB の保存は可能な限り冪等（ON CONFLICT / トランザクション）を用いています。
- ルックアヘッドバイアス回避に注意しており、各処理は target_date 時点のデータのみを利用する設計です。
- news_collector では SSRF 対策、XML パース安全化（defusedxml）、レスポンスサイズ制限などの安全対策を実装しています。
- 一部の設計・仕様（StrategyModel.md / DataPlatform.md 等）に従う前提で実装されています。実際に実行する際は該当ドキュメントを参照してください（リポジトリに未含の場合は別途用意してください）。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
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
    - monitoring/    # モニタリング関連（参照は __all__ に含む可能性あり）
- README.md (本ファイル)
- .env.example (プロジェクトルートに置く想定)

各モジュールの詳細はソース内の docstring に設計方針・API が記載されています。API 名と引数は docstring を参照して呼び出してください。

---

## よくある操作（チートシート）
- スキーマ初期化:
  - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
- 日次 ETL 実行（スクリプトから）:
  - Python 内で run_daily_etl(conn)
- 特徴量作成 + シグナル生成:
  - build_features(conn, date)
  - generate_signals(conn, date)
- RSS ニュース収集:
  - run_news_collection(conn, sources=..., known_codes=...)

---

もし README に追加したい実行例（cron / systemd ユニット / Airflow DAG 例）や、環境別の運用手順（paper_trading/live 切り替え、Slack 通知設定）などがあれば、用途に合わせて追記します。どの操作を優先してドキュメント化しますか？