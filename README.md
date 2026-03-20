# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ取得（J‑Quants）、ETL、マーケットカレンダー管理、ニュース収集、ファクター計算、特徴量正規化、シグナル生成、発注監査用スキーマなどを含み、研究（research）→ 特徴量（feature）→ 戦略（strategy）→ 実行（execution）というワークフローを想定しています。

主な設計方針
- ルックアヘッドバイアスを防ぐため、計算は必ず target_date 時点のデータのみを使用
- DuckDB を中心に冪等（idempotent）な保存を実現（ON CONFLICT / トランザクション）
- J-Quants API のレート制限・認証リフレッシュ・リトライ処理を実装
- RSS ニュース収集は SSRF 対策・入力正規化・重複排除を実施

---

## 機能一覧

- 環境設定読み込み（.env / OS 環境変数）、必須変数チェック（kabusys.config）
- DuckDB スキーマ定義・初期化（data.schema）
- J-Quants API クライアント（data.jquants_client）
  - レートリミット制御、リトライ、トークン自動リフレッシュ
  - 日足・財務・マーケットカレンダーの取得＋DuckDB への保存ユーティリティ
- ETL パイプライン（日次差分取得、バックフィル、品質チェックの呼出し）(data.pipeline)
- マーケットカレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
- ニュース収集（RSS フィード → raw_news、銘柄抽出、重複排除、SSRF/サイズ対策）
- ファクター計算（momentum / volatility / value）（research.factor_research）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ・features 保存）（strategy.feature_engineering）
- シグナル生成（features + ai_scores 統合、BUY/SELL 生成、エグジット判定）（strategy.signal_generator）
- 統計ユーティリティ（zscore_normalize 等）（data.stats）
- 発注／監査スキーマ（execution / data.audit） — 監査ログ用テーブル群定義

---

## 必要環境

- Python 3.10 以上（型注釈に `X | None` などを使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

例（仮想環境内）:
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install duckdb defusedxml
# 開発モードでインストールする場合（setup.py/pyproject があれば）
# pip install -e .
```

（プロジェクトで requirements.txt / pyproject.toml があればそちらに従ってください。）

---

## 環境変数（Settings）

kabusys.config.Settings で参照する主要な環境変数（必須・デフォルト値の例）:

必須
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意（デフォルトあり）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/...（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動的な .env ファイル読み込みを無効化

データベースパス（デフォルト）
- DUCKDB_PATH — data/kabusys.duckdb
- SQLITE_PATH — data/monitoring.db

自動で .env/.env.local をプロジェクトルートから読み込みます。自動読み込みを無効化するには:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

サンプル .env（README 用の例）
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 任意: pip install -e .
```

2. 環境変数を設定（.env をプロジェクトルートに作成）
- 上記のサンプルを参考に .env を作成してください。

3. DuckDB スキーマを初期化
Python REPL かスクリプトで:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ディレクトリを自動作成
conn.close()
```

---

## 使い方（主要 API の例）

以下は最小限の操作例です。適宜ログ設定やエラーハンドリングを追加してください。

- 日次 ETL の実行（J-Quants からの差分取得・保存・品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # デフォルトで今日を対象に実行
print(result.to_dict())
conn.close()
```

- 特徴量作成（features テーブルへ保存）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, date(2025, 1, 1))
print(f"upserted features: {n}")
conn.close()
```

- シグナル生成
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, date.today())
print(f"generated signals: {count}")
conn.close()
```

- ニュース収集（RSS）と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄コード集合（4桁文字列）
known_codes = {"7203","6758","9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
conn.close()
```

- カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
conn.close()
```

- J-Quants の生データ取得（低レベル API）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings からリフレッシュトークンを参照して取得
records = fetch_daily_quotes(id_token=token, date_from=None, date_to=None)
```

---

## 実装上の注意 / 設計上のポイント

- DuckDB への書き込みは原則トランザクション内で行い、日付単位での置換（DELETE + INSERT）で冪等性を担保しています。
- J-Quants クライアントは 120 req/min のレート制限に対応する RateLimiter を実装。リトライ・バックオフ、401 の自動トークンリフレッシュを行います。
- RSS の取得は SSRF 対策（スキーム検査、プライベートIPブロック、リダイレクト検査）、受信サイズ制限、XML パースに対する defusedxml を用いた安全化を行っています。
- strategy 層は発注 API（execution 層）へ直接依存しない設計です。signals テーブルに出力し、別プロセス（execution 層）がそれをピックアップして発注する想定です。
- 設定は .env / .env.local / OS 環境変数から読み込まれます。テスト等で自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成（抜粋）

（プロジェクトルートは pyproject.toml か .git により自動検出されます）
```
src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      schema.py
      pipeline.py
      stats.py
      news_collector.py
      calendar_management.py
      features.py
      audit.py
      audit.py
      ... (その他 data 関連モジュール)
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    strategy/
      __init__.py
      feature_engineering.py
      signal_generator.py
    execution/
      __init__.py
    monitoring/
      (モニタリング関連モジュール)
```

主要ファイルの役割
- config.py: 環境変数/設定の読み込み
- data/schema.py: DuckDB スキーマ定義・初期化
- data/jquants_client.py: J-Quants API の取得・保存ユーティリティ
- data/pipeline.py: 日次 ETL の統括
- data/news_collector.py: RSS ニュース収集 → raw_news 保存
- research/*: 研究用のファクター計算・解析（IC/forward returns 等）
- strategy/*: 特徴量の構築・シグナル生成ロジック

---

## 開発者向けメモ

- 型注釈とドキュメント文字列（docstring）が充実しています。各モジュールの docstring を参照すると設計・仕様がわかります。
- 単体テストや CI の記載はリポジトリに依存します。テストを書く際は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にして環境依存を避けると便利です。
- DuckDB はファイルベースの軽量 DB で、":memory:" を指定すればインメモリでのテストが可能です。

---

ご希望があれば、README に以下の追加情報を追記します：
- 具体的な .env.example のテンプレート
- systemd / cron / Airflow 等での運用例（ETL・calendar 更新ジョブの定期実行）
- 実行例のスクリプト化（run_etl.py 等）や docker-compose での運用案内

必要な追加項目があれば教えてください。