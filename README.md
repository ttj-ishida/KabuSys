# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ群です。データ取得・ETL、ニュース収集、マーケットカレンダー管理、監査ログ（トレーサビリティ）、簡易的なストラテジ / 実行レイヤーの土台を提供します。

現在のバージョン: 0.1.0

---

## 概要

KabuSys は以下を実現することを目的とした Python パッケージです。

- J-Quants API からの株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
- RSS フィードからのニュース収集と銘柄紐付け
- DuckDB を用いたスキーマ定義・初期化および冪等保存
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダーを用いた営業日判定ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマと初期化
- 設定は環境変数／.env ファイルで管理（自動読み込み機能あり）

設計上の注力点：API レート制御、リトライ、冪等性、Look-ahead バイアス対策、SSRF対策、データ品質チェックなど。

---

## 主な機能一覧

- データ取得（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - トークン自動リフレッシュ・リトライ・レートリミット対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）: カレンダー取得 → 株価 → 財務 → 品質チェック
  - 差分更新、バックフィル機能
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（gzip 対応、XML 攻撃対策）、URL 正規化、記事ID生成（SHA-256 先頭32文字）
  - raw_news テーブルへの冪等保存、銘柄コード抽出と紐付け
  - SSRF 対策（リダイレクト検査・プライベートIP拒否）、レスポンスサイズ制限
- スキーマ管理（kabusys.data.schema）
  - DuckDB スキーマ一式の定義と init_schema / get_connection
  - Raw / Processed / Feature / Execution 層のテーブルを含む
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job：夜間バッチでカレンダーを差分更新
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions 等の監査テーブルと初期化関数
  - UTC タイムゾーン固定やトランザクション制御
- 品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比）、重複、日付不整合などのチェック群と集約実行

---

## 前提 / 推奨環境

- Python 3.10+
- DuckDB（Python パッケージ）
- defusedxml
- その他標準ライブラリ（urllib 等）

（実プロジェクトでは pyproject.toml / requirements.txt を用意して依存管理してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS/Linux
   .venv\Scripts\activate       # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   # 任意でパッケージを editable install する場合:
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置することで自動的に読み込まれます（優先度: OS 環境変数 > .env.local > .env）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD : kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN : Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
   - 任意・デフォルト:
     - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL : デフォルト http://localhost:18080/kabusapi
     - DUCKDB_PATH : デフォルト data/kabusys.duckdb
     - SQLITE_PATH : デフォルト data/monitoring.db

   .env の例（簡易）:
   ```
   JQUANTS_REFRESH_TOKEN=あなたの_refresh_token
   KABU_API_PASSWORD=あなたの_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（基本例）

以下は Python スクリプト／REPL での基本的な利用例です。

1) スキーマ初期化（DuckDB）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイルを自動作成してテーブル定義を作成
```

2) 監査スキーマ初期化（監査用 DB）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

3) 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)  # 既存接続（init_schema 後）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4) ニュース収集ジョブ（RSS 取得 → 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 既知の銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

5) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

6) J-Quants 直接呼び出し（トークン取得・API 呼び出し）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を使用
quotes = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
```

---

## 主要モジュール（ディレクトリ構成）

ルート: src/kabusys 以下（主なファイル/パッケージ）

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 管理（自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得/保存/レート制御/リトライ）
    - news_collector.py             — RSS ニュース収集・前処理・保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py                   — ETL パイプライン（日次 ETL / 各ジョブ）
    - calendar_management.py        — カレンダー管理と営業日ユーティリティ
    - audit.py                      — 監査ログ（signal/order/execution）スキーマ & 初期化
    - quality.py                    — データ品質チェック群
  - strategy/
    - __init__.py                   — 戦略層（拡張ポイント）
  - execution/
    - __init__.py                   — 発注実装（拡張ポイント）
  - monitoring/
    - __init__.py                   — 監視 / メトリクス（拡張ポイント）

---

## 注意事項 / 実運用上のポイント

- 環境変数の自動ロード:
  - プロジェクトルート（.__file__ を基準に上位で .git または pyproject.toml が見つかる場所）にある `.env` / `.env.local` を自動読み込みします。
  - テスト等で自動ロードを無効にする場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants API:
  - レート制限（120 req/min）に基づく固定間隔スロットリングを実装済みです。
  - 401 受信時はリフレッシュトークンから自動で id_token を再取得して 1 回リトライします。
- DuckDB スキーマ:
  - init_schema は冪等にテーブルを作成します。初回実行で DB ファイルの親ディレクトリがなければ作成します。
- ニュース収集:
  - RSS のレスポンス上限（10MB）や SSRF 対策を実装しています。外部 URL の検証（スキーム、プライベートアドレス）を行います。
- 品質チェック:
  - ETL 後の品質チェックは Fail-Fast ではなく全件収集し、呼び出し元が判断できるようにしています。
- 監査ログ:
  - 監査テーブルは UTC タイムゾーンで保存する想定です（init_audit_schema は SET TimeZone='UTC' を実行します）。

---

## テスト / 開発ヒント

- テスト時に環境変数を直接注入し、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みをオフにすることで再現性のあるテストが可能です。
- jquants_client の HTTP 呼び出し部分は urllib を使用しているため、単体テスト時は urllib.request.urlopen などをモックするか、モジュールレベルの token キャッシュ関数を差し替えてテストしてください。
- news_collector._urlopen をモックすることで外部ネットワークに依存しないテストが可能です。

---

## 貢献 / ライセンス

（この README はコードベースから自動生成した概要です。実際のリポジトリに CONTRIBUTING ガイドや LICENSE を追加してください。）

---

README に記載されていない詳細な API 仕様や運用手順（cron / Airflow の例、Slack 通知・監視の実装など）は、今後ドキュメントを拡充してください。必要であれば、README にサンプルの cron ジョブや systemd タイマー例、docker-compose 例の追記も可能です。必要であればその内容を教えてください。