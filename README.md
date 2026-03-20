# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants から市場データや財務データを取得し、DuckDB に保存、特徴量生成・シグナル生成・ニュース収集など戦略実行に必要な処理を提供します。

- 現在のバージョン: 0.1.0

---

## 概要

KabuSys は以下のレイヤーで構成される日本株自動売買向けプラットフォームのコア機能を提供します。

- Data layer: J-Quants から株価・財務・カレンダー・ニュースを取得して DuckDB に保存する ETL・スキーマ
- Research layer: ファクター計算、将来リターン・IC の計算、特徴量探索
- Strategy layer: 特徴量の正規化・合成とシグナル生成（BUY / SELL）
- Execution / Monitoring 層のインターフェース（発注・監査・監視を格納するスキーマを含む）
- ユーティリティ: 環境設定、統計関数、ニュースパーシング、J-Quants クライアント等

設計上の要点:
- DuckDB を永続 DB として利用（:memory: も可）
- J-Quants API のレート制限・リトライ・トークンリフレッシュ対応
- ETL と DB 保存は冪等（ON CONFLICT / トランザクション）を意識
- ルックアヘッドバイアス防止のため計算は target_date 時点のデータのみを利用

---

## 主な機能一覧

- DuckDB スキーマの初期化（data.schema.init_schema）
- J-Quants API クライアント（data.jquants_client）
  - 株価日足、財務データ、マーケットカレンダーの取得・保存
  - レートリミット、リトライ、トークン自動更新対応
- ETL パイプライン（data.pipeline）
  - run_daily_etl: カレンダー・株価・財務の差分取得と品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別 ETL
- ニュース収集（data.news_collector）
  - RSS 取得、テキスト前処理、記事保存、銘柄抽出
  - SSRF / XML Bomb / 大容量対策などの安全対策
- 研究用ファクター計算（research.factor_research）
  - Momentum / Volatility / Value 等のファクターを計算
- 特徴量作成（strategy.feature_engineering）
  - Z スコア正規化、ユニバースフィルタ、features テーブルへの UPSERT
- シグナル生成（strategy.signal_generator）
  - 各ファクター＋AIスコアを統合して final_score を計算し BUY/SELL を作成
  - Bear レジーム抑制、ストップロス等のエグジット条件
- 統計ユーティリティ（data.stats）
- マーケットカレンダー管理（data.calendar_management）
- 監査ログスキーマ（data.audit）

---

## システム要件（推奨）

- Python 3.10+
- pip
- DuckDB（Python パッケージ：duckdb）
- defusedxml（RSS XML パース用）
- ネットワークアクセス（J-Quants API、RSS）

最低限インストールするパッケージ例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

プロジェクト化されている場合は setup/requirements があればそれを利用してください（本リポジトリでは requirements.txt は含まれていません）。

---

## 環境変数 / 設定

自動で .env / .env.local をプロジェクトルートから読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主要な環境変数（必須となるもの）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack 通知先チャネル ID（必須）

オプション / デフォルト:
- KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
- LOG_LEVEL   : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視 DB 等の SQLite パス（デフォルト: data/monitoring.db）

設定読み込みのユーティリティ:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## セットアップ手順（開発 / 実行）

1. レポジトリをクローンし仮想環境を作成
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 他に必要なパッケージがあれば追加でインストール
```

2. 環境変数を設定
- プロジェクトルートに `.env` を作り、必要な値を設定します（.env.example を参考に）。
例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

3. DuckDB スキーマ初期化
Python REPL やスクリプトで初期化できます。
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
# 以降 conn を使って ETL / 解析 / 戦略を実行
```

---

## 使い方（主要な API 例）

以下は代表的な利用例です。実運用ではエラーハンドリングやログ設定を追加してください。

- 日次 ETL を実行（カレンダー→株価→財務→品質チェック）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # デフォルトは今日
print(result.to_dict())
```

- 特徴量を構築（strategy.feature_engineering.build_features）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("/path/to/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 1, 10))
print(f"features upserted: {count}")
```

- シグナル生成（strategy.signal_generator.generate_signals）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection("/path/to/kabusys.duckdb")
signals_written = generate_signals(conn, target_date=date(2025,1,10))
print(f"signals written: {signals_written}")
```

- ニュース収集ジョブ（RSS 取得→raw_news保存→銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("/path/to/kabusys.duckdb")
# known_codes は既知の銘柄コードセット（例: prices_daily から取得）
rows = conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall()
known_codes = {r[0] for r in rows}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

- J-Quants の生データを直接取得して保存
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("/path/to/kabusys.duckdb")
recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
saved = jq.save_daily_quotes(conn, recs)
print(saved)
```

---

## 推奨ワークフロー（例）

1. init_schema() で DuckDB を初期化
2. run_daily_etl() を Cron / Airflow 等で毎日実行してデータを蓄積
3. build_features() を実行して strategy/features を作成
4. generate_signals() を実行し signals テーブルに BUY/SELL を書き込む
5. Execution 層（kabu ステーションやブローカ API）により発注し、実行ログを audit テーブルに記録
6. Slack 連携などでモニタリング・通知

---

## ログ・デバッグ

- LOG_LEVEL は環境変数で設定可能（LOG_LEVEL=DEBUG など）
- 各モジュールは標準 logging を使用しています。必要に応じて logging.basicConfig() でハンドラやフォーマットを設定してください。

---

## ディレクトリ構成

以下は主要なファイル・モジュールの一覧（提供コードベースに基づく抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数/設定管理
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント
      - news_collector.py      # RSS ニュース収集
      - schema.py              # DuckDB スキーマ定義・init_schema
      - stats.py               # 統計ユーティリティ（zscore 等）
      - pipeline.py            # ETL パイプライン
      - features.py            # data レイヤの公開インターフェース
      - calendar_management.py # カレンダー管理ユーティリティ
      - audit.py               # 監査ログスキーマ
      - ...                    # 他（quality 等が想定される）
    - research/
      - __init__.py
      - factor_research.py     # ファクター計算（momentum/volatility/value）
      - feature_exploration.py # 将来リターン/IC/統計サマリ
    - strategy/
      - __init__.py
      - feature_engineering.py # features の構築（正規化・フィルタ）
      - signal_generator.py    # final_score 計算・BUY/SELL 生成
    - execution/                # 発注/実行管理（パッケージ化の入口）
    - monitoring/               # 監視・メトリクス（パッケージ化の入口）

（実際のリポジトリではこれらに加えて tests、docs、スクリプト等が存在することが想定されます）

---

## 注意事項 / TODO

- 本リポジトリは戦略モデルや実際の資金管理を含みます。実稼働で使用する場合は十分なバックテスト・リスク管理を行ってください。
- 実際の発注（execution 層）と接続する場合は、証券会社 API の仕様・認証・手数料・約定モデルを考慮する必要があります。
- 一部の機能（トレーリングストップ、時間決済、監査の一部ロジック等）はコメントに未実装箇所の注記があります。必要に応じて拡張してください。

---

もし README に追加したい実行スクリプト例（systemd/cron 用のラッパー、docker-compose サンプル、CI 設定など）があれば、用途に合わせてサンプルを作成できます。どの項目を優先して追加しますか？