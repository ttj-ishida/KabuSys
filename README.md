# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、DuckDB スキーマ管理、ETL パイプライン、ファクター計算／特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムに必要な以下の機能群を提供します。

- J-Quants API からの市場データ取得（株価、財務、カレンダー）
- DuckDB ベースのスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 差分 ETL（差分取得・保存・品質チェック）
- 研究用途のファクター計算（モメンタム／ボラティリティ／バリュー等）
- 特徴量の正規化（Z スコア）・合成・features テーブルへの登録
- シグナル生成（final_score に基づく BUY/SELL 判定、エグジット判定含む）
- ニュース（RSS）収集と記事 → 銘柄紐付け
- マーケットカレンダー管理（営業日判定・next/prev_trading_day 等）
- 監査ログ／トレーサビリティ（signal/events → order_requests → executions）

設計上の特徴:
- ルックアヘッドバイアスを避けるため「target_date 時点の情報のみ」を使用
- 冪等性（ON CONFLICT / INSERT … DO UPDATE 等）を意識した実装
- 外部依存を最小化（標準ライブラリ中心、DuckDB・defusedxml 等を利用）
- ETL・データ取得に対してリトライ／レートリミット制御を実装

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・トークン自動更新・レート制御・保存関数）
  - schema: DuckDB スキーマ定義と init_schema()
  - pipeline: 日次差分 ETL 実装（run_daily_etl）
  - news_collector: RSS 取得・記事正規化・DB への冪等保存・銘柄抽出
  - calendar_management: market_calendar 管理・営業日判定・calendar_update_job
  - stats: zscore_normalize 等の統計ユーティリティ
- research/
  - factor_research: モメンタム／ボラティリティ／バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- strategy/
  - feature_engineering: ファクターの合成・ユニバースフィルタ・Z スコア正規化 → features へ保存
  - signal_generator: features / ai_scores / positions を統合して BUY/SELL シグナルを生成
- config: 環境変数管理（.env 自動読み込み、必須値取得用 settings）
- audit / execution / monitoring: 発注・監査・モニタリング（骨格）

---

## 必要環境 / 依存関係

- Python >= 3.10（| 型注記を使用）
- duckdb
- defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# その他必要パッケージがあれば適宜追加
```

（プロジェクトには requirements.txt は付属していません。実行環境に応じて追加してください）

---

## 環境変数（.env）

パッケージは .env（および .env.local）から自動的に環境変数を読み込みます（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.env の簡易例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. リポジトリをクローン（あるいはパッケージを配置）
2. Python 仮想環境を作成・有効化
3. 依存ライブラリをインストール（上記参照）
4. 必要な環境変数を .env に設定（プロジェクトルートに配置）
5. DuckDB スキーマ初期化

DuckDB スキーマ初期化例（Python REPL またはスクリプト）:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

---

## 使い方（代表的な API）

以下はよく使うワークフローのサンプルです。

- 日次 ETL（市場カレンダー / 株価 / 財務）を実行:
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- 特徴量（features）を構築:
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, date(2024, 1, 31))
print(f"features upserted: {count}")
```

- シグナル生成:
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, date(2024, 1, 31))
print(f"signals written: {total}")
```

- RSS ニュース収集（known_codes を渡すと銘柄紐付けを行う）:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コード集合
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: inserted_count, ...}
```

- カレンダー更新ジョブ（夜間バッチ想定）:
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- J-Quants からのデータ取得を手動で呼ぶ（低レベル）:
```python
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# 保存:
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
jq.save_daily_quotes(conn, records)
```

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なディレクトリ／ファイル構成（src/kabusys 以下）:

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
    - audit (その他の data モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/         # 発注関連（骨格）
  - monitoring/        # 監視・メトリクス（骨格）
  - (その他モジュール)

各モジュールの役割:
- config.py: .env からの自動読み込み、settings オブジェクト経由で設定を提供
- data/schema.py: DuckDB の DDL を定義し init_schema() を提供
- data/jquants_client.py: J-Quants API 呼び出し / rate limit / save_* 関数
- data/pipeline.py: 差分 ETL の高レベル API（run_daily_etl）
- research/*: 研究用途のファクター計算・評価関数
- strategy/*: features → signals の流れを実装
- data/news_collector.py: RSS 取得 → raw_news 保存 → news_symbols 紐付け

---

## 注意点 / 運用上のヒント

- 環境変数は .env / .env.local に設定すること。OS 環境変数が優先されます。
- DuckDB の初期化は一度行えば良く、以後は get_connection() で接続を再利用できます。
- J-Quants のレート制限（120 req/min）や一部 API の 401 を自動でハンドルしますが、実運用では API 使用量に注意してください。
- ニュース収集は RSS ソースの信頼性・サイズに注意（レスポンスサイズ上限や SSRF チェックあり）。
- 本コードベースは本番口座（live）への発注処理を含むため、実資金で運用する際は充分なレビューとテストを行ってください。
- KABUSYS_ENV を `paper_trading` にしてペーパートレード運用、`live` で実資金運用のスイッチを実装すると安全です。

---

## 開発 / 貢献

- コード・API の変更はユニットテストを追加してから PR を送ってください（テストフレームワークは任意）。
- .env.example をリポジトリに含めると初期セットアップが楽になります（現在は .env の手動作成を想定）。

---

必要があれば、この README を英語版に翻訳したり、具体的なコマンドライン実行スクリプト（cron / systemd / Airflow 等）例、CI 設定や Dockerfile のテンプレートも追記できます。どの追加情報が必要か教えてください。