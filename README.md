# KabuSys

日本株向けの自動売買（トレーディング）プラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、DuckDB スキーマ等を含む、研究〜本番までのワークフローを想定したモジュール構成になっています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の層を備えた日本株自動売買基盤のライブラリ群です。

- Data Layer: J-Quants から株価・財務・カレンダー等を取得し DuckDB に保存
- Feature / Research: ファクター計算（モメンタム、ボラティリティ、バリュー等）・探索用ユーティリティ
- Strategy: 正規化済み特徴量と AI スコアを統合して売買シグナルを生成
- Execution (骨格): 発注・約定・ポジションのスキーマ設計（発注実装は別途）
- Monitoring / News: RSS 収集、ニュース→銘柄紐付け、品質チェック等

設計上のポイント:
- ルックアヘッドバイアスの回避（各処理は target_date 時点の情報のみを参照）
- 冪等性（DB 保存は ON CONFLICT 対応など）
- 外部依存は最小（DuckDB と一部標準ライブラリ、defusedxml 等を使用）

---

## 主な機能一覧

- J-Quants API クライアント（取得・リトライ・レート制御・トークンリフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
- DuckDB スキーマ初期化 / 接続ユーティリティ
  - init_schema(db_path) / get_connection(db_path)
- ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
- 研究用ファクター計算
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
- 特徴量作成（正規化・ユニバースフィルタ）
  - build_features(conn, target_date)
- シグナル生成
  - generate_signals(conn, target_date, threshold, weights)
- ニュース収集（RSS）と DB 保存
  - fetch_rss / save_raw_news / run_news_collection
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 各種統計ユーティリティ（z-score 正規化 等）

---

## 必要な環境変数（主なもの）

Settings クラスで参照されます。README にある環境変数を .env へ設定してください。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション等の API パスワード（発注実装がある場合）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必要に応じて）
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV           : development / paper_trading / live （デフォルト: development）
- LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL （デフォルト: INFO）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）

自動 env ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python (3.10+) をインストールします（本リポジトリの型注釈などから Python 3.10 以上を想定）。

2. 仮想環境を作成して有効化:
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 必要パッケージをインストール:
   - 本コードベースでは少なくとも以下が必要です:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を用意して依存管理してください。

4. リポジトリルートに .env を作成（上記の必須環境変数を設定）。

5. DuckDB スキーマを初期化:
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可能
     ```

---

## 使い方（簡易ガイド）

いくつかの代表的な処理の実行例を示します。

- DuckDB 初期化 + ETL（日次）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量作成（build_features）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

- シグナル生成（generate_signals）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {n}")
```

- ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"market_calendar saved: {saved}")
```

注意:
- 上記は本ライブラリのコア関数を直接呼ぶサンプルです。運用ではログ設定、例外ハンドリング、トークン注入（テスト時）などを追加してください。
- run_daily_etl は ETL 実行結果（ETLResult）を返します。result.has_errors / result.has_quality_errors 等で状態確認できます。

---

## 実装上のポイント・設計ノート

- 冪等性: DuckDB への保存は ON CONFLICT や INSERT ... RETURNING を用いて重複を防ぎます。
- レート制御: J-Quants クライアントは固定間隔スロットリング（120 req/min）を実装。
- リトライ: HTTP エラーやネットワークエラーに対して指数バックオフのリトライを行う。
- セキュリティ: RSS 取得では SSRF 対策、XML パースに defusedxml を利用、URL 正規化で追跡パラメータを削除。
- バイアス対策: ルックアヘッドバイアスを避けるため target_date 時点の情報だけで計算する設計。

---

## ディレクトリ構成

リポジトリの主要ファイルとフォルダ（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                    # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント（取得・保存）
    - news_collector.py          # RSS 収集・記事保存・銘柄紐付け
    - schema.py                  # DuckDB スキーマ定義・初期化
    - stats.py                   # 統計ユーティリティ（zscore_normalize）
    - pipeline.py                # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py     # カレンダー更新・営業日判定
    - audit.py                   # 監査ログ（signal/order/execution）
    - features.py                # features 再エクスポート
  - research/
    - __init__.py
    - factor_research.py         # ファクター計算（momentum/volatility/value）
    - feature_exploration.py     # 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py     # 特徴量作成（正規化・ユニバースフィルタ）
    - signal_generator.py        # シグナル生成ロジック
  - execution/                    # 発注関連（空の __init__.py 等）
  - monitoring/                   # 監視関連（実装ファイルはここに置く想定）

---

## 開発・テストに関するヒント

- 環境依存を排除するため、設定読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます（テスト等で .env を自動読み込みしたくない場合に便利）。
- DuckDB は ":memory:" を使ってインメモリ DB で処理を実行できます（単体テストで便利）。
- ネットワーク呼び出し（J-Quants や RSS）はモック化しやすいように関数が分離されており、id_token の注入なども可能です。

---

## ライセンス・貢献

本 README はコードベースの抜粋に基づくドキュメントです。実際のライセンス表記や貢献方法はリポジトリルートの LICENSE / CONTRIBUTING を参照してください（本コードにはライセンスファイルは含まれていません）。

---

必要であれば README に含めるサンプル .env.example やより詳細な API 仕様・運用手順（cron 設定、Slack 通知例、kabuステーション連携方法等）も作成します。どの項目を詳細化したいか教えてください。