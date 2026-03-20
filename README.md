# KabuSys

日本株向けの自動売買基盤ライブラリ（ミニマム実装）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ／監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築に必要な基盤機能をモジュール化したライブラリです。主な責務は以下です。

- J-Quants API からの市場データ・財務データ・カレンダー取得（レート制御・自動トークンリフレッシュ・リトライ付き）
- DuckDB を用いた Raw / Processed / Feature / Execution 層のスキーマ管理
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究／戦略層のファクター計算・特徴量正規化（Z スコア）・シグナル生成
- RSS ベースのニュース収集と銘柄紐付け
- 監査ログ（signal → order → execution のトレース）用テーブル定義

設計上のポイント:
- ルックアヘッドバイアスを避ける（target_date 時点で参照すべきデータのみ使用）
- 冪等性（DB への保存は ON CONFLICT / upsert を使う）
- ネットワーク安全（SSRF 対策、受信サイズ制限等）
- 外部依存を最小化（主要な統計処理は標準ライブラリで実装）

---

## 主な機能一覧

- data/jquants_client
  - API 呼び出し（ページング対応・レート制御・トークンリフレッシュ・リトライ）
  - fetch / save: 日足、財務、マーケットカレンダー
- data/schema
  - DuckDB の完全なスキーマ初期化（Raw / Processed / Feature / Execution / Audit）
  - init_schema / get_connection
- data/pipeline
  - run_daily_etl: 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 個別 ETL ヘルパー（run_prices_etl 等）
- data/news_collector
  - RSS 取得、正規化、raw_news への保存、銘柄抽出と紐付け
- research / strategy
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 特徴量作成: build_features（Z スコア正規化・ユニバースフィルタ）
  - シグナル生成: generate_signals（final_score 計算、BUY/SELL の生成、エグジット判定）
- monitoring / execution（骨組み）
  - 監査ログ用スキーマ / テーブル群（signal_events, order_requests, executions 等）

---

## 必要環境（例）

- Python 3.10+（typing の union 型等を使用）
- 必要な主なパッケージ:
  - duckdb
  - defusedxml
（環境によって urllib 等の標準ライブラリのみで動作する箇所も多いですが、上記は必須に近い）

パッケージ管理は任意の方法で行ってください（pip / poetry 等）。例:
- pip install duckdb defusedxml

---

## セットアップ手順

1. ソースをクローン（またはコピー）:
   - git clone ...

2. 仮想環境の作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール:
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

4. 環境変数の設定:
   - プロジェクトルートに `.env` / `.env.local` を作成できます。.env は自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
   - 必須キー（最低限）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 任意:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化:
   - Python REPL やスクリプトから実行
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成・初期化
   ```

---

## 使い方（短いサンプル）

以下は基本的な操作フロー（DuckDB 初期化 → ETL → 特徴量作成 → シグナル生成）の例です。

- DuckDB の初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量構築（研究モジュールが prices_daily / raw_financials を参照する前提）
```python
from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

- シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

total = generate_signals(conn, target_date=date.today())
print(f"signals written: {total}")
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 抽出対象の銘柄コードセット（例: all tickers）
known_codes = {"7203", "6758", "9984", ...}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- J-Quants 直接呼び出し（テスト・確認用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
from kabusys.config import settings

quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

注意点:
- run_daily_etl 等は内部で try/except によりステップごとのエラーを吸収し、ETLResult にエラー情報を集約します。
- settings は環境変数ベースです。必須キーが未設定だと ValueError を投げます。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV — 環境識別子（development | paper_trading | live）
- LOG_LEVEL — ログレベル（DEBUG|INFO|...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — (任意) 自動 .env ロードを無効化するには 1 をセット

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧と簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み・Settings クラス
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save 関数）
    - news_collector.py — RSS 収集・前処理・DB 保存
    - schema.py — DuckDB スキーマ定義と init_schema/get_connection
    - stats.py — zscore_normalize など統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — market_calendar の管理ユーティリティ
    - audit.py — 監査ログ用テーブル DDL
    - features.py — zscore_normalize の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features（特徴量作成）
    - signal_generator.py — generate_signals（最終スコア計算・BUY/SELL 生成）
  - execution/ (骨組み: 発注処理等の実装箇所)
  - monitoring/ (監視・メトリクス用テーブル/ロジック)

---

## 開発上のヒント・注意点

- DuckDB の SQL は一部バージョン依存な記法があるため、テスト環境の duckdb バージョンを合わせてください。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を検索）にある .env / .env.local を読み込みます。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API 呼び出しはレート制限（120 req/min）に合わせて内部でスロットリングしています。大量バックフィルの際は時間がかかる可能性があります。
- NewsCollector は外部 RSS のHTML/XML を扱うため、defusedxml を利用した安全性確保やレスポンスサイズ上限を実装していますが、運用時は接続先の信頼性を確認してください。

---

README に記載の無い内部仕様（StrategyModel.md / DataPlatform.md 等）やテーブル定義の詳細はソースコードコメントに記載されています。必要に応じて各モジュールの docstring を参照してください。ご要望があれば、セットアップスクリプト例やサンプルワークフロー（Docker / systemd timer / Airflow 連携例）を追記します。