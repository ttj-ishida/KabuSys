# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ。  
データ取得（J-Quants）、ETL パイプライン、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ定義、データ品質チェック、監査ログ（発注→約定トレーサビリティ）といった基盤機能を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）遵守、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ETL パイプライン
  - 差分更新（最終取得日＋バックフィル）、カレンダー先読み、品質チェックを統合
  - run_daily_etl で日次 ETL を実行

- ニュース収集モジュール
  - RSS フィードから記事取得、前処理、DuckDB への冪等保存（raw_news）
  - URL 正規化（トラッキングパラメータ除去）、SSRF 防止、XML 攻撃対策（defusedxml）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で一意化

- マーケットカレンダー管理
  - JPX カレンダーの差分更新バッチ、営業日判定ユーティリティ（next/prev/get_trading_days/is_sq_day）

- データ品質チェック
  - 欠損・スパイク（急騰/急落）・重複・日付不整合を検出
  - QualityIssue オブジェクトで問題を集約し呼び出し元が対処可能

- DuckDB スキーマ管理（Data Layer）
  - Raw / Processed / Feature / Execution / Audit 各レイヤーのテーブル DDL を提供
  - init_schema / init_audit_db による初期化

- 監査ログ（Audit）
  - signal → order_request → executions のトレーサビリティを保証するテーブル群
  - UTC タイムゾーン固定、冪等・ステータス管理

---

## 前提（依存・環境）

最小限のランタイム依存（抜粋）:
- Python 3.10+（型注釈で | 型などを使用）
- duckdb（DuckDB Python バインディング）
- defusedxml（RSS/XML パースの安全化）

実際のプロジェクトでは pyproject.toml / requirements.txt に依存を記載してください。

---

## セットアップ手順

1. リポジトリをクローンし、開発環境を構築します（例: 仮想環境）:

   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install --upgrade pip
     ```

2. 必要パッケージのインストール（例）:
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトで requirements を用意している場合はそちらを利用してください）

3. パッケージをインストール（編集可能なモード）:
   ```
   pip install -e .
   ```
   （プロジェクトルートに pyproject.toml / setup.cfg 等がある想定です）

4. 環境変数を設定:
   - リポジトリルートの .env または環境変数で設定します（下記「環境変数」参照）。
   - 自動読み込みはデフォルトで有効。テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## 必要な環境変数

Settings クラスは環境変数を参照します。主な必須/任意変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack のチャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB 保存パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）

設定例（.env）:
```
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

以下は主要 API の利用例です。実行前に必要な環境変数と依存パッケージを設定してください。

- DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ファイルを作成してスキーマを作る
```

- 日次 ETL 実行（J-Quants から株価・財務・カレンダーを取得し品質チェック）:
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

- ニュース収集ジョブ:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
stats = run_news_collection(conn, known_codes=known_codes)
print(stats)  # {source_name: saved_count}
```

- カレンダー夜間更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

- 監査ログ用スキーマ初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- J-Quants API を直接使って ID トークンを取得:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()
```

注意:
- jquants_client の各関数は内部でレートリミットとリトライ処理を行います。
- fetch 系関数はページネーションに対応しています。
- ETL 関数は冪等に設計されており、ON CONFLICT による上書きを行います。

---

## ディレクトリ構成（抜粋）

src/
  kabusys/
    __init__.py
    config.py                    # 設定・.env 読み込みロジック
    data/
      __init__.py
      jquants_client.py          # J-Quants API クライアント（取得＋保存）
      news_collector.py          # RSS ニュース取得・前処理・DB 保存
      schema.py                  # DuckDB スキーマ定義と初期化
      pipeline.py                # ETL パイプライン（run_daily_etl 等）
      calendar_management.py     # カレンダー更新と営業日ユーティリティ
      audit.py                   # 監査ログ（signal/order_request/executions）
      quality.py                 # データ品質チェック
      audit.py
    strategy/                     # 戦略層（空のパッケージ、拡張ポイント）
      __init__.py
    execution/                    # 発注・約定連携（拡張ポイント）
      __init__.py
    monitoring/                   # 監視モジュール（拡張ポイント）
      __init__.py

主要モジュールは data パッケージ下に集約されています。strategy / execution / monitoring は拡張ポイントとして空のパッケージが準備されています。

---

## 設計上の注意点 / 運用メモ

- API レート制限
  - J-Quants は 120 req/min を想定しており、jquants_client は固定間隔の RateLimiter を使用しています。大量の同時要求を行わないでください。

- セキュリティ
  - news_collector は defusedxml と SSRF 対策（リダイレクト検証 / プライベートホスト拒否 / レスポンスサイズ上限）を実装していますが、外部フィードの取り扱いには注意してください。

- 時刻・タイムゾーン
  - すべての fetched_at / created_at 等のタイムスタンプは UTC を前提としています。監査スキーマ初期化時に TimeZone を UTC に固定します。

- 冪等性
  - raw データ保存処理は ON CONFLICT を使って上書き（またはスキップ）するよう設計されています。複数回実行しても重大な重複を生じないよう配慮しています。

- テスト
  - ネットワーク依存の箇所（_urlopen 等）をモックしやすい設計になっています。CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境読み込みを無効化できます。

---

## 開発・拡張のヒント

- strategy / execution / monitoring パッケージはプレースホルダです。ここにアルゴリズム、ポートフォリオ管理、発注ラッパー等を実装してください。
- DuckDB の SQL を直接利用して高速なバッチ変換や特徴量計算（features テーブル生成）を実装できます。
- audit スキーマはトレーサビリティを重視しています。order_request_id を冪等キーとして使用して二重発注を防ぐ実装を行ってください。

---

もし README に追加したいサンプルスクリプト、CI 設定、あるいは具体的な環境（pyproject/requirements）ファイルがあれば、追記して詳細なセットアップ手順を作成します。