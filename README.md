# KabuSys

KabuSys は日本株の自動売買／データ基盤用のライブラリ群です。  
J-Quants API からの市場データ取得、DuckDB によるスキーマ定義・永続化、ETL パイプライン、ニュース収集、監査ログなど、取引戦略開発に必要な基盤機能を提供します。

---

## 概要

主な目的：

- J-Quants API から株価・財務・マーケットカレンダー等を取得して DuckDB に保存
- ETL（差分取得・バックフィル・品質チェック）を自動化
- RSS ベースのニュース収集と銘柄紐付け
- 監査ログ（signal → order → execution のトレース）用スキーマ
- カレンダー判定（営業日 / SQ 日など）と夜間更新ジョブ

設計上のポイント：

- API レート制限（120 req/min）・リトライ・トークン自動リフレッシュを考慮
- DuckDB を用いた冪等性のある保存（ON CONFLICT）
- ニュース収集は SSRF / XML-Bomb / 大容量レスポンス対策あり
- 品質チェックで欠損・スパイク・重複・日付不整合を検出

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（株価日足 / 財務 / 市場カレンダー取得）
  - レート制御・再試行・401 の自動リフレッシュ
  - DuckDB への保存関数（save_*）
- data/schema.py
  - DuckDB の全スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) で初期化
- data/pipeline.py
  - 日次 ETL パイプライン（run_daily_etl）
  - 差分取得・バックフィル・品質チェック
- data/news_collector.py
  - RSS 取得・前処理・記事ID生成（SHA-256）・DuckDB への保存
  - 銘柄コード抽出・news_symbols への紐付け
- data/calendar_management.py
  - 営業日判定、前後営業日の算出、カレンダー更新ジョブ
- data/audit.py
  - 監査ログ用スキーマ（signal_events / order_requests / executions）
  - init_audit_schema / init_audit_db
- data/quality.py
  - データ品質チェック（欠損 / スパイク / 重複 / 日付整合性）
- config.py
  - 環境変数読み込み（.env/.env.local の自動読み込み、無効化フラグあり）
  - 必須環境変数チェック、settings オブジェクト経由で取得

---

## 要求環境

- Python 3.10+
- 主要依存ライブラリ（例、requirements.txt に記載想定）
  - duckdb
  - defusedxml
  - そのほか標準ライブラリのみで動作するモジュール多数

パッケージを開発環境にインストールするには（プロジェクトルートで）:

```bash
pip install -e .            # または requirements.txt を使う
```

（実際の配布方法はプロジェクト側の packaging に従ってください）

---

## セットアップ手順

1. Python 3.10+ の環境を用意する（venv など推奨）。

2. 依存ライブラリをインストールする：

   ```bash
   pip install duckdb defusedxml
   ```

3. 必要な環境変数を設定する（.env をプロジェクトルートに配置すると自動読み込みされます）。最低限必要なキー：

   - JQUANTS_REFRESH_TOKEN （必須）
   - KABU_API_PASSWORD （kabuステーション API 用）
   - SLACK_BOT_TOKEN （通知用）
   - SLACK_CHANNEL_ID （通知用）
   - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   例（.env）:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   自動的に .env と .env.local をプロジェクトルートから読み込みます。読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテスト用）。

4. DuckDB のスキーマ初期化：

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

   またはインメモリ DB:

   ```python
   conn = init_schema(":memory:")
   ```

---

## 使い方（主要な例）

基本的なワークフロー例を示します。

- 日次 ETL を実行する

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 引数で target_date, id_token 等を渡せます
print(result.to_dict())
```

- ニュース収集ジョブを実行する

```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（抽出条件）。渡さないと紐付けはスキップされます。
known_codes = {"7203", "6758", "9432"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

- J-Quants ID トークンを直接取得する（例外は propagate）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用
```

- カレンダー更新バッチを実行する

```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved:", saved)
```

- 監査スキーマを初期化する（既存 conn に追加）

```python
from kabusys.data.audit import init_audit_schema
# conn は init_schema で得た接続
init_audit_schema(conn, transactional=True)
```

---

## 環境変数 / 設定（主要なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot Token（必須）
- SLACK_CHANNEL_ID: Slack Channel ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 用パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境（development | paper_trading | live）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" を設定すると .env の自動読み込みを無効化

設定は `kabusys.config.settings` オブジェクトから取得できます。

---

## ロギング設定

ライブラリは標準の logging を使います。アプリ側で適宜ハンドラやフォーマットを設定してください。例:

```python
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
```

LOG_LEVEL 環境変数で設定を制御する場合はアプリ起動時に settings.log_level を参照してロギングレベルを設定してください。

---

## 注意点 / 実装上の留意点

- Python 3.10 以上（PEP 604 の組合せ型（|）を使用）
- J-Quants API のレート制限（120 req/min）に合わせて内部でスロットリングしています。大量データ取得の際は時間に注意してください。
- jquants_client の HTTP リトライは 408/429/5xx 等に対応。401 はトークンリフレッシュで 1 回自動リトライします。
- NewsCollector は外部フィードからの RSS を扱うため、SSRF・XML 攻撃・大容量レスポンス対策が施されています。
- DuckDB の操作はトランザクションで行われますが、DDL 系は呼び出し方によってはトランザクション境界に注意してください（audit.init_audit_schema の transactional 引数参照）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要な構成は以下の通りです（src 配下）:

- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (環境変数 / 設定管理)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント)
    - news_collector.py (RSS ニュース収集)
    - schema.py (DuckDB スキーマ定義・初期化)
    - pipeline.py (ETL パイプライン)
    - calendar_management.py (マーケットカレンダー管理)
    - audit.py (監査ログスキーマ)
    - quality.py (データ品質チェック)
  - strategy/
    - __init__.py (戦略関連モジュール格納場所)
  - execution/
    - __init__.py (注文・発注インターフェース格納場所)
  - monitoring/
    - __init__.py (監視関連コード置き場)

---

## 貢献 / 拡張案

- kabuステーションとの注文送信、約定取り込み（execution 層）の実装
- 戦略モジュール（strategy）とポートフォリオオプティマイザの追加
- モニタリング用のメトリクス収集（Prometheus など）
- NewsCollector のソース追加、NLP による自動銘柄抽出の高度化

---

必要であれば README に含める具体的な .env.example、requirements.txt、あるいは CI / Cron での ETL スケジュール例（systemd timer / cron / Airflow）なども追加します。どの情報を優先して追記しますか？