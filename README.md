# KabuSys

日本株向けの自動売買・データ基盤ライブラリ / フレームワークです。  
Data（DuckDBベース）とResearch（ファクター計算）、ETL、ニュース収集、J-Quants APIクライアント、監査ログスキーマなどを提供します。

---

## 概要

KabuSys は以下を目的としたモジュール群を含むパッケージです。

- J-Quants API からの市場データ / 財務データ / カレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution 層）と初期化ユーティリティ
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集（SSRF対策・トラッキングパラメータ除去・冪等保存）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー 等）、IC 計算、統計ユーティリティ
- マーケットカレンダー管理、監査ログ（トレーサビリティ）スキーマ

パッケージは本番口座の発注処理等にアクセスするモジュール（execution/strategy 等）を想定していますが、提示されたコードでは主に Data / Research / ETL に重点を置いています。

---

## 主な機能一覧

- 環境変数管理（.env/.env.local 自動ロード、必須変数チェック）
- J-Quants API クライアント
  - ページネーション対応、レートリミット制御、再試行（指数バックオフ）、401 時の自動トークンリフレッシュ
  - fetch/save の冪等処理（DuckDB への ON CONFLICT 更新）
- ETL パイプライン
  - 市場カレンダー / 株価日足 / 財務データの差分更新（バックフィル対応）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）
  - URL 正規化、トラッキングパラメータ除去、SSRF 対策、gzip 制限、記事ID ハッシュ化、冪等保存
  - 銘柄コード抽出と news_symbols への紐付け
- DuckDB スキーマ初期化（init_schema）
- 監査ログ（order_requests / executions / signal_events 等）の初期化（init_audit_schema / init_audit_db）
- Research
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials に基づく）
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（data.stats）

---

## 要件

- Python 3.9+
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml

（実行環境により追加ライブラリが必要になる場合があります）

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # UNIX
3. 必要パッケージをインストール（例）
   pip install duckdb defusedxml
   # 追加で HTTP クライアントやテストツールを入れること

4. 環境変数を準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的にロードされます（読み込み優先度: OS環境 > .env.local > .env）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. .env に最低限必要な値（例）
   JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   KABU_API_PASSWORD=<kabu_api_password>
   SLACK_BOT_TOKEN=<slack_bot_token>
   SLACK_CHANNEL_ID=<slack_channel_id>
   # 任意:
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

注意: Settings クラスは必須環境変数が未設定の場合 ValueError を送出します。

---

## 使い方（代表的な例）

以下は基本的な利用フローのサンプルコード例です。

- DuckDB スキーマ初期化（ETL 前に実行）

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 監査ログ専用 DB 初期化

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- 日次 ETL の実行

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- News（RSS）収集ジョブ実行（既知銘柄コードを渡して紐付けを行う例）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(result)
```

- Research: モメンタム等の計算例

```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 31)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# Zスコア正規化例
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- J-Quants API からデータを直接フェッチして保存する例

```python
from kabusys.data import jquants_client as jq
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

---

## 設定項目（主要な環境変数）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベースURL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化するには 1 を設定

Settings で未設定の必須変数にアクセスすると ValueError が発生します。

---

## ディレクトリ構成

（主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    # 環境変数・設定管理 (.env 自動ロード / Settings)
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント（fetch / save）
    - news_collector.py         # RSS ニュース収集・前処理・DB保存
    - schema.py                 # DuckDB スキーマ定義・init_schema / get_connection
    - stats.py                  # 統計ユーティリティ（zscore_normalize）
    - pipeline.py               # ETL パイプライン / run_daily_etl 等
    - features.py               # features 公開インターフェース（zscore 再エクスポート）
    - calendar_management.py    # マーケットカレンダー管理（is_trading_day 等）
    - audit.py                  # 監査ログスキーマ（signal_events / order_requests / executions）
    - etl.py                    # ETL 公開インターフェース（ETLResult 再エクスポート）
    - quality.py                # 品質チェック（欠損・スパイク・重複・日付整合性）
  - research/
    - __init__.py               # 研究用ユーティリティの公開
    - feature_exploration.py    # 将来リターン計算・IC・統計サマリー
    - factor_research.py        # モメンタム/ボラティリティ/バリュー計算
  - strategy/                    # 戦略関連（未実装のエントリ）
    - __init__.py
  - execution/                   # 発注・ブローカー接続（未実装のエントリ）
    - __init__.py
  - monitoring/                  # モニタリング（未実装のエントリ）
    - __init__.py

---

## 開発・運用時の注意点

- DuckDB の SQL 実行ではパラメータバインド（?）を多用しており、SQL インジェクションリスクは低く設計されていますが、外部データの取り扱いには注意してください。
- RSS の取得は SSRF 対策を施していますが、外部 URL 取得時のタイムアウトやレスポンスサイズ上限（10MB）などが設定されています。
- J-Quants API はレート制限（120 req/min）を守るため内部にスロットリングがあります。大量取得時は時間がかかることに注意してください。
- ETL は各ステップでエラーをハンドリングし続行する設計（Fail-Fast ではない）です。result の quality_issues / errors を確認して運用判断してください。
- 本番環境（KABUSYS_ENV=live）での実行前に、paper_trading 環境で十分な検証を行ってください。

---

## 参考

- 設定管理: src/kabusys/config.py（.env パーサ実装、優先順位、保護キー）
- スキーマ / 初期化: src/kabusys/data/schema.py（init_schema, get_connection）
- ETL 実行: src/kabusys/data/pipeline.py（run_daily_etl 等）
- J-Quants クライアント: src/kabusys/data/jquants_client.py（fetch_*/save_*）
- ニュース収集: src/kabusys/data/news_collector.py
- 研究関連: src/kabusys/research/*.py

---

必要があれば README にサンプル .env.example、より詳細な API 使用例（fetch のページネーション・id_token 注入やテストのためのフック）、または CI / デプロイ手順を追加できます。どの情報を優先して追加しますか？