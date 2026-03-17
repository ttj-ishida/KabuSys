# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。J-Quants や kabu ステーション等の外部 API からデータを取得し、DuckDB に保存・整形、品質チェック、ニュース収集、監査ログなどを通じて戦略・実行層へつなげるための基盤機能を提供します。

主な設計思想:
- データの冪等性を重視（DuckDB への INSERT は ON CONFLICT を利用）
- API レートとエラーに対する堅牢なリトライ／トークンリフレッシュ
- SSRF / XML Bomb 等のセキュリティ対策（ニュース収集）
- 品質チェックと監査（トレース可能なログ設計）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - `.env` や OS 環境変数から設定を読み込む（自動ロード機能、無効化可）
  - 必須設定の取得・検証

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）取得（ページネーション対応、レート制限、リトライ、トークン自動リフレッシュ）
  - 財務データ取得（四半期 BS/PL）
  - JPX マーケットカレンダー取得
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（DB の最終取得日に基づく差分取得）
  - backfill による後出し修正吸収
  - 品質チェックの統合実行（kabusys.data.quality）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・正規化・前処理
  - 記事IDの冪等化（正規化 URL の SHA-256 先頭32文字）
  - SSRF 対策、受信サイズ制限、gzip 対応
  - DuckDB への保存（raw_news, news_symbols）

- データスキーマ管理（kabusys.data.schema）
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - スキーマ初期化・接続ヘルパー

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日の取得、期間内営業日リスト
  - 夜間のカレンダー差分更新ジョブ

- 監査（kabusys.data.audit）
  - シグナル→発注→約定のトレーサビリティテーブルと初期化ロジック

- データ品質検査（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合 等のチェック

---

## セットアップ手順

前提
- Python 3.10 以上（typing に | 演算子や Literal を使用しているため）
- Git リポジトリルートにプロジェクトがあること（自動 .env 検出用）

1. リポジトリをクローン／配置
   - 例: git clone ...

2. 仮想環境を作成して有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - プロジェクトを開発モードでインストールする場合（pyproject.toml があれば）:
     - pip install -e .

   ※他に必要なライブラリがあれば適宜追加してください（logging 等は標準ライブラリ）。

4. 環境変数設定 (.env)
   - プロジェクトルートの `.env` または `.env.local` に必要な設定を記述します。
   - 例（最低限）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   - 自動ロードを無効化したいとき:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（基本例）

以下はいくつかの典型的な利用例です。各種 API は Python から直接呼び出して利用します。

1) スキーマ初期化（DuckDB を作成して全テーブルを作る）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH から取得される Path
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行する（株価・財務・カレンダーを差分取得、品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)
print(result.to_dict())
```

引数例:
- target_date: 指定日を ETL 対象にする
- id_token: J-Quants の id_token を注入（テスト用）
- run_quality_checks: 品質チェックをスキップする場合は False

3) ニュース収集を実行する
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes に有効な銘柄コードのセットを渡すと紐付けも行う
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

4) 監査用スキーマの初期化（監査ログ専用）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 監査ログを別 DB として初期化する場合
audit_conn = init_audit_db(settings.duckdb_path)  # あるいは別パス
```

5) カレンダー更新バッチ（夜間ジョブ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"saved {saved} calendar rows")
```

注意点 / 挙動:
- J-Quants API 呼び出しは 120 req/min のレート制限を守るため内部でスロットリングします。
- HTTP 408/429/5xx 等では指数バックオフで最大 3 回リトライします。401 受信時はリフレッシュトークンで自動更新を試みます（1回だけ）。
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を基本としています。
- ニュース収集における RSS パースは defusedxml を使い XML 攻撃防止を行います。

---

## 環境変数一覧（主要）

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API パスワード
- SLACK_BOT_TOKEN: Slack ボットトークン（通知等に使用する場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

settings からは Python コード上で次のようにアクセスできます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.is_live)
```

---

## ディレクトリ構成

リポジトリの主要なファイル / モジュール一覧（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント + DuckDB 保存
    - news_collector.py       # RSS ニュース収集・保存
    - schema.py               # DuckDB スキーマ定義・初期化
    - pipeline.py             # ETL パイプライン
    - calendar_management.py  # 市場カレンダー管理
    - audit.py                # 監査ログ（signal/order/execution）スキーマ
    - quality.py              # データ品質チェック
  - strategy/
    - __init__.py             # 戦略層用プレースホルダ
  - execution/
    - __init__.py             # 発注/実行層用プレースホルダ
  - monitoring/
    - __init__.py             # 監視関連プレースホルダ

---

## 開発メモ / 注意事項

- Python の型注釈や構造はテスト可能性を考慮しており、id_token の注入や内部の _urlopen などをモックして単体テストを行えます。
- DuckDB 接続はシンプルな API で取得できます。運用時は接続数やファイルロックに注意してください。
- セキュリティ: RSS 取得時にリダイレクト先やレスポンスサイズを厳格に検査します。外部 URL の取り扱いには注意してください。
- ETL/ジョブはログ出力を前提としているため、運用環境では適切に logging を設定してください。

---

もし README に追加したい具体的な手順（例: systemd での定期ジョブ設定、Docker 化、CI 設定、サンプル .env.example）や、戦略／実行層のサンプルコードを希望される場合は教えてください。必要に応じて追記します。