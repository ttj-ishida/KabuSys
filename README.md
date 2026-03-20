# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（データパイプライン・ファクター計算・シグナル生成・ニュース収集・監査等）。  
このリポジトリは DuckDB を中心に、J-Quants API からのデータ取得・保存、特徴量生成、シグナル生成、ニュース収集／銘柄紐付け、マーケットカレンダー管理、監査ログなどの機能を提供します。

---

## プロジェクト概要

KabuSys は主に次の層で構成されています。

- Data Layer（data/）: J-Quants API クライアント、ETL パイプライン、ニュース収集、DuckDB スキーマ定義、統計ユーティリティ
- Research Layer（research/）: ファクター計算、特徴量探索（IC/forward returns 等）
- Strategy Layer（strategy/）: 特徴量正規化・合成（features 作成）、最終スコア計算・シグナル生成
- Execution / Monitoring（execution/, monitoring/）: 発注・監視に関する土台（本リポジトリでは基盤コードを提供）

設計上のポイント：
- ルックアヘッドバイアスを避けるため、各処理は target_date 時点のデータのみを使用
- DuckDB を使ったローカル永続化。ETL は冪等（ON CONFLICT / upsert）設計
- 外部依存は最小限（duckdb, defusedxml 等）で、標準ライブラリ中心の実装

---

## 主な機能一覧

- J-Quants API クライアント（data/jquants_client.py）
  - 日足（OHLCV）、財務データ、マーケットカレンダー取得（ページネーション／リトライ／レート制御）
  - 保存用ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）
- DuckDB スキーマ定義・初期化（data/schema.py）
- ETL パイプライン（日次 ETL、差分取得、バックフィル、品質チェック呼び出し）(data/pipeline.py)
- ニュース収集（RSS 収集、HTML除去・正規化、記事ID生成、raw_news 保存、銘柄抽出）(data/news_collector.py)
- マーケットカレンダー管理（営業日判定、next/prev trading day、夜間更新ジョブ）(data/calendar_management.py)
- 研究用ファクター計算（momentum / volatility / value）(research/factor_research.py)
- 特徴量作成（Zスコア正規化・ユニバースフィルタ・features テーブルへの upsert）(strategy/feature_engineering.py)
- シグナル生成（複数コンポーネントの重み付け合算、Bear レジーム抑制、BUY/SELL 判定、signals テーブルへの upsert）(strategy/signal_generator.py)
- 統計ユーティリティ（zscore_normalize 等）(data/stats.py)
- 監査ログのためのスキーマ（audit.py）など

---

## 必要環境 / 依存

- Python 3.9+
- 必要パッケージ（例）
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 開発時はパッケージを editable install する場合
pip install -e .
```

（プロジェクトに pyproject.toml / setup.py があれば pip install -e . を使用してください）

---

## 環境変数（設定）

KabuSys は .env / .env.local もサポートしており、プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から自動で読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数（必須）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）

その他（任意・デフォルトあり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視等で使用する SQLite パス（デフォルト: data/monitoring.db）

例 .env:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（最小構成）

1. リポジトリをクローンして仮想環境・依存をインストール
2. .env を作成して必要な環境変数を設定
3. DuckDB スキーマ初期化

Python REPL またはスクリプト例:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH のデフォルトを利用
conn = init_schema(settings.duckdb_path)
print("DuckDB initialized at:", settings.duckdb_path)
```

これで基本的なテーブルが作成されます（冪等）。

---

## 使い方（主要なユースケース）

以下に主要 API の簡単な使用例を示します。各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。

- 日次 ETL（市場カレンダー・日足・財務の差分取得と保存）

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())
```

- 特徴量の構築（features テーブル作成）

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection(settings.duckdb_path)
n = build_features(conn, target_date=date(2024, 1, 5))
print(f"features upserted: {n}")
```

- シグナル生成（signals テーブル作成）

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection(settings.duckdb_path)
count = generate_signals(conn, target_date=date(2024, 1, 5))
print(f"signals written: {count}")
```

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）

```python
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection(settings.duckdb_path)
# known_codes は既知の銘柄コードセット（文字列4桁）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ（夜間バッチ）

```python
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print("calendar rows saved:", saved)
```

---

## ロギングとデバッグ

モジュールは標準ライブラリ logging を利用しています。開発中は以下のようにログレベルとハンドラを設定して詳細を確認してください。

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

環境変数 `LOG_LEVEL` を設定することで設定クラス経由でも制御できます。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
- config.py — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント & 保存ユーティリティ
  - schema.py — DuckDB スキーマ定義 / init_schema / get_connection
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - news_collector.py — RSS 取得・raw_news 保存・銘柄抽出
  - calendar_management.py — market_calendar 管理 / 営業日ユーティリティ
  - audit.py — 監査ログスキーマ
  - stats.py — zscore_normalize 等汎用統計関数
  - features.py — public re-export（zscore_normalize）
- research/
  - __init__.py
  - factor_research.py — momentum / volatility / value の計算
  - feature_exploration.py — forward returns / IC / summary 等
- strategy/
  - __init__.py
  - feature_engineering.py — features 作成（正規化 / ユニバースフィルタ）
  - signal_generator.py — final_score 計算・BUY/SELL 判定
- execution/ — 発注実装用プレースホルダ（将来的に broker 接続等を実装）
- monitoring/ — 監視関連（未展開の機能）

---

## 注意事項 / ベストプラクティス

- production（live）環境では KABUSYS_ENV=live を設定し、設定値を厳格に管理してください。
- J-Quants の API レート制限や認証仕様に従ってください。jquants_client にはリトライ／レート制御の実装がありますが、長時間のバッチでは注意が必要です。
- DuckDB のバックアップとファイルローテーションを検討してください（データ量が増えるとファイルサイズが大きくなります）。
- ニュース収集は外部 URL を扱うため、SSRF 対策や XML の安全なパース（defusedxml を使用）を行っています。外部フィードの追加は既存の制約に従ってください。
- 本リポジトリは「戦略の計算とシグナル生成」までを提供し、実際の発注実行（ブローカ接続）を行う場合は execution 層での追加実装や十分なテストが必要です。

---

必要に応じて README を拡張（運用手順、cron/CI ジョブ例、監査ログのクエリ例、品質チェックの詳細など）します。特にどの部分を詳しく書いてほしいか指示いただければ追記します。