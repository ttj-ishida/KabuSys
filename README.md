# KabuSys

日本株自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得・ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログなどの基盤機能を提供します。

---

## 概要

KabuSys は主に以下を目的とした内部ライブラリ群です。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する ETL パイプライン
- RSS からニュース記事を収集し、記事と銘柄の紐付けを行うニュース収集モジュール
- 市場カレンダーの管理（営業日判定、前後営業日の取得など）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル→発注→約定のトレース用スキーマ）
- 環境変数・設定の読み込み（.env 自動ロードを含む）

設計上の特徴：
- API レート管理、再試行（指数バックオフ）、トークン自動リフレッシュ
- DuckDB に対する冪等保存（ON CONFLICT を利用）
- SSRF・XML Bomb 対策などセキュリティ考慮
- 品質チェックはFail-Fastにせず、問題を収集して呼び出し元で判断可能

---

## 主な機能一覧

- データ取得（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）の取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
  - レート制限・リトライ・トークン管理
  - DuckDB への idempotent な保存関数

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードの安全な取得（SSRF/サイズ/圧縮対策）
  - URL 正規化・記事ID生成（SHA-256）
  - DuckDB への冪等保存（INSERT ... RETURNING）
  - テキスト前処理・銘柄コード抽出

- スキーマ管理（src/kabusys/data/schema.py）
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）
  - 初期化関数（init_schema）・コネクション取得

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新ロジック（最終取得日から必要範囲のみ取得）
  - 日次 ETL のエントリ run_daily_etl（カレンダー → 株価 → 財務 → 品質チェック）
  - 各種個別 ETL ジョブ（prices / financials / calendar）

- マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
  - 営業日判定、前後営業日の取得、範囲の営業日リスト取得
  - 夜間バッチ（calendar_update_job）

- 監査ログ（src/kabusys/data/audit.py）
  - signal_events / order_requests / executions 等の監査スキーマ
  - 初期化関数（init_audit_schema / init_audit_db）

- データ品質チェック（src/kabusys/data/quality.py）
  - 欠損データ、重複、スパイク、日付整合性検査
  - run_all_checks による一括実行

- 設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の抽象化（settings オブジェクト）
  - KABUSYS_ENV / LOG_LEVEL 等の検証ロジック

---

## セットアップ手順

必要環境
- Python 3.10 以上（型ヒントの | 演算子等を使用）
- pip

必須 Python パッケージ（代表例）
- duckdb
- defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb defusedxml
```

※ 実プロジェクトでは requirements.txt を用意して `pip install -r requirements.txt` を行ってください。  
※ Slack 連携や kabuステーション連携など追加ライブラリが必要な場合があります（本リポジトリでは最小コアのみ記載）。

環境変数設定
- プロジェクトルートに `.env`（および必要なら `.env.local`）を配置すると自動で読み込まれます。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（settings で使用）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — デフォルト "http://localhost:18080/kabusapi"
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン（通知用）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（Monitoring用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意) — "development" | "paper_trading" | "live"（デフォルト development）
- LOG_LEVEL (任意) — "DEBUG","INFO","WARNING","ERROR","CRITICAL"（デフォルト INFO）

例: .env
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易例）

以下はライブラリを直接使う簡単なコード例です。実際はエントリスクリプトやジョブランナーから呼び出します。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# デフォルトファイル位置を使う場合 settings.duckdb_path を参照して初期化できます
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants への認証は settings で管理）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes があれば記事中の4桁銘柄コード抽出→紐付けを行う
known_codes = {"7203", "6758", "9432"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

4) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"保存件数: {saved}")
```

5) 監査スキーマの初期化（既存の conn に追加）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

設定の参照例
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env)
```

ログ設定・実行環境向けに適切なロギングコンフィグを用意してください（LOG_LEVEL 環境変数で制御）。

---

## ディレクトリ構成

以下は本コードベースの主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py
    - パッケージ定義（バージョン等）
  - config.py
    - 環境変数の自動読み込み、settings オブジェクト
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py
      - RSS からニュース収集、前処理、DuckDB 保存、銘柄抽出
    - schema.py
      - DuckDB の DDL（Raw/Processed/Feature/Execution 層）と初期化
    - pipeline.py
      - ETL の差分更新ロジック、run_daily_etl 等
    - calendar_management.py
      - カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
    - audit.py
      - 監査ログ用テーブル定義と初期化
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - strategy/
    - __init__.py（戦略モジュール用プレースホルダ）
  - execution/
    - __init__.py（実行/発注周りプレースホルダ）
  - monitoring/
    - __init__.py（モニタリング周りプレースホルダ）

その他:
- .env / .env.local
  - 実行環境に応じた環境変数を配置

---

## 運用上の注意 / ベストプラクティス

- .env には機密情報（APIトークン等）が含まれるため、ソース管理には含めないこと。`.gitignore` に追加してください。
- DB ファイル（DuckDB）はバックアップ・ローテーションや永続化先を考慮してください（大きくなることがあります）。
- J-Quants のレート制限（120 req/min）を遵守していますが、短時間で大量の処理を並列化する場合は追加の考慮が必要です。
- NEWS 収集では外部 URL を扱うため、SSRF・XML攻撃対策を行っていますが、さらに厳しい制約が必要な場合はファイアウォール等で保護してください。
- 本ライブラリはコア機能に集中しており、運用の監視・アラート・ジョブスケジューリングは別途用意してください（cron, Airflow など）。

---

## 参考

- settings による .env 自動ロードの挙動:
  - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を起点に `.env` を読み込み、続いて `.env.local` を読み込みます。
  - OS 環境変数が優先され、`.env.local` は既存の OS 値を上書きできますが `.env` は OS 値を上書きしません。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

この README はコードベースに含まれる主要モジュールの概要と利用手順をまとめたものです。実際の運用や拡張にあたっては、個別モジュール（特に jquants_client, news_collector, pipeline, schema, audit, quality）のドキュメントコメントを参照してください。