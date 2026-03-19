# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）のリポジトリ用 README。

このドキュメントはソースコードを基にした概要・セットアップ・基本的な使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の機能を持つ Python モジュール群です：

- J-Quants API からの市場データ（株価・財務・マーケットカレンダー）取得と DuckDB への保存（差分取得・冪等保存）
- RSS からのニュース収集とテキスト前処理、銘柄紐付け
- 価格データを元にしたファクター計算（モメンタム、ボラティリティ、バリュー等）
- ファクターの正規化・特徴量生成（features テーブル）
- 特徴量 + AI スコアを用いたシグナル生成（BUY / SELL）
- マーケットカレンダー管理、ETL パイプライン、品質チェック、監査用テーブル群の初期化
- DuckDB を用いたローカル DB スキーマ（Raw / Processed / Feature / Execution 層）

設計上のポイント：
- ルックアヘッドバイアスを避けるため「target_date 時点で利用可能なデータのみ」を用いる実装（ETL・戦略・研究モジュール）
- DuckDB を中核に、SQL と純粋 Python の組合せで高速に処理
- API レート制御・リトライ・トークン自動リフレッシュなどの堅牢な実装（J-Quants クライアント）
- DB への保存は冪等（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING を活用）

---

## 主な機能一覧（モジュール / 主要関数）

- kabusys.config
  - settings: 環境変数による設定取得（J-Quants トークン、kabu API、Slack、DB パスなど）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可能）

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（トークン自動リフレッシュ）, リトライ・レートリミット実装

- kabusys.data.schema
  - init_schema(db_path): DuckDB のテーブル・インデックスを初期化
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...): カレンダー → 株価 → 財務 → 品質チェック の ETL を実行
  - run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.data.news_collector
  - fetch_rss(url, source): RSS の取得＋解析（SSRF 対策・gzip 上限・XML 脆弱性対策済み）
  - save_raw_news / save_news_symbols / run_news_collection

- kabusys.research
  - calc_momentum / calc_volatility / calc_value: ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank: 研究用の解析ユーティリティ
  - zscore_normalize（data.stats 経由）

- kabusys.strategy
  - build_features(conn, target_date): raw ファクターを正規化して features テーブルへ保存
  - generate_signals(conn, target_date, threshold, weights): features + ai_scores を統合して signals を生成

- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job

- kabusys.data.audit
  - 監査用テーブル群（signal_events, order_requests, executions など）を定義

- その他
  - data.stats.zscore_normalize: クロスセクション Z スコア正規化
  - execution, monitoring モジュール群（パッケージ階層に定義される）

---

## 必要条件 / 依存ライブラリ

- Python 3.10 以上（typing の `X | None` などの構文を使用）
- pip インストール可能なパッケージ（最低限）:
  - duckdb
  - defusedxml

例：
```bash
python -m pip install "duckdb" "defusedxml"
```

（実運用では logging、テスト系、Slack 通知等の追加パッケージが必要になる場合があります）

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトディレクトリへ移動

2. Python 仮想環境を作成（推奨）
```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows
```

3. 必要パッケージをインストール
```bash
pip install duckdb defusedxml
```

4. 環境変数または .env ファイルを用意する
- 自動読み込み: パッケージはプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動でロードします。
- 無効化したい場合:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

- 主要な環境変数（例）:
  - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
  - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
  - KABU_API_BASE_URL : kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知用（必須）
  - DUCKDB_PATH : DuckDB ファイルパス（省略時: data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 SQLite DB（省略時: data/monitoring.db）
  - KABUSYS_ENV : "development" / "paper_trading" / "live"（デフォルト: development）
  - LOG_LEVEL : "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"

例 .env の最小例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

---

## 基本的な使い方（コード例）

- DuckDB スキーマを初期化して接続を取得
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行（カレンダー・価格・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日
print(result.to_dict())
```

- 特徴量（features）を構築
```python
from datetime import date
from kabusys.strategy import build_features
cnt = build_features(conn, date(2024, 1, 10))
print("upserted features:", cnt)
```

- シグナルを生成
```python
from kabusys.strategy import generate_signals
from datetime import date
n = generate_signals(conn, date(2024, 1, 10), threshold=0.6)
print("signals generated:", n)
```

- RSS からニュース収集（既知銘柄コードセットを与えて銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コード集合
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

注意点:
- 各関数は基本的に DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。init_schema で初期化した接続を使うか、get_connection で接続してください。
- J-Quants API を利用する関数は settings.jquants_refresh_token に依存します。環境変数を設定してください。
- generate_signals は ai_scores / positions / features 等の DB テーブルを参照します。事前に ETL と build_features を実行してください。

---

## 推奨運用フロー（概略）

1. init_schema で DB を構築
2. 定期的に run_daily_etl を実行してデータを更新（Cron / Airflow 等）
3. ETL 後に build_features を実行して features を更新
4. generate_signals でシグナルを作成
5. シグナルは signals テーブルに格納。別プロセスで execution 層が取り出して発注処理を行う（order_requests / executions / trades 等で監査）

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要ファイルとフォルダ構成の抜粋（src/kabusys 配下）です。

- src/kabusys/
  - __init__.py
  - config.py                           # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py                 # J-Quants API クライアント（fetch/save）
    - news_collector.py                 # RSS ニュース収集・保存
    - schema.py                         # DuckDB スキーマ定義 & init_schema
    - stats.py                          # 統計ユーティリティ（zscore_normalize）
    - pipeline.py                       # ETL パイプライン（run_daily_etl 他）
    - features.py                       # zscore_normalize の再エクスポート
    - calendar_management.py            # マーケットカレンダー管理
    - audit.py                          # 監査ログ用テーブル定義
    - audit.py                          # （同上 - 監査ログ）
  - research/
    - __init__.py
    - factor_research.py                # ファクター計算（momentum/volatility/value）
    - feature_exploration.py            # 研究用ユーティリティ（IC / forward returns / summary）
  - strategy/
    - __init__.py
    - feature_engineering.py            # features を作る処理
    - signal_generator.py               # final_score 計算 & signals 作成
  - execution/                           # 発注・ブローカー連携層（パッケージ）
    - __init__.py
  - monitoring/                          # 監視関連のコード（パッケージ）
    - __init__.py

（上記はコードベースに基づく主要ファイル。テスト、docs、スクリプト等はこの抜粋に含みません）

---

## 注意事項 / 補足

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。CI や一部のテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- J-Quants API の利用には API トークン（refresh token）が必要です。get_id_token はトークンを取得・キャッシュし、401 時に自動リフレッシュします。
- news_collector は外部ネットワークからの RSS 取得を行うため、SSRF 対策やレスポンスサイズ制限、XML パースの安全化（defusedxml）を実装しています。
- DuckDB のファイルパス（DUCKDB_PATH）は Settings.duckdb_path で取得できます。デフォルトは data/kabusys.duckdb。
- 実運用でブローカーへの実発注を行う場合は execution 層の実装・テスト・リスク管理（スロットリング、冪等性、監査）を十分に行ってください。本リポジトリの execution パッケージは基本フレームワークを想定しています。

---

もし README に追加したい内容（API の詳細な例、SQL スキーマの抜粋、運用手順のテンプレート、CI/CD の設定例等）があれば教えてください。必要に応じてより詳細なドキュメント（StrategyModel.md, DataPlatform.md 相当の要約）も作成します。