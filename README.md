# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ（研究・データ基盤・戦略生成・ETL・監査・発注管理のユーティリティ群）。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けにデータ収集（J-Quants）、データベース（DuckDB）での保存・整形、特徴量計算、シグナル生成、および発注/監視に必要なユーティリティをまとめた Python パッケージです。研究（research）で得られたファクターを正規化・合成し、戦略的な売買シグナルの作成や、ニュース収集、マーケットカレンダー管理、ETL パイプライン、監査ログ等を提供します。

設計上のポイント:
- DuckDB をデータ基盤として使用（スキーマ定義・初期化機能を提供）
- J-Quants API 用のクライアント（レート制御・自動リトライ・トークンリフレッシュ）
- 研究用ファクター計算と戦略用の特徴量作成・シグナル生成（ルックアヘッドバイアス対策あり）
- ニュース収集（RSS）と銘柄紐付け
- 冪等（idempotent）な DB 保存ロジック
- 簡易な ETL 実行エントリポイントを提供

---

## 主な機能一覧

- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（無効化可）
  - 必須パラメータチェック

- データ層（kabusys.data）
  - J-Quants クライアント（fetch/save）
  - DuckDB スキーマ定義・初期化（init_schema）
  - ETL パイプライン（run_daily_etl, run_prices_etl, ...）
  - ニュース収集（RSS）と保存（raw_news, news_symbols）
  - マーケットカレンダー管理・営業日判定
  - 統計ユーティリティ（zscore_normalize 等）

- 研究 / 戦略層（kabusys.research / kabusys.strategy）
  - ファクター計算（mom, volatility, value）
  - 特徴量正規化・保存（build_features）
  - シグナル生成（generate_signals）
  - Feature exploration: forward returns, IC, summary

- Execution / 監査（audit）設計
  - トレーサビリティ用テーブル群・DDL（signal_events, order_requests, executions 等）

---

## 前提条件 / 必要環境

- Python 3.10+
- duckdb
- defusedxml

（パッケージのインストールや CI 環境に応じて requirements を用意してください）

---

## インストール

ローカル開発でパッケージ化されている場合:

1. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 開発環境依存パッケージをインストール
   - pip install -r requirements.txt  （requirements.txt があれば）
   - もしくは最小で:
     - pip install duckdb defusedxml

3. パッケージをインストール（ローカル）
   - pip install -e .

（プロジェクトの配布方法に応じて setup/pyproject を利用してください）

---

## 環境変数（.env）

自動でプロジェクトルート（.git または pyproject.toml が見つかる場所）から .env/.env.local を読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（Settings によって参照されるもの）:

- JQUANTS_REFRESH_TOKEN: J‑Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

簡易の .env.example:

JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（DB 初期化の例）

1. 環境変数を用意（.env）
2. Python REPL またはスクリプトから DuckDB スキーマを初期化

サンプルスクリプト:

from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Path を返します
conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection。以降 ETL / クエリに使用できます。

init_schema は指定した DuckDB ファイルに対して全テーブルを作成します（冪等）。

---

## 使い方（主要ユースケース）

以下は代表的な操作のコード例です。各モジュールの関数はドキュメント文字列に詳細があります。

1) 日次 ETL の実行（市場カレンダー・株価・財務の差分取得と品質チェック）:

from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

2) 特徴量作成（features テーブルへ保存）:

from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {count}")

3) シグナル生成（signals テーブルへ保存）:

from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
n = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals written: {n}")

4) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）:

from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes: 有効銘柄コードのセットを渡すと自動抽出して紐付けします
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)

5) カレンダー更新バッチ:

from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")

注意点:
- 各処理は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。init_schema は DB を作成して接続を返し、get_connection は既存 DB に接続します。
- J-Quants API を利用する処理は JQUANTS_REFRESH_TOKEN が必須です。
- 自動保存関数（save_*）は冪等（ON CONFLICT ... DO UPDATE / DO NOTHING）になっており再実行に耐えます。

---

## ログ / 実行環境

- KABUSYS_ENV により is_dev / is_paper / is_live を切り替えられます。
  - development / paper_trading / live のいずれかを設定してください。
- LOG_LEVEL でログレベルを制御できます（INFO デフォルト）。

---

## ディレクトリ構成

リポジトリの主要なファイル/ディレクトリ概要（抜粋）:

src/
  kabusys/
    __init__.py                 # パッケージ初期化（__version__ 等）
    config.py                   # 環境設定管理
    data/
      __init__.py
      jquants_client.py         # J-Quants API クライアント（fetch/save）
      news_collector.py         # RSS ニュース収集
      schema.py                 # DuckDB スキーマ定義・初期化
      pipeline.py               # ETL パイプライン（run_daily_etl 等）
      stats.py                  # 統計ユーティリティ（zscore_normalize）
      features.py               # features 公開インターフェース
      calendar_management.py    # マーケットカレンダー管理
      audit.py                  # 監査ログ用 DDL（signal_events / executions 等）
      ...                       # その他データ用モジュール
    research/
      __init__.py
      factor_research.py        # ファクター計算（momentum/value/volatility）
      feature_exploration.py    # IC / forward returns / summary
    strategy/
      __init__.py
      feature_engineering.py    # features を作成する build_features
      signal_generator.py       # generate_signals（BUY/SELL判定）
    execution/
      __init__.py               # 発注層（スケルトン）
    monitoring/                 # 監視・メトリクス用（SQLite 等を想定）
      ...
    data/                       # (パッケージ内) data 関連
    research/                   # research helper
    strategy/                   # strategy helper

各モジュールは docstring に詳細な設計方針・仕様を記載しています。関数毎の引数・戻り値はソース上の docstring を参照してください。

---

## 開発・テスト時のヒント

- .env 読み込みを無効化したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB の一時的なインメモリ実行:
  - init_schema(":memory:")
- J-Quants の API 呼び出しはレート制限・リトライ・トークン自動更新を組み込んでいるため、テスト時は id_token を直接注入してモックする（関数引数 id_token を利用）。

---

## 参照 / 追加ドキュメント

本コードベースは内部で以下の設計文書を参照する実装になっています（リポジトリに同梱されている想定）:
- DataPlatform.md
- StrategyModel.md
- その他設計ドキュメント

これらを参照するとアルゴリズムの背景やパラメータの由来が理解しやすくなります。

---

もし README に追加してほしい実行例（CLI スクリプト、Docker、CI 用のセットアップ）や、.env の具体的なテンプレート、ユニットテストの実行方法などがあれば教えてください。必要に応じて追記します。