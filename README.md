# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けユーティリティ群です。  
データ取得（J‑Quants）、ニュース収集、DuckDB スキーマ管理、ETL パイプライン、品質チェック、監査ログなど、戦略・実行層の基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

主な目的は「市場データの堅牢な収集・保存・品質管理」と「売買フローのトレーサビリティ確保」です。  
設計上の特徴：

- J‑Quants API からの株価・財務・カレンダー取得（レート制限遵守、リトライ、トークン自動リフレッシュ）
- RSS ベースのニュース収集（SSRF/XML攻撃対策、トラッキングパラメータ除去、記事IDの冪等化）
- DuckDB を用いた 3 層（Raw / Processed / Feature）＋Execution / Audit のデータスキーマ
- ETL（差分更新、バックフィル、品質チェック）を行う日次パイプライン
- 監査ログ（signal → order_request → executions）のスキーマと初期化ユーティリティ
- 各所で冪等性・トランザクション管理を重視

---

## 機能一覧

- 環境設定管理（.env の自動読み込み / 環境変数）
- J‑Quants クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務（四半期 BS/PL）取得
  - マーケットカレンダー取得
  - レートリミッタ、リトライ、401 時のトークン自動リフレッシュ
- ニュース収集（RSS）
  - URL 正規化・記事ID生成（SHA‑256）
  - SSRF・gzip bomb・XML 注入対策
  - raw_news / news_symbols への冪等保存
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 向けテーブル定義とインデックス
  - スキーマ初期化ユーティリティ（init_schema / init_audit_schema 等）
- ETL パイプライン
  - 日次 ETL（calendar → prices → financials → 品質チェック）
  - 差分更新・バックフィル機能
- データ品質チェック
  - 欠損・重複・スパイク（前日比変化）・日付不整合検出
- カレンダー管理
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
- 監査ログ（audit）スキーマ
  - signal_events, order_requests, executions テーブルおよびインデックス

空のパッケージ・プレースホルダ:
- kabusys.strategy
- kabusys.execution
- kabusys.monitoring

---

## セットアップ

前提
- Python 3.10 以上（PEP 604 の型記法（|）などを使用）
- ネットワーク接続（J‑Quants、RSS など）

推奨パッケージ（最低限）
- duckdb
- defusedxml

例: pip でインストールする場合
```bash
python -m pip install duckdb defusedxml
```

ローカル開発時（プロジェクトルートで）
```bash
python -m pip install -e .
# または必要パッケージを requirements.txt にまとめている場合
# python -m pip install -r requirements.txt
```

環境変数
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効にする（1 または任意値で無効化）

.env の自動読み込み
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を検出し、
  `.env` → `.env.local` の順で読み込みます（OS 環境変数が優先、.env.local は上書き）。
- 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用等）。

---

## 使い方（基本例）

以下はライブラリを利用する簡単なスクリプト例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

2) 監査ログスキーマ初期化（既存接続に追加）
```python
from kabusys.data import audit

# schema.init_schema で作成した conn を渡す
audit.init_audit_schema(conn, transactional=True)
# 監査専用DBを作成する場合
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl, get_connection
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- run_daily_etl はカレンダー → 株価 → 財務 → 品質チェック を順に実行します。J‑Quants の認証は Settings から自動取得（環境変数）されます。必要なら id_token を引数で渡せます。

4) RSS ニュース収集と保存
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "8035", "6758"}  # 既知の銘柄コードセット（抽出用）
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}
```

5) J‑Quants API を直接利用（fetch / save）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

注意点
- jquants_client は 120 req/min のレートリミットを組み込み済みです。大量取得時は RateLimiter によりスロットリングされます。
- API から 401 が返った場合は自動でトークンをリフレッシュして 1 回だけリトライします。
- fetch_* はページネーション対応で全件を取得します（pagination_key を使用）。
- ETL は冪等性を重視しており、DuckDB への INSERT は ON CONFLICT DO UPDATE などで衝突を扱います。

---

## ディレクトリ構成

プロジェクトの主要ファイル・ディレクトリ構成（抜粋）
```
src/
  kabusys/
    __init__.py           # パッケージ初期化・version
    config.py             # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py   # J-Quants API クライアント（fetch/save）
      news_collector.py   # RSS ニュース収集
      schema.py           # DuckDB スキーマ定義・init
      pipeline.py         # ETL パイプライン（日次ETL等）
      calendar_management.py  # マーケットカレンダー管理
      audit.py            # 監査ログ（signal/order/execution）スキーマ
      quality.py          # データ品質チェック
    strategy/
      __init__.py         # 戦略レイヤー用プレースホルダ
    execution/
      __init__.py         # 発注/約定/ブローカー連携用プレースホルダ
    monitoring/
      __init__.py         # 監視/メトリクス用プレースホルダ
```

---

## 補足・トラブルシューティング

- 環境変数が不足していると Settings のプロパティが ValueError を投げます（例: JQUANTS_REFRESH_TOKEN が未設定）。
- 自動 .env 読み込みはプロジェクトルート検出（.git もしくは pyproject.toml）が成功した場合のみ行われます。CI 等で無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- RSS 取得は SSRF や XML 攻撃に対する対策を組み込んでいます。外部 URL を柔軟に扱う場面では例外処理を適切に追加してください。
- DuckDB ファイルのパーミッションやディレクトリ作成の失敗は Path 作成時に例外が出ます。init_schema は親ディレクトリを自動作成しますが、権限を確認してください。

---

## 開発・拡張

- strategy / execution / monitoring パッケージは拡張ポイントです。戦略で生成した signal を signal_queue / order_requests を通じて execution 層へ渡し、audit テーブルでトレーサビリティを保つ設計になっています。
- テスト: 環境依存を切り離すため、pipeline/run_daily_etl 等は id_token を引数で受け取れるようになっています。外部呼び出しをモックして単体テストを作成しやすい設計です。

---

README に記載の無い操作や実装の詳細については、該当するモジュール（kabusys/data/*.py、kabusys/config.py）を参照してください。必要であれば README のサンプルコードや環境変数の雛形（.env.example）等も作成しますのでお知らせください。