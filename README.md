# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、カレンダー管理、監査ログなどを含むモジュール群を提供します。

---

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価／財務／カレンダー取得（レート制御・リトライ付き）
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）のスキーマ管理
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算、クロスセクション正規化（Zスコア）
- 戦略向けの特徴量生成・シグナル生成（BUY / SELL の判定ロジック）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・トラッキング除去）
- マーケットカレンダー管理（営業日／SQ 日判定）
- 発注・約定・監査ログ向けのスキーマ（監査トレーサビリティ）

設計方針としては「ルックアヘッドバイアス排除」「冪等性」「外部サービスに対する安全対策（SSRF等）」を重視しています。

---

## 主な機能（抜粋）

- J-Quants クライアント（ページネーション、リトライ、トークン自動更新）
- DuckDB スキーマ初期化（init_schema）
- 日次 ETL（run_daily_etl）— カレンダー、株価、財務を差分で取得・保存
- ファクター計算（momentum / volatility / value）
- 特徴量生成（build_features） — Z スコア正規化、ユニバースフィルタ適用、features テーブルへの UPSERT
- シグナル生成（generate_signals） — AI スコア統合、レジーム判定、BUY/SELL 判定、signals テーブルへの保存
- ニュース収集（fetch_rss / save_raw_news / run_news_collection） — RSS 取得、前処理、銘柄抽出、保存
- マーケットカレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
- 監査ログ DDL（signal_events / order_requests / executions 等）

---

## 必要条件 / 依存ライブラリ

- Python 3.10 以上（typing の | 記法などを使用）
- 必要な Python パッケージ（例）:
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, datetime, logging, json, hashlib, socket など

（上記はコードから必要性が読み取れる主要パッケージ。実際の setup.py / pyproject.toml に合わせてインストールしてください。）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはプロジェクトの要件ファイルがあればそれを使う
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

2. 依存パッケージをインストールします（上記参照）。

3. 環境変数を準備します。パッケージはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（テスト時に無効化するなら `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須の環境変数（コードから判明するもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注層利用時）
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルト可能な環境変数:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / ...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視データベースパス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化

例 .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

4. DuckDB スキーマを初期化します（初回のみ）:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

---

## 使い方（サンプル）

以下はライブラリの代表的な使用例です。実際はアプリ側で CLI やジョブスケジューラに組み込んで利用します。

- 日次 ETL 実行（カレンダー、株価、財務の差分取得と保存、品質チェック）:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # デフォルトは今日を対象
print(result.to_dict())
```

- 特徴量（features）を生成:
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema(settings.duckdb_path)
n = build_features(conn, target_date=date(2024, 1, 12))
print(f"features upserted: {n}")
```

- シグナル生成:
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")
```

- ニュース収集ジョブ（RSS を取得して DB に保存、既知銘柄コードで紐付け）:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema(settings.duckdb_path)
# known_codes: 有効な銘柄コードのセット（例えば prices_daily の code カラムを参照して作成）
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー更新（夜間バッチ）:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意: 上記関数群は「DuckDB 接続」を受け取り、内部で必要なテーブルを参照します。初回は `init_schema()` を呼んでテーブルを作成してから使用してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なソース構成（`src/kabusys/`）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py       — RSS 取得 / 前処理 / DB 保存
    - schema.py               — DuckDB スキーマ定義・初期化
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  — カレンダー関連ユーティリティ・ジョブ
    - audit.py                — 監査ログ用 DDL（signal_events / order_requests / executions 等）
  - research/
    - __init__.py
    - factor_research.py      — momentum / value / volatility の計算
    - feature_exploration.py  — IC / forward returns / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py  — features 作成（正規化・フィルタ適用・UPSERT）
    - signal_generator.py     — final_score 計算、BUY/SELL 判定、signals 保存
  - execution/
    - __init__.py
    - （発注 / ブローカー連携は今後の実装想定）
  - monitoring/
    - （監視／メトリクス・Slack 通知用コードなどを想定）

各モジュールはドキュメント文字列（docstring）に設計方針や処理フローが記載されています。詳細は該当ファイルを参照してください。

---

## 開発・テスト時のヒント

- 環境変数の自動読み込みは `kabusys.config` がプロジェクトルート（.git または pyproject.toml の位置）を探索して `.env` / `.env.local` を読み込みます。テストで自動読み込みを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB をインメモリで使うことも可能です（テスト用）:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  ```
- HTTP 周りの処理（RSS 取得 / J-Quants）や外部依存はテスト時にモックしやすいように設計されています（関数にトークン注入可・内部の open 関数を差し替え可能など）。
- ログは標準の logging を使用します。`settings.log_level` を使ってログレベルを制御してください。

---

以上が README の要約です。追加で含めたい情報（例: 実際の CLI、CI 設定、pyproject.toml の依存一覧、設計ドキュメントへのリンクなど）があればお知らせください。README をそれらに合わせて拡張します。