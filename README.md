# KabuSys

日本株向け自動売買プラットフォーム用ユーティリティ群（ライブラリ）。  
データ取得・ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ用スキーマ等を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は J-Quants API や RSS フィード等から市場データ・ニュースを取得し、DuckDB に保存・整備するためのモジュール群です。  
設計上の特徴：

- J-Quants API 向けの堅牢なクライアント（レート制限、リトライ、トークン自動更新）
- DuckDB を用いた 3 層（Raw / Processed / Feature）データスキーマ
- ニュース収集モジュール：RSS 解析、URL 正規化、SSRF 対策、トラッキングパラメータ除去
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- カレンダー管理（JPX カレンダーの夜間バッチ更新、営業日判定）
- 監査ログ（シグナル→発注→約定のトレーサビリティ用テーブル）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

---

## 機能一覧

- 環境設定読み込み（.env / .env.local、自動ロード・保護）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 四半期財務データ取得
  - 市場カレンダー取得
  - レート制御（120 req/min）, リトライ、401時トークン自動リフレッシュ
- DuckDB スキーマ定義・初期化（raw_prices, raw_financials, market_calendar, features, signals, orders, trades, positions, audit tables など）
- ETL パイプライン（差分更新／バックフィル／品質チェック）
- ニュース収集（RSS パース、URL 正規化、記事ID生成、raw_news 保存、銘柄コード抽出）
- マーケットカレンダー管理（営業日判定、next/prev trading day、calendar update job）
- 品質チェック（missing, spike, duplicates, date consistency）
- 監査ログスキーマ（signal_events / order_requests / executions）

---

## 前提条件

- Python 3.10 以上（PEP 604 の `X | Y` 記法を使用）
- 推奨パッケージ（少なくとも次をインストールしてください）:
  - duckdb
  - defusedxml

例（pip）:
```bash
pip install duckdb defusedxml
```

プロジェクトでは urllib, json, logging, datetime 等の標準ライブラリを利用します。

---

## セットアップ手順

1. リポジトリをクローン／展開
2. Python 環境を用意（venv 等）
3. 依存ライブラリをインストール
   ```
   pip install duckdb defusedxml
   ```
   （requirements.txt / pyproject.toml がある場合はそれを使用してください）

4. 環境変数を設定（.env または OS 環境変数）
   - 自動でプロジェクトルートの `.env` → `.env.local` を読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意/デフォルト:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL) — デフォルト: INFO

   例 `.env`（簡易）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（主要な操作例）

以下は Python スクリプトまたは対話環境で利用する例です。

- DuckDB スキーマ初期化（全テーブル作成）
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ファイルがなければ親ディレクトリを自動作成
```

- 監査ログスキーマの初期化（既存接続に追加）
```python
from kabusys.data import audit
audit.init_audit_schema(conn)  # conn は init_schema で得た接続
# または監査専用DBを作る場合:
# audit.init_audit_db("data/audit.duckdb")
```

- 日次 ETL を実行（株価 / 財務 / カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # デフォルト: 今日を対象
print(result.to_dict())
```

- 単体 ETL ジョブ
  - 市場カレンダー更新（夜間バッチ）
    ```python
    from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)
    print("saved calendar rows:", saved)
    ```
  - 株価差分 ETL（例: ある日付まで）
    ```python
    from datetime import date
    from kabusys.data.pipeline import run_prices_etl
    fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 16))
    ```
  - 財務差分 ETL
    ```python
    from kabusys.data.pipeline import run_financials_etl
    fetched, saved = run_financials_etl(conn, target_date=date.today())
    ```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に使用する 4 桁コードのセット（省略すると銘柄紐付けをスキップ）
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)  # {source_name: 新規保存件数}
```

- J-Quants API 直接利用例（ID トークン取得・取得関数呼び出し）
```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を利用
quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 品質チェックを個別実行
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

- 環境設定オブジェクト（コードから参照）
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- jquants_client の _RateLimiter やトークンキャッシュはモジュールレベルで管理されます。テスト時に自動ロード等を抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector は defusedxml と SSRF 対策（リダイレクト検査、プライベートIP拒否）等を実装しています。テストで外部リクエストを差し替えたい場合は internal 関数（例: news_collector._urlopen）をモックしてください。

---

## ディレクトリ構成

リポジトリの主要ファイル/モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得 / 保存ロジック）
    - news_collector.py             — RSS ニュース取得・保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py                   — ETL パイプライン（差分更新・日次ETL）
    - calendar_management.py        — マーケットカレンダー管理・営業日判定
    - audit.py                      — 監査ログ（signal/events/order_requests/executions 等）
    - quality.py                    — データ品質チェック（missing / spike / duplicates / date）
  - strategy/
    - __init__.py                   — 戦略関連のエントリ（将来的に戦略実装）
  - execution/
    - __init__.py                   — 発注/ブローカー連携用モジュール（将来的に実装）
  - monitoring/
    - __init__.py                   — 監視・メトリクス関連（将来的に実装）

DuckDB スキーマは data/schema.py にまとめられており、Raw / Processed / Feature / Execution 層のテーブルが定義されています。

---

## 設定・デバッグのポイント

- .env 自動ロード:
  - プロジェクトルートは .git または pyproject.toml により検出されます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化する: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- KABUSYS_ENV の有効値:
  - development / paper_trading / live
- ログレベル:
  - LOG_LEVEL 環境変数で制御（DEBUG/INFO/...）。コード内 logger を利用しているため標準的な logging 設定で出力先を制御してください。
- ネットワーク関連:
  - J-Quants API の呼び出しは rate limit と retry ロジックがありますが、プロキシやネットワーク負荷のある環境では適宜調整が必要です。
- テスト:
  - ネットワークリクエスト（RSS / J-Quants）はモック可能な小さなラッパー（例: news_collector._urlopen）を経由しているため、ユニットテストで差し替えやすく設計されています。

---

## 開発・貢献

- 新機能・バグ修正の PR を歓迎します。コードの変更は既存の DB スキーマへの影響に注意してください（DDL 変更は互換性に注意）。
- 大規模なスキーマ変更や API の仕様変更はドキュメント（DataPlatform.md / DataSchema.md 等）と合わせて行ってください。

---

この README は現状のソースコードを参照してまとめたものです。追加の使い方や例が必要であれば、どの操作について詳しく記載するか教えてください。