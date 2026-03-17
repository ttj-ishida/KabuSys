# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants）、ETL、ニュース収集、DuckDB スキーマ定義、データ品質チェック、マーケットカレンダー管理、監査ログ機能などを提供します。

- 現状のパッケージバージョン: 0.1.0

---

## 概要

KabuSys は日本株のアルゴリズム取引基盤のための内部ライブラリ群です。主な目的は以下のとおりです。

- J-Quants API からの市場データ・財務データ・マーケットカレンダーの取得（レートリミット・リトライ・トークン自動更新を実装）
- RSS フィードからのニュース収集・前処理・銘柄紐付け
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）のスキーマ定義と初期化
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー操作（営業日判定、次/前営業日検索、夜間バッチ更新）
- 監査ログ（シグナル → 発注 → 約定までのトレース）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上、冪等性（ON CONFLICT）、Look-ahead Bias 防止のための fetched_at 記録、セキュリティ対策（SSRF防止、defusedxml 利用等）に配慮しています。

---

## 機能一覧

- 環境変数/設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出: .git / pyproject.toml）
  - 必須環境変数の検査
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価（日足）、財務（四半期）、マーケットカレンダー取得
  - レートリミット遵守 / リトライ（指数バックオフ） / トークン自動リフレッシュ
  - DuckDB への冪等保存用関数
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、テキスト前処理、ID 生成（正規化 URL → SHA-256）
  - SSRF 対策、受信サイズ制限、defusedxml による安全な XML パース
  - raw_news / news_symbols への保存（トランザクション、チャンク挿入）
  - テキストからの銘柄コード抽出（既知銘柄コードセットに基づく）
- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス定義
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（calendar → prices → financials → 品質チェック）
  - 差分更新・backfill 対応
  - 品質チェックの集約結果を ETLResult として返却
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev 営業日、期間内営業日リスト
  - 夜間更新ジョブ（calendar_update_job）
- 品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合チェック
  - QualityIssue を返す（error / warning）
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions 等の監査テーブルと初期化関数

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションに X | Y を使用）
- Git, pip 等の基本ツール

推奨手順（開発環境）

1. リポジトリをクローン / 取得
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 必須パッケージ（最低限）
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - packaging が整っている場合:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env（または .env.local）を作成します。自動読み込みは .git または pyproject.toml を起点に行われます。
   - 主要な環境変数例:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_api_password
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (任意; デフォルトあり)
     - SLACK_BOT_TOKEN=your_slack_bot_token
     - SLACK_CHANNEL_ID=your_slack_channel_id
     - DUCKDB_PATH=data/kabusys.duckdb  (デフォルト)
     - SQLITE_PATH=data/monitoring.db    (デフォルト)
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - LOG_LEVEL=INFO|DEBUG|...  (デフォルト: INFO)
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env ロードを無効化可能

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - 監査ログ専用に初期化する場合:
     - from kabusys.data.audit import init_audit_db
     - audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     - または既存 conn に対して init_audit_schema(conn)

---

## 使い方（簡易例）

以下は代表的な使い方例（対話的に実行する想定）。

1) DuckDB スキーマ作成 / 接続
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection

# init（ファイルがなければ親ディレクトリも作成）
conn = init_schema(settings.duckdb_path)

# 既存 DB に接続するのみ
# conn = get_connection(settings.duckdb_path)
```

2) 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定せず実行すると今日を基準に処理
print(result.to_dict())
```

3) ニュース収集ジョブの実行（既知銘柄コードセットを渡すと銘柄紐付けを行う）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 例えば取引対象の銘柄コードセットを用意
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

4) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved:", saved)
```

5) 監査ログ初期化（既存 conn に対して）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # conn は init_schema の戻り値でも可
```

注記:
- J-Quants API 呼び出しはレートリミット（120 req/min）を遵守します。
- get_id_token() によるトークン取得は settings.jquants_refresh_token を使用します。必須環境変数を正しく設定してください。

---

## ディレクトリ構成

開発時の主要ファイル・モジュール構成（抜粋）:

src/
  kabusys/
    __init__.py
    config.py                    # 環境変数・設定読み込みロジック
    data/
      __init__.py
      jquants_client.py          # J-Quants API クライアント（取得・保存）
      news_collector.py          # RSS ニュース収集・保存・銘柄抽出
      schema.py                  # DuckDB スキーマ定義・初期化
      pipeline.py                # ETL パイプライン（差分取得・品質チェック）
      calendar_management.py     # マーケットカレンダー管理
      audit.py                   # 監査ログ（signal/order/execution）
      quality.py                 # データ品質チェック
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py

主要モジュールの説明:
- kabusys.config: .env 自動読み込み、Settings クラス（各種環境変数プロパティ）
- kabusys.data.*: データ取得・保存・ETL・品質系の実装群
- strategy / execution / monitoring: 将来的な戦略・発注・監視ロジックのプレースホルダ（現状 __init__ のみ）

---

## 注意事項 / 実運用向けのヒント

- 環境変数は .env.example などを参照して必要なキーを設定してください（JQUANTS_REFRESH_TOKEN 等）。
- 本ライブラリは J-Quants の API レスポンスや kabuステーション API を前提としています。実運用時は API の利用規約やキーの管理に注意してください。
- DuckDB ファイルのバックアップと権限管理を適切に行ってください。
- ニュースの URL 正規化や RSS パースではトラッキングパラメータを除去しますが、運用上の要件で別途保持したい場合は実装を調整してください。
- テストを行う際は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化できます。

---

必要に応じて README に追記（CLI 実行例、より詳細な .env.example、デプロイ手順、CI/CD 設定等）します。どの項目を詳しく追加したいか教えてください。