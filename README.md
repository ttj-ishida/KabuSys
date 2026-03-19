# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
DuckDB をデータ層に用い、J-Quants API や RSS を取り込み、研究（research）→ 特徴量（features）→ シグナル（signals）生成までのパイプラインを提供します。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- データ取得・保存（J-Quants API 経由の株価・財務・カレンダー、RSS ニュース）
- DuckDB を用いたスキーマ定義と永続化（Raw / Processed / Feature / Execution 層）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）
- シグナル生成（複数コンポーネントの重み付け合成、BUY/SELL 判定）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS の安全な取得と銘柄抽出）
- マーケットカレンダー管理（営業日判定・前後営業日探索）
- 監査ログ・発注追跡用のスキーマ

設計上、ルックアヘッドバイアス回避や冪等性（ON CONFLICT / upsert）、ネットワーク安全対策（SSRF/サイズ制限/XMLパースの安全化）に配慮しています。

---

## 主な機能一覧

- DuckDB スキーマの初期化（init_schema）
- J-Quants API クライアント（トークン自動リフレッシュ、レート制御、リトライ）
- 株価 / 財務 / カレンダーの差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- ファクター計算（calc_momentum / calc_volatility / calc_value）
- 特徴量作成（build_features）
- シグナル生成（generate_signals）
- RSS ベースのニュース収集と銘柄紐付け（fetch_rss / run_news_collection）
- マーケットカレンダー操作（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
- 監査ログ用スキーマ（signal_events / order_requests / executions）

---

## 動作環境・依存関係

- Python 3.10 以上（型注釈の `X | Y` を使用しているため）
- 必要な Python パッケージ（最低限）
  - duckdb
  - defusedxml

インストール例（venv 推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージとしてインストール可能なら:
# pip install -e .
```

（プロジェクトに pyproject.toml があれば `pip install -e .` で依存もインストールできる想定です）

---

## 環境変数 / 設定

KabuSys は `.env` / `.env.local` または OS 環境変数から設定を読み込みます。自動ロードはパッケージのルート（.git または pyproject.toml を探索）を基準に行われます。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（Settings で _require() が使われるもの）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabu API 用のパスワード（execution 層で利用想定）
- SLACK_BOT_TOKEN — Slack 通知用（Bot Token）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルト有り:

- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等に使う SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（任意）

サンプル .env:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリを取得する
   - git clone してプロジェクトルートへ移動

2. Python 仮想環境を作成して有効化

```bash
python -m venv .venv
source .venv/bin/activate
```

3. 依存パッケージをインストール

```bash
pip install duckdb defusedxml
# あるいはプロジェクトがパッケージ化されている場合:
# pip install -e .
```

4. 環境変数を用意
   - `.env`（または OS 環境）に必須の値（JQUANTS_REFRESH_TOKEN 等）を設定

5. DuckDB スキーマを初期化

Python REPL やスクリプト:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Settings.duckdb_path の Path オブジェクト
conn = init_schema(settings.duckdb_path)
# conn は duckdb connection。以降 ETL 等で使用する
```

---

## 使い方（主要 API の例）

以下は代表的な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

1) 日次 ETL の実行（市場カレンダー・株価・財務の差分取得と品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量の作成（features テーブルへの書き込み）

```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

3) シグナル生成（signals テーブルへ書き込み）

```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {n}")
```

4) ニュース収集（RSS 収集 → raw_news 保存 → 銘柄抽出）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes: 銘柄コードセット（例: 全上場銘柄の4桁コード）
results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
print(results)  # {source_name: saved_count, ...}
```

5) カレンダー更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意:
- J-Quants API 呼び出しには有効なトークンが必要です（JQUANTS_REFRESH_TOKEN）。
- ネットワーク/認証エラーは例外となるため運用ではリトライやアラートを組み合わせてください。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（抜粋）です。実際のリポジトリはさらに補助ファイルやドキュメントを含む想定です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 & 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 + 保存）
    - news_collector.py      — RSS 取得 / raw_news 保存 / 銘柄抽出
    - schema.py              — DuckDB スキーマ定義・初期化
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - features.py            — データ層の特徴量ユーティリティ公開
    - calendar_management.py — カレンダー管理（営業日判定・更新ジョブ）
    - audit.py               — 監査ログ用スキーマ定義
    - (その他: quality, etc. を想定)
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — IC/forward returns/統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル構築（正規化・フィルタ）
    - signal_generator.py    — final_score 計算と signals テーブル生成
  - execution/
    - __init__.py            — 発注・ブローカー連携を担う層（実装は別途）
  - monitoring/              — 監視・アラート関連（ファイルありうる）

---

## 注意点 / 運用上のヒント

- 自動 .env 読み込みはプロジェクトルートを基準に行われます。CI やテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って制御可能です。
- DuckDB ファイルはデフォルトで `data/kabusys.duckdb` を使用します。別パスを指定する場合は `DUCKDB_PATH` を設定してください。
- J-Quants のレート制限（120 req/min）に対してクライアント側でスロットリングが実装されていますが、運用負荷には注意してください。
- ニュース収集は外部ネットワーク（RSS）に依存します。SSRF 対策や最大レスポンスサイズチェックを実装していますが、追加のネットワークポリシー（プロキシ/ホワイトリスト）を推奨します。
- production（live）モードを有効にする際は KABUSYS_ENV=live に設定し、kabu ステーション等の発注周りのテストと検証を十分行ってください。

---

## ライセンス・貢献

（ここにライセンス情報やコントリビュート手順 / Issue / PR のポリシーを記載してください。プロジェクトによって内容を設定してください。）

---

この README はコードベース（src/kabusys 以下）を元に作成しています。実運用や導入時は追加のドキュメント（DataPlatform.md / StrategyModel.md / Research/Operation guide 等）を参照してください。問題点や質問があればリポジトリの Issue で共有してください。