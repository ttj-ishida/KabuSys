# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ KabuSys の README です。  
このリポジトリは、J-Quants 等の外部 API から市場データを取得して DuckDB に保存し、品質チェック・ニュース収集・監査ログ・ETL パイプライン等を提供します。

## プロジェクト概要
KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API から株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを安全かつ効率的に取得
- DuckDB を用いたスキーマ設計（Raw / Processed / Feature / Execution / Audit レイヤ）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と銘柄紐付け（SSRF・XML攻撃対策、サイズ制限などを実装）
- 発注・約定・監査ログ用スキーマ（監査トレーサビリティ）

設計上の主要ポイント:
- API レート制御・リトライ・トークン自動リフレッシュ
- ETL の冪等性（ON CONFLICT での上書き/排除）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集のセキュリティ対策（defusedxml、SSRF ブロック、レスポンスサイズ制限）

## 主な機能一覧
- data:
  - jquants_client: J-Quants からデータ取得（fetch / save）・認証ロジック・レートリミット
  - schema: DuckDB のスキーマ定義および初期化（init_schema）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）の実装（run_daily_etl 等）
  - news_collector: RSS 収集、前処理、記事保存、銘柄抽出・紐付け
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 発注〜約定をトレースする監査スキーマと初期化関数
  - quality: データ品質チェック関数群（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
- config:
  - 環境変数管理: .env / .env.local の自動読み込み（プロジェクトルート検出）、Settings オブジェクト経由で設定値取得

（strategy / execution / monitoring 用のパッケージ雛形あり）

## 前提条件
- Python 3.10+（コードは型ヒントに | を使用）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
- （実運用では J-Quants / kabu API のアクセス情報が必要）

依存パッケージはこのリポジトリに requirements.txt があればそれを使用してください。無ければ上記を pip でインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# または: pip install -r requirements.txt
```

## セットアップ手順

1. リポジトリをクローン / checkout
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動的に読み込まれます。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID — Slack 送信先チャンネル ID
   - 任意（デフォルト値あり）:
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) (default: development)
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (default: INFO)

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=XXXXXXXX
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. DuckDB スキーマ初期化
   - data/schema.init_schema() を使って DB を初期化します。例:

```bash
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```

これにより必要なテーブル群とインデックスが作成されます。

## 使い方（簡易ガイド）

以下はライブラリの主要な API を使う例です。実際はスクリプトやジョブとして組み込みます。

- DuckDB 接続を取得 / 初期化

```python
from kabusys.data.schema import init_schema, get_connection
# 初期化（ファイルがなければディレクトリも作成されます）
conn = init_schema("data/kabusys.duckdb")
# 既存 DB に接続するだけなら:
# conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- 個別 ETL ジョブを呼ぶ（価格のみ等）

```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

- カレンダー（夜間バッチ）更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
```

- ニュース収集ジョブ（RSS → raw_news に保存、銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は有効な銘柄コードのセット（例: 上場銘柄リスト）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
```

- J-Quants の個別取得（例: 日足）

```python
from kabusys.data.jquants_client import fetch_daily_quotes
records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
```

- 監査スキーマ初期化（audit 用 DB、または既存接続へ追加）

```python
from kabusys.data.audit import init_audit_db, init_audit_schema
# 専用 DB を作る場合
audit_conn = init_audit_db("data/audit.duckdb")
# 既存 conn に監査スキーマだけ追加する場合
init_audit_schema(conn)
```

## 設定・動作の注意点
- 環境変数は Settings クラス（kabusys.config.settings）を通じて取得します。未設定の必須変数にアクセスすると ValueError が発生します。
- .env 読み込み順:
  - OS 環境変数（優先）
  - .env
  - .env.local（.env.local は .env の上書き）
- API レート制御:
  - J-Quants は 120 req/min に制限されるため内部でスロットリングが入っています。長いページネーション取得で自動的に調整されます。
- ニュース収集のセキュリティ:
  - defusedxml を使用して XML 攻撃を防ぐ
  - リダイレクト先のスキーム・ホスト検査（SSRF 対策）
  - レスポンスサイズ上限（デフォルト 10MB）
- DuckDB の初期化は冪等（存在するテーブルはスキップ）です。監査スキーマは別関数で追加できます。

## ディレクトリ構成
リポジトリの主なファイル／ディレクトリ（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py     -- J-Quants API クライアント（fetch/save）
    - news_collector.py     -- RSS フィード収集・前処理・保存・銘柄抽出
    - schema.py             -- DuckDB スキーマ定義・初期化
    - pipeline.py           -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py-- 市場カレンダー管理・営業日判定
    - audit.py              -- 監査ログスキーマと初期化
    - quality.py            -- データ品質チェック
  - strategy/               -- 戦略関連（骨組み）
  - execution/              -- 発注 / 実行関連（骨組み）
  - monitoring/             -- 監視関連（骨組み）

（トップレベルの pyproject.toml / .git 等でプロジェクトルートを検出して .env を自動読み込みします）

## テスト・開発
- 自動環境変数読み込みを無効にしたい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト用に明示的に設定を行ってください。
- 各モジュールは id_token の注入や接続オブジェクトの注入を想定しており、ユニットテストでモックしやすく設計されています（例: news_collector._urlopen を差し替え）。

---

さらに詳しい使い方や運用手順（cron / Airflow での ETL スケジュール、Slack 通知フロー、kabu ステーションとの実稼働接続）については別途運用ドキュメントを用意してください。必要であれば README に追加する項目や具体的な運用例（systemd / Docker / Airflow 構成など）も作成します。