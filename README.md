# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）のリポジトリ向け README。  
本ドキュメントはソースコード（src/kabusys 以下）の実装に基づいて作成しています。

## プロジェクト概要

KabuSys は日本株のデータ取得・ETL・特徴量生成・シグナル生成・監査までをカバーする自動売買基盤のライブラリ群です。主に以下の層を提供します。

- Data（J-Quants からの株価・財務・カレンダー・ニュース取得と DuckDB への保存）
- Research（ファクターの計算・特徴量探索・統計ユーティリティ）
- Strategy（特徴量の正規化・シグナル生成ロジック）
- Execution（発注・約定・ポジション管理のためのスキーマ／インタフェース）
- Monitoring（監視・アラート関連モジュール — ディレクトリは存在）

設計上のポイント:
- DuckDB をデータレイヤに採用（ローカルでの分析/ETL に最適）
- J-Quants API 利用（レート制限とリトライ、トークン自動更新を実装）
- ルックアヘッドバイアス対策を重視（「対象日時点で利用可能なデータのみ」を前提）
- 冪等性を重視した DB 書き込み（ON CONFLICT / トランザクション利用）
- 外部ライブラリ依存を最小化（ただし duckdb、defusedxml 等は利用）

## 主な機能一覧

- J-Quants クライアント（data/jquants_client.py）
  - 日足取得 / 財務データ / 市場カレンダーの取得（ページネーション・リトライ・レート制御）
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）
- ETL パイプライン（data/pipeline.py）
  - 差分取得、バックフィル、品質チェック、日次 ETL の統合 run_daily_etl
- スキーマ定義・初期化（data/schema.py）
  - raw / processed / feature / execution 層のテーブル定義・インデックス
  - init_schema() による初期化
- ニュース収集（data/news_collector.py）
  - RSS フェッチ、前処理、raw_news 保存、銘柄抽出（SSRF 対策・サイズ制限等）
- 研究系ユーティリティ（research/）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量エンジニアリング（strategy/feature_engineering.py）
  - research が計算した raw ファクターの統合、ユニバースフィルタ、Z スコア正規化、features への UPSERT
- シグナル生成（strategy/signal_generator.py）
  - 正規化済み特徴量と AI スコアを統合して final_score を算出
  - Bear レジーム判定、BUY / SELL シグナル生成、signals テーブルへの保存
- マーケットカレンダー管理、監査ログテーブル等

## 必要環境（推奨）

- Python 3.10 以上（パイプライン内での型注記 "X | None" を使用）
- 必要なライブラリ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリ：urllib、datetime、logging 等

インストール例（仮想環境を推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# プロジェクトを editable インストール可能であれば:
# pip install -e .
```

プロジェクトに requirements.txt / packaging がある場合はそちらを参照してください。

## セットアップ手順

1. リポジトリをチェックアウト
2. 仮想環境作成・依存インストール（上記参照）
3. 環境変数の準備（.env または OS 環境変数）
   - プロジェクトルート（.git または pyproject.toml のあるフォルダ）に `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
4. DuckDB スキーマの初期化（例はデフォルトパス data/kabusys.duckdb）
```bash
python - <<'PY'
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
print("schema initialized")
PY
```

## 環境変数（主なもの）

config.Settings で利用される主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、監視用 DB デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意、development | paper_trading | live、デフォルト: development)
- LOG_LEVEL (任意、DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意、1 をセットすると自動 .env ロードを無効化)

未設定の必須変数にアクセスすると ValueError が発生します（settings.jquants_refresh_token 等）。

## 使い方（代表的な操作）

以下は簡単な Python スニペット例です。実運用ではスクリプト化・ジョブ化してください。

- DuckDB 接続とスキーマ初期化
```python
from kabusys.data.schema import init_schema, get_connection
conn = init_schema("data/kabusys.duckdb")  # 初回は init_schema
# 既存 DB に接続する場合:
# conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL 実行（J-Quants トークンは settings から自動取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 引数で target_date, id_token 等を指定可
print(result.to_dict())
```

- ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
conn = init_schema("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使う銘柄コードセット（例: set of "7203","6758"...）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(res)
```

- 特徴量の構築（features テーブルへの書き込み）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date
conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, date(2024, 1, 31))
print(f"features upserted: {n}")
```

- シグナル生成（signals テーブルへの書き込み）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date
conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, date(2024, 1, 31), threshold=0.6)
print(f"signals written: {count}")
```

- カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- スキーマ／監査関連：`kabusys.data.audit`、`kabusys.data.schema` を参照して監査ログや発注要求を記録できます。

注意:
- 各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。
- ETL や保存関数は冪等設計（既存行は更新）です。
- 実際のブローカー発注連携や Slack 通知等は別レイヤで接続する想定です（設定情報は Settings 経由で取得）。

## ディレクトリ構成

（src/kabusys 以下の主要ファイル一覧）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント + 保存処理
    - news_collector.py     — RSS ニュース収集・前処理・保存
    - schema.py             — DuckDB スキーマ定義・初期化
    - stats.py              — zscore_normalize 等統計ユーティリティ
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - features.py           — data.stats の再エクスポート
    - calendar_management.py— カレンダー管理ユーティリティ
    - audit.py              — 監査ログ用 DDL / 初期化補助（監査テーブル）
    - (他: quality 等が参照される想定)
  - research/
    - __init__.py
    - factor_research.py    — momentum/volatility/value の計算
    - feature_exploration.py— 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py— features の構築（正規化・フィルタ）
    - signal_generator.py   — final_score 計算と BUY/SELL シグナル生成
  - execution/
    - __init__.py           — 発注・約定・ポジション管理のためのパッケージ（実装拡張対象）
  - monitoring/
    - (監視・アラート関連の実装置き場)

※ 実際のリポジトリにはさらにユーティリティやテストファイル、ドキュメントが含まれる可能性があります。

## 運用上の注意 / 実装上のポイント

- settings は必須環境変数の未設定で例外を投げます。運用前に .env を用意してください。
- J-Quants API 呼び出しはレート制限を守るよう実装されていますが、複数プロセスから同時に大量呼び出しを行うとレートを超える恐れがあります。
- ニュース収集では SSRF / XML BOM / gzip 膨張攻撃対策を実装していますが、外部フィードの取り扱いには注意してください。
- シグナル生成は features と ai_scores を参照します。AI スコアが無い場合も中立値で扱うため動作は継続します。
- DuckDB のバージョンや機能差により外部キーや ON DELETE の挙動が異なるため、DDL 内に注釈があります（DuckDB の制限に対応）。

---

この README はソースコードの現状に基づいた概要・使い方の抜粋です。詳細な仕様（StrategyModel.md / DataPlatform.md / Research ドキュメント等）がプロジェクトに含まれている場合はそちらを参照してください。追加で具体的な実行スクリプト例、CI 設定、運用手順（cron / Airflow / Airbyte 等）を記載することもできます。必要でしたら追記します。