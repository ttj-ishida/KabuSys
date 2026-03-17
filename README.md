# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得（J-Quants、RSS）、ETL、データ品質チェック、DuckDB スキーマ、監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なデータ基盤と補助ライブラリを集めた Python パッケージです。主に次を提供します。

- J-Quants API 経由での株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- RSS からのニュース収集と記事の正規化・保存（SSRF対策・サイズ制限・トラッキングパラメータ除去）
- DuckDB ベースのスキーマ定義および初期化ユーティリティ
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- 市場カレンダー管理（営業日判定、前後営業日探索、夜間更新ジョブ）
- 監査ログ（シグナル〜発注〜約定のトレース可能なテーブル群）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

設計上のポイント：
- API レート制限と再試行（指数バックオフ）を実装
- 冪等な DB 操作（ON CONFLICT 等）
- セキュリティ対策（XML 脆弱性、SSRF、レスポンスサイズ上限）
- 品質チェックは Fail-Fast ではなく検出結果を返す設計

---

## 主な機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ保存する save_* 関数（冪等）
  - レートリミッタ・リトライ・401 自動リフレッシュ対応
- data.news_collector
  - RSS フィード取得（gzip対応）と記事前処理
  - URL 正規化（utm 等除去）・記事ID生成（SHA-256 一部）
  - SSRF 対策（リダイレクト時の検証、プライベートIP拒否）
  - raw_news / news_symbols テーブルへの冪等保存
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) でテーブル・インデックスを作成
- data.pipeline
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック（差分取得・バックフィル）
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job: 夜間で JPX カレンダーを更新
- data.audit
  - 監査用テーブル（signal_events, order_requests, executions）と初期化ユーティリティ
- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- config
  - 環境変数読み込み（.env / .env.local 自動読み込み、無効化フラグあり）
  - Settings クラスで設定値を取得（必須変数は例外）

空のパッケージプレースホルダ:
- execution, strategy, monitoring（将来的な拡張用）

---

## セットアップ手順

前提：
- Python 3.9+（型アノテーションの Union 代替や pathlib を利用）
- pip が利用可能

1. リポジトリをチェックアウト
   - git clone ...（省略）

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）
   - pip install -e .  （パッケージを編集可能モードでインストールする場合）

4. 環境変数 / .env の準備
   - ルート（.git または pyproject.toml があるディレクトリ）に .env または .env.local を配置すると自動読み込みされます。
   - 自動読み込みを無効にする場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

必須の主な環境変数（Settings 参照）:
- JQUANTS_REFRESH_TOKEN         （必須）J-Quants リフレッシュトークン
- KABU_API_PASSWORD            （必須）kabuステーション API パスワード
- SLACK_BOT_TOKEN              （必須）Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID             （必須）Slack チャネル ID

任意 / デフォルト:
- KABUSYS_ENV                  デフォルト "development"（有効値: development, paper_trading, live）
- LOG_LEVEL                    デフォルト "INFO"（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUS_API_BASE_URL           デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH                  デフォルト "data/kabusys.duckdb"
- SQLITE_PATH                  デフォルト "data/monitoring.db"

例 .env（ルートに配置）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

注意:
- config モジュールは .git / pyproject.toml を基準にプロジェクトルートを自動判定して .env をロードします（CWD に依存しない）。
- OS 環境変数が優先され、.env.local は .env を上書きします。

---

## 使い方（サンプル）

以下は典型的な操作例です。実行はプロジェクトルートから行ってください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイルDB を初期化（親ディレクトリがなければ自動作成）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（株価・財務・カレンダー取得＋品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) RSS ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット（例）
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

4) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

5) J-Quants の id_token を明示的に取得
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()
```

6) 監査ログスキーマの初期化（監査テーブルのみ）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

ログ出力の制御:
- LOG_LEVEL 環境変数でログレベルを設定します。

注意点（運用上の留意事項）:
- J-Quants API のレート制限（120 req/min）を尊重する仕組みを組み込んでいますが、並列で大量のリクエストを発生させると制限に抵触する可能性があります。
- ETL は差分更新・バックフィル方式です。初回ロードはデータ量が大きくなる可能性があります。
- news_collector は外部 URL を扱うため SSRF 対策やサイズチェックを実装しています。テスト時は _urlopen をモックして差し替え可能です。

---

## ディレクトリ構成

主要なファイルとモジュールの構成は以下の通りです（src/kabusys 下）:

- kabusys/
  - __init__.py         (パッケージ定義、__version__)
  - config.py           (環境変数 / Settings)
  - data/
    - __init__.py
    - jquants_client.py  (J-Quants API クライアント、保存ロジック)
    - news_collector.py  (RSS 収集、前処理、保存)
    - schema.py          (DuckDB スキーマ定義・init_schema)
    - pipeline.py        (ETL パイプライン: run_daily_etl 等)
    - calendar_management.py (市場カレンダー管理、営業日判定)
    - audit.py           (監査ログスキーマ / init_audit_schema)
    - quality.py         (データ品質チェック)
  - strategy/
    - __init__.py        (戦略層のプレースホルダ)
  - execution/
    - __init__.py        (発注/実行層のプレースホルダ)
  - monitoring/
    - __init__.py        (監視用のプレースホルダ)

その他:
- pyproject.toml / setup.cfg 等（存在する場合はパッケージ管理に使用）
- .env / .env.local    （プロジェクトルートに配置して環境設定をロード）

---

## 運用・開発のヒント

- テスト時に環境変数の自動読み込みを抑止する場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector の外部通信を切りたい場合は内部関数 kabusys.data.news_collector._urlopen をモックしてください。
- ETL の品質チェックは fail-fast ではなく全ての問題を返すため、監査・アラートルールを別に設けることが推奨されます。
- DuckDB のパフォーマンス上、bulk insert をチャンク化しているため大規模データ取込でも比較的安全に動作します。

---

必要な追加情報（例: 実際のAPIキーや運用手順、CI/CD、cron ジョブの例など）があれば、README を拡張して運用マニュアルやデプロイ手順、サンプルユーティリティスクリプトを追記します。どの部分を詳しく追記しましょうか？