# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants や RSS を介して市場データ・財務データ・ニュースを収集し、DuckDB に格納・品質チェックを行い、戦略 -> 発注 -> 監査の各レイヤーに渡すための基盤機能を提供します。

バージョン: 0.1.0

---

## 主な特徴

- J-Quants API クライアント
  - 日次株価（OHLCV）・四半期財務データ・JPX カレンダーを取得
  - レート制限（120 req/min）遵守、リトライ・トークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録（look-ahead bias 対策）
  - DuckDB へ冪等的（ON CONFLICT DO UPDATE）に保存

- ニュース収集（RSS）
  - 複数 RSS ソースから記事を収集、前処理、DuckDB に保存
  - URL 正規化・トラッキングパラメータ除去、SSRF 対策、XML 攻撃対策（defusedxml）
  - 記事IDは正規化 URL の SHA-256（先頭32文字）で冪等性を保証
  - 銘柄コード抽出（テキスト中の 4 桁コードと既知銘柄セットの照合）

- ETL パイプライン
  - 差分更新（最終取得日ベース）＋バックフィル可能
  - カレンダー先読み、品質チェック（欠損/スパイク/重複/日付整合性）
  - run_daily_etl() による一括処理

- マーケットカレンダー管理
  - 営業日判定・前後営業日の取得・期間内営業日一覧取得
  - JPX カレンダーの夜間更新ジョブ

- 監査ログ（Audit）
  - シグナル -> 発注要求 -> 約定 のトレースを行う監査用スキーマ
  - 発注要求は冪等キー（order_request_id）で二重発注を防止
  - 全ての TIMESTAMP を UTC へ固定

- データ品質チェック（Quality）
  - 欠損値、スパイク、重複、日付不整合などの検出・集約

---

## 必要環境 / 依存パッケージ

- Python 3.10 以上（| 型ヒントなどを使用）
- ランタイム依存（主なもの）
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging, gzip, hashlib など

（開発環境により別途 slack / kabu API 用のパッケージが必要となる場合がありますが、本パッケージ内では標準ライブラリを使用した HTTP 呼び出しを行っています）

---

## セットアップ手順

1. リポジトリを取得（例）
   - git clone ... && cd repo

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt`）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと、自動で読み込まれます（自動ロードはデフォルトで有効）。  
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 必要な環境変数（主要なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（省略時: data/monitoring.db）
   - KABUSYS_ENV: 環境 (development|paper_trading|live)（省略時: development）
   - LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、省略時 INFO）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## データベース初期化

DuckDB スキーマを初期化するには data.schema.init_schema を使用します。

例:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# これで全テーブルとインデックスが作成されます（冪等）
```

監査ログ専用 DB を初期化する場合:
```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/audit.duckdb")
```

既存 DB へ接続のみ行いたい場合:
```python
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
```

---

## 使い方（主要 API と実行例）

- J-Quants の ID トークン取得
```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を使う
```

- 日次 ETL（市場カレンダ・株価・財務・品質チェック）
```python
from kabusys.data import pipeline, schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```
引数で id_token を渡すこともできます（テスト用やトークン注入）:
```python
result = pipeline.run_daily_etl(conn, id_token="xxx", run_quality_checks=True)
```

- ニュース収集（RSS）ジョブ
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# sources を指定しなければデフォルトソースを使用
results = news_collector.run_news_collection(conn, known_codes={"7203", "6758"})
# results は {source_name: saved_count} の辞書
```

- カレンダー更新ジョブ（夜間バッチ想定）
```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved: {saved}")
```

- 品質チェックだけ実行したい場合
```python
from kabusys.data import quality, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

- 簡単な ETL ワークフロー例（スクリプト化）
  - init_schema() を実行しておく
  - cron / Airflow 等から run_daily_etl() を呼ぶ（ログは設定した LOG_LEVEL に従う）

---

## 設定の自動ロードについて

- パッケージ起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env`→`.env.local` の順に自動読み込みします。
- OS 環境変数は保護され、.env.local で上書きできます。
- 自動ロードを無効にする: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- 設定アクセスは `from kabusys.config import settings` を使い、プロパティとして参照可能:
  - settings.jquants_refresh_token
  - settings.duckdb_path など

---

## ディレクトリ構成

主要ファイル／モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義と初期化
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — カレンダー管理（営業日判定・更新ジョブ）
    - audit.py               — 監査ログスキーマ（signal / order / execution）
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略層（実装を追加）
  - execution/
    - __init__.py            — 発注・ブローカー連携（実装を追加）
  - monitoring/
    - __init__.py            — 監視・メトリクス（実装を追加）

各モジュールは役割別に分かれており、ETL・データ保存・品質保証・監査トレースが独立して提供されます。

---

## 開発メモ / 注意点

- DuckDB の SQL 実行ではパラメータバインド（?）を使用しています。SQL インジェクションに注意。
- J-Quants API はレート制限があり、ライブラリは固定間隔スロットリングとリトライを実装しています。長時間の大規模取得時は API 制限に留意してください。
- news_collector は XML を解析するため defusedxml を使用しており、また SSRF / Gzip bomb 等の防御ロジックを備えています。
- ETL の品質チェックは Fail-Fast にならない設計（問題を集めて呼び出し元で判断）です。自動運用時は検出された問題に応じてアラートや処理フローを設計してください。
- audit.init_audit_schema() はデフォルトで接続のタイムゾーンを UTC に設定します。

---

必要な追加説明や、README のサンプル .env.example を出力する等の追加作業が必要であれば教えてください。