# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。  
J-Quants / kabuステーション 等のデータソースからデータを取得・保存し、ETL・データ品質チェック・ニュース収集・監査ログ（発注〜約定トレーサビリティ）などの機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを支えるデータ基盤・ユーティリティ群をまとめた Python パッケージです。主に以下を目的としています。

- J-Quants API からの市場データ（株価、財務、マーケットカレンダー）取得と DuckDB への冪等保存
- RSS フィードからのニュース収集と銘柄紐付け
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、次営業日/前営業日の取得）
- 監査ログ（シグナル → 発注 → 約定 のトレース可能なテーブル群）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

設計上のポイントとして、API レート制限・再試行戦略・SSRF対策・Gzip/サイズ制限・トランザクション管理・冪等性（ON CONFLICT）等を重視しています。

---

## 主な機能一覧

- J-Quants クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - トークン自動リフレッシュ、指数バックオフ・リトライ、レートリミット制御
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、自動バックフィル、品質チェック）
- ニュース収集モジュール（RSS -> raw_news 保存、記事IDの冪等化、SSRF対策、トラッキングパラメータ除去）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（営業日判定、next/prev/get_trading_days、更新ジョブ）
- 監査ログ（signal_events / order_requests / executions の初期化用 DDL とユーティリティ）

---

## 動作要件（概略）

- Python 3.10+
- 必要なライブラリ（主なもの）
  - duckdb
  - defusedxml

（依存関係はプロジェクト配布方法に合わせて requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローン

   ```
   git clone <this-repo-url>
   cd <this-repo>
   ```

2. 仮想環境作成（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール

   例（最低限）:

   ```
   pip install duckdb defusedxml
   ```

   プロジェクト配布がセットアップ可能であれば:

   ```
   pip install -e .
   ```

   または requirements.txt を用意している場合:

   ```
   pip install -r requirements.txt
   ```

4. 環境変数設定

   プロジェクトルート（.git や pyproject.toml を含むディレクトリ）に `.env` / `.env.local` を置くと、自動的に読み込まれます（読み込み順: OS環境 > .env.local > .env）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須（Settings クラスで require されるもの）:

   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API のパスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   任意（デフォルト値あり）:

   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
   - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db

   例 .env:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 初期化（DuckDB スキーマ）

Python スクリプトから DuckDB スキーマを初期化する例:

```python
from kabusys.data import schema
from kabusys.config import settings

# ファイルに永続化された DuckDB を初期化
conn = schema.init_schema(settings.duckdb_path)
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

監査ログ専用 DB を初期化する例:

```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/audit.duckdb")
```

---

## 使い方（簡易例）

- J-Quants の ID トークン取得

```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を参照して取得
```

- 日次 ETL の実行（株価・財務・カレンダーを差分取得し品質チェックを実行）

```python
from kabusys.data import pipeline, schema
from kabusys.config import settings
from datetime import date

conn = schema.init_schema(settings.duckdb_path)
result = pipeline.run_daily_etl(conn, target_date=date.today())

print(result.to_dict())
```

- RSS ニュース収集ジョブ

```python
from kabusys.data import news_collector, schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)

# 既知の銘柄コード集合 (extract_stock_codes で参照)
known_codes = {"7203", "6758", "9984"}

# デフォルト RSS ソースを使って収集
stats = news_collector.run_news_collection(conn, known_codes=known_codes)
print(stats)
```

- カレンダー更新ジョブ（夜間バッチ等で利用）

```python
from kabusys.data import calendar_management, schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
```

- ETL の個別実行（例: 株価のみ差分取得）

```python
from datetime import date
from kabusys.data import pipeline, schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

---

## 環境変数の自動読み込みについて

- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を探索）を特定し、`.env` と `.env.local` を自動読み込みします。
- 既に OS 環境変数があるキーは上書きされません（.env.local は上書き可）。
- テストなどで自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。
- .env のパースはシェル風（export KEY=val、クォートあり/なし、行内コメントなど）に対応しています。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要なモジュールと役割:

- src/kabusys/
  - __init__.py : パッケージ定義、バージョン
  - config.py : 環境変数 / 設定の読み込みと Settings クラス
- src/kabusys/data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（取得・保存用ユーティリティ）
  - news_collector.py : RSS ベースのニュース収集と raw_news/news_symbols 保存
  - pipeline.py : ETL パイプライン（run_daily_etl 等）
  - schema.py : DuckDB スキーマ定義と init_schema / get_connection
  - calendar_management.py : マーケットカレンダー管理（営業日判定・更新ジョブ）
  - audit.py : 監査ログ（signal_events, order_requests, executions 等）初期化
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
- src/kabusys/strategy/ : 戦略関連（将来的な実装領域）
- src/kabusys/execution/ : 発注実装（将来的な実装領域）
- src/kabusys/monitoring/ : 監視・メトリクス（将来的な実装領域）

（各モジュール内に設計方針や挙動の詳細コメントが記載されています）

---

## 開発・運用上の注意

- J-Quants のレート制限（120 req/min）や API のレスポンスエラーに対するリトライ・バックオフロジックを組み込んでいますが、運用環境では過剰な同時実行を避ける運用設計が必要です。
- DuckDB のトランザクション管理や ON CONFLICT による冪等性を前提にしているため、外部からの直接的な DB 操作は注意してください。
- news_collector は外部 URL を取得するため SSRF 対策や受信サイズ上限を実装していますが、運用環境のセキュリティポリシーに従ってください。
- 監査ログ（audit）を有効にすると、発注〜約定のトレースが可能になります。必ず UTC タイムゾーンでの保存を行う設計です。

---

## よくある操作

- スキーマの初期化（最初に一度）:
  - schema.init_schema(settings.duckdb_path)
  - audit.init_audit_db("data/audit.duckdb")（監査用に別 DB を用意する場合）

- 日次バッチ（cron / Airflow 等）:
  - 仮想環境を有効化し、スクリプトで schema.init_schema → run_daily_etl を呼ぶ

---

READMEに書かれている説明は、各モジュール内にも詳細な docstring / コメントがあります。実運用前に Settings の環境変数を正しく設定し、テスト環境で ETL と DB 初期化を確認してください。疑問点や追加のドキュメント化が必要な箇所があれば教えてください。