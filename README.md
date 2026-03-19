# KabuSys

KabuSys は日本株自動売買プラットフォーム向けのライブラリ群です。データ収集（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、監査ログ／スキーマ管理などを一貫して提供します。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 簡単な使い方
- 環境変数
- ディレクトリ構成
- 補足・設計方針の抜粋

---

## プロジェクト概要
KabuSys は DuckDB をバックエンドに用いた日本株向けのデータプラットフォーム兼戦略実行スタックです。  
主に次の領域をカバーします。

- J-Quants API を利用した株価・財務データ・市場カレンダーの取得（レート制御・リトライ・トークン自動更新）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- DuckDB スキーマ定義と初期化
- 研究用ファクター計算（Momentum / Value / Volatility 等）
- 特徴量正規化・統合（features テーブルへの保存）
- シグナル生成（最終スコア計算、BUY / SELL 判定）
- RSS ベースのニュース収集と銘柄紐付け
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計ではルックアヘッドバイアス防止、冪等性（DB の ON CONFLICT ロジック等）、外部 API に対する堅牢なエラーハンドリングを重視しています。

---

## 主な機能一覧
- data/jquants_client.py: J-Quants API クライアント（レートリミット・リトライ・自動トークン更新）
- data/schema.py: DuckDB のテーブル定義と初期化（Raw / Processed / Feature / Execution 層）
- data/pipeline.py: ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- data/news_collector.py: RSS 収集・正規化・raw_news 保存・銘柄抽出
- data/calendar_management.py: 市場カレンダー管理／営業日判定ユーティリティ
- research/factor_research.py: モメンタム・ボラティリティ・バリュー等ファクター計算
- research/feature_exploration.py: 将来リターン計算・IC（Spearman）・統計サマリー
- strategy/feature_engineering.py: ファクター統合・Z スコア正規化・features テーブルへの書き込み
- strategy/signal_generator.py: final_score 計算、BUY/SELL シグナル生成、signals テーブルへの保存
- data/stats.py: 共通の統計ユーティリティ（zscore_normalize）
- config.py: .env または環境変数からの設定読み込み（自動 .env ロードをサポート）

---

## セットアップ手順

前提:
- Python 3.8+（ソースは typing | None 型ヒント等を使用）
- 必要なライブラリ: duckdb, defusedxml など（プロジェクトで使用されるもの）

例（仮の requirements がない場合の最小インストール例）:

1. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
   - pip install duckdb defusedxml

   ※プロジェクトで追加依存がある場合は requirements.txt を参照してインストールしてください。

3. パッケージを開発インストール（任意）
   - pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を配置して必要な値を設定してください。
   - 自動ロードは config._find_project_root() によりプロジェクトルート（.git または pyproject.toml）を探し、`.env` → `.env.local` の順で読み込みます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB スキーマの初期化（例）
   - Python REPL やスクリプトから:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
   - デフォルトの DB パスは `data/kabusys.duckdb`（settings.duckdb_path）

---

## 簡単な使い方（サンプル）

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL 実行（J-Quants から差分取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量構築（features テーブルの作成）
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4) シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals generated: {count}")
```

5) ニュース収集ジョブ（RSS 取得 → DB 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection, init_schema
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes は既知の銘柄コードセット（例: prices_daily などから抽出）
known_codes = {"7203", "6758", ...}
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)
```

注意:
- 上記は最小の実行例です。実稼働ではログ設定・エラーハンドリング・監査ログの整備・発注層との統合が必要です。

---

## 環境変数（設定項目）

config.Settings によりアクセスされる主要な環境変数一覧:

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live。デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL。デフォルト: INFO)

自動 .env ロードの制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 に設定すると自動で .env ファイルを読み込まなくなります（テスト用等）。

.env ファイルはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から読み込まれます。`.env.local` は `.env` を上書きする形で優先的に読み込まれます。

---

## ディレクトリ構成（主なファイル）
（リポジトリのルートが `src/` 配下にある構成を想定）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント（レート制御・リトライ）
    - news_collector.py       -- RSS ニュース収集／前処理／DB 保存
    - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
    - schema.py               -- DuckDB スキーマ定義と init_schema
    - stats.py                -- 汎用統計ユーティリティ（zscore_normalize）
    - features.py             -- data.stats の再エクスポート
    - calendar_management.py  -- 市場カレンダー管理ユーティリティ
    - audit.py                -- 監査ログの DDL（signal_events / order_requests / executions 等）
    - ...（その他データ層ユーティリティ）
  - research/
    - __init__.py
    - factor_research.py      -- ファクター（momentum / volatility / value）
    - feature_exploration.py  -- IC / forward_returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py  -- features の構築（正規化・ユニバースフィルタ）
    - signal_generator.py     -- final_score 計算・シグナル生成
  - execution/                -- 発注層（プレースホルダ / 将来的な実装）
  - monitoring/               -- 監視・モニタリング（DB: monitoring.db など）

---

## 補足・設計方針（抜粋）
- ルックアヘッドバイアス防止: ファクター・シグナル計算は target_date 時点で利用可能なデータのみを参照します。
- 冪等性: データ保存関数は ON CONFLICT / DO UPDATE や INSERT ... ON CONFLICT DO NOTHING を使用し、複数実行時の二重登録を防ぎます。
- エラーハンドリング: ETL は各ステップ毎に独立してエラーハンドリングを行い、1 ステップの失敗で全体が停止しないよう設計されています。
- セキュリティ: news_collector では SSRF 対策（スキーム検証、プライベートIP拒否）、defusedxml による XML パース保護、最大レスポンスサイズ制限などを行っています。
- J-Quants クライアントはレート制御とリトライ、401 の場合のトークン自動更新などを備えます。

---

README では主要な使用例と設定の要点を示しました。実運用ではログ設定、監査ログの有効化、発注層（execution）の実装、安全なキー管理（シークレット管理サービスの利用推奨）、テスト・CI を整備してください。必要であればサンプルスクリプトや運用フロー（cron / Airflow 等）向けの追加ドキュメントを作成します。