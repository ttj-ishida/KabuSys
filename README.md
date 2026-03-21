# KabuSys

KabuSys は日本株を対象とした自動売買基盤のコアライブラリです。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査用スキーマなどを含むモジュール群を提供します。主に研究環境（Research）と本番実行（Execution）を分離した設計になっており、DuckDB をデータストアとして利用します。

## 主な特徴（機能一覧）
- データ取得
  - J-Quants API クライアント（株価日足 / 財務 / 市場カレンダー）
  - RSS ベースのニュース収集（SSRF/サイズ上限/トラッキング除去）
- ETL（kabusys.data.pipeline）
  - 差分取得、バックフィル、品質チェック連携
  - 日次 ETL ジョブ（market_calendar、prices、financials の差分取得）
- スキーマ / データベース
  - DuckDB ベースの多層スキーマ（raw / processed / feature / execution）
  - スキーマ初期化ユーティリティ（冪等）
- 研究（research）
  - ファクター計算 (momentum / volatility / value)
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 特徴量エンジニアリング（strategy.feature_engineering）
  - 複数ソースのファクターを正規化・フィルタ・保存
- シグナル生成（strategy.signal_generator）
  - 正規化ファクターと AI スコアを統合し BUY/SELL シグナルを生成
  - Bear レジーム抑制、エグジット（ストップロス等）
- 監査（data.audit）
  - シグナル→発注→約定をトレースする監査ログ用テーブル群
- 汎用ユーティリティ
  - 統計ユーティリティ（z-score 正規化 等）
  - マーケットカレンダー管理（営業日判定 / 翔日探索）

## セットアップ手順

前提
- Python 3.10+（型ヒントで Union/| が使われているため）
- DuckDB が利用可能（Python パッケージとしてインストールされます）

1. リポジトリをクローンして仮想環境を作成
```bash
git clone <repo-url>
cd <repo-root>
python -m venv .venv
source .venv/bin/activate
pip install -U pip setuptools
```

2. 依存パッケージをインストール
（requirements ファイルがない場合は最低限以下をインストールしてください）
```bash
pip install duckdb defusedxml
```
※ 実際のプロジェクトでは requirements.txt / pyproject.toml に依存解決を含めてください。

3. 環境変数の準備
プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション等の API パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN: Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）。デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. データベーススキーマ初期化
最初に DuckDB スキーマを作成します（親ディレクトリ自動作成あり）。
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

## 基本的な使い方（簡易例）

以下は代表的な処理の実行例です。実行は Python スクリプトや CLI ラッパーから呼び出します。

- 日次 ETL（市場カレンダー・株価・財務を差分取得）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量（features）作成（ある target_date に対して）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
count = build_features(conn, target_date=date(2024, 1, 1))
print(f"features built: {count}")
```

- シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
signals_count = generate_signals(conn, target_date=date(2024, 1, 1))
print(f"signals written: {signals_count}")
```

- ニュース収集ジョブ（RSS -> raw_news + news_symbols）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes: 抽出に使う有効な銘柄コードセット（例: 全上場銘柄コード）
known_codes = {"7203", "6758", "9432"}  # 実運用ではリストを用意
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

注意:
- 上記の ETL / news collector / jquants_client はネットワークアクセス・API トークンを必要とします。
- 実運用ではログ設定、例外ハンドリング、リトライ戦略やジョブスケジューラ（cron / Airflow 等）との統合を行ってください。

## ディレクトリ構成（主要ファイル）
以下はソースツリー（src/kabusys）の主要ファイルと役割のサマリです。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理（自動 .env 読み込み、必須キー取得）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（rate limiting, retry, token refresh）
    - news_collector.py
      - RSS ニュースの取得、正規化、DB 保存、銘柄抽出
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - features.py
      - data.stats の再エクスポート
    - calendar_management.py
      - market_calendar 管理・判定ユーティリティ
    - audit.py
      - 発注/約定の監査ログ定義
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value ファクター計算
    - feature_exploration.py
      - 将来リターン、IC、統計サマリ等
  - strategy/
    - __init__.py
    - feature_engineering.py
      - 生ファクターの正規化・ユニバースフィルタ・features への保存
    - signal_generator.py
      - final_score 計算、BUY/SELL シグナル生成、signals テーブルへの保存
  - execution/
    - __init__.py
    - （発注連携・execution 層は拡張ポイント）
  - monitoring/
    - （監視・アラート用モジュール。今回は空のパッケージ）

## 設計上の注意点 / ヒント
- ルックアヘッドバイアス対策
  - 各モジュールは target_date 時点で利用可能なデータのみを参照する設計です（ETL の fetched_at や prices の最終日処理に注意）。
- 冪等性
  - DB への保存は多くが ON CONFLICT で冪等化されています。ETL の再実行が可能です。
- 環境変数自動ロード
  - config.py はプロジェクトルートの `.env` / `.env.local` を自動で読み込みます。テスト等でこれを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれかでなければなりません。
- ロギング・モニタリングはプロジェクト要件に合わせて設定してください（LOG_LEVEL 等）。

## テスト・開発
- 単体テストは各モジュールのネットワーク依存箇所（jquants_client.fetch_*、news_collector._urlopen など）をモックして行うことを推奨します。
- DuckDB のインメモリ接続（":memory:"）を使えばスキーマ初期化→処理検証が高速に行えます。
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  ```

---

この README はライブラリの概要と基本的な使い方をまとめたものです。運用・デプロイ・監視、証券会社 API 連携（発注ロジック）等は別途実装・運用設計が必要です。README の補足や CLI / サンプルスクリプトの追加が必要であれば教えてください。