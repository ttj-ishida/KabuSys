# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ集です。データ取得・ETL・データ品質チェック・マーケットカレンダー管理・ニュース収集・監査ログなど、運用に必要な基盤処理を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は主に以下の目的で設計されています。

- J-Quants API から株価日足、財務データ、JPX マーケットカレンダーを取得して DuckDB に永続化する
- RSS からニュース記事を収集して前処理・冪等保存し、銘柄コードとの紐付けを行う
- ETL パイプライン（差分取得・バックフィル・品質チェック）を提供する
- マーケットカレンダーを管理し、営業日の判定や前後営業日の取得を行う
- 監査ログ（signal → order_request → executions）のスキーマを初期化する
- データ品質チェック（欠損・スパイク・重複・日付不整合）を行う

設計上の注目点:
- レート制限（J-Quants: 120 req/min）を守る固定間隔スロットリング
- リトライ（指数バックオフ、最大 3 回）、401 受信時の自動トークンリフレッシュ
- DuckDB への保存は冪等（ON CONFLICT）を前提
- RSS 収集での SSRF 対策・XML 脆弱性対策・受信サイズ制限
- 品質チェックは Fail-Fast ではなく問題をすべて収集して呼び出し側で判断可能

---

## 主な機能一覧

- 環境設定管理（.env 自動ロード、必須環境変数の取得）
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンによる ID トークン取得）
  - DuckDB への save_* 関数（raw_prices / raw_financials / market_calendar）
- ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl（カレンダー取得 → 株価・財務差分取得 → 品質チェック）
- ニュース収集
  - fetch_rss（RSS 取得・前処理・SSRF/サイズ検査）
  - save_raw_news / save_news_symbols / run_news_collection
  - 銘柄コード抽出（テキスト中の4桁コード・既知コード集合でフィルタ）
- スキーマ管理
  - init_schema（DuckDB のテーブル・インデックスを定義して初期化）
  - init_audit_schema / init_audit_db（監査ログ用スキーマ）
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（夜間バッチで差分更新）
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（まとめ実行）

---

## 前提条件（Prerequisites）

- Python 3.10 以上（型ヒントの union 型表記などを使用）
- 必要なパッケージ（例）:
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

（プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成してアクティベート（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
4. 環境変数を設定する（.env ファイルをプロジェクトルートに置くと自動で読み込まれます）
   - 自動ロードはデフォルトで有効。テスト時などに無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須)
     - SLACK_CHANNEL_ID (必須)
     - DUCKDB_PATH (省略可, デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (省略可, デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live, デフォルト development)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト INFO)

例: .env（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（簡単な例）

以下は Python スクリプトまたは REPL からの利用例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # 親ディレクトリが自動作成されます
```

2) 日次 ETL 実行（J-Quants から差分取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出に用いる 4 桁コードの集合（例: 上場銘柄リスト）
saved_counts = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(saved_counts)
```

4) マーケットカレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("calendar rows saved:", saved)
```

5) 監査スキーマの初期化（監査ログを別 DB に分ける場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

6) 設定値の取得（環境変数を経由）
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
```

注意:
- テスト時に環境自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants へのリクエストはモジュール内で自動的にトークンキャッシュ・リフレッシュを行います。トークン取得に失敗した場合は例外が発生します。

---

## ディレクトリ構成

リポジトリ（src 配下の主要ファイル）:

- src/kabusys/
  - __init__.py                 # パッケージメタデータ（__version__）
  - config.py                   # 環境変数・設定管理（.env 自動ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント・保存ロジック（DuckDB保存）
    - news_collector.py         # RSS ニュース収集・前処理・保存
    - schema.py                 # DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
    - pipeline.py               # ETL パイプライン（差分更新・backfill・品質チェック）
    - calendar_management.py    # マーケットカレンダー管理（営業日判定等）
    - audit.py                  # 監査ログ（signal/order_request/executions）スキーマ
    - quality.py                # データ品質チェック
  - strategy/
    - __init__.py               # （戦略用パッケージプレースホルダ）
  - execution/
    - __init__.py               # （約定／発注用パッケージプレースホルダ）
  - monitoring/
    - __init__.py               # （監視用パッケージプレースホルダ）

この README に書かれていない細かな内部仕様や設計ドキュメントは、コード内のドキュメンテーション文字列（docstring）を参照してください。モジュールごとに詳細な設計コメントが含まれています。

---

## 開発・運用上の注意

- DuckDB への書き込みは多くが ON CONFLICT を利用した冪等実装です。ETL は再実行可能な設計ですが、外部から直接 DB を操作する場合は注意してください。
- news_collector は外部 RSS の内容に依存するため、ネットワーク・XML の攻撃ベクトル（XML Bomb、SSRF）に対策済みですが、運用中も監視が必要です。
- J-Quants API はレート制限があるため、過度な同時実行やループでの短時間連続呼び出しは避けてください。
- 設定は環境変数により切り替え可能です（KABUSYS_ENV）。live モードでは実際の発注などの処理と組み合わせる際に十分な安全対策を実施してください。

---

もし README に追加したいサンプルスクリプト（CLI、定期実行ジョブの systemd/timer / Airflow サンプル等）や、CI/テストの方法、依存管理ファイル（pyproject.toml/requirements.txt）を用意したい場合は、その要件を教えてください。