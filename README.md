# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・データプラットフォームのコアライブラリです。J-Quants からの市場データ取得、DuckDB を用いたデータ格納・スキーマ管理、RSS ニュース収集、ETL パイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）などを提供します。

主な目的は「取得日時のトレーサビリティ」「冪等性」「ネットワーク制御（レート/リトライ）」「SSRF 等の防御」「データ品質チェック」を担保しつつ、戦略や実行層へ安定してデータを供給することです。

---

## 機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務情報、JPX マーケットカレンダーの取得
  - レートリミット制御、再試行（指数バックオフ）、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
- DuckDB ベースのスキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - 初期化ユーティリティ（init_schema / init_audit_schema）
- ETL パイプライン
  - 差分取得（バックフィル対応）、保存（冪等）、品質チェックの実行
  - 日次 ETL エントリポイント（run_daily_etl）
- ニュース収集（RSS）
  - RSS の取得と前処理、記事ID の冪等化（正規化 URL → SHA-256）
  - SSRF 対策・gzip サイズ制限・XML ディフェンス（defusedxml）
  - raw_news / news_symbols への保存
- マーケットカレンダー管理
  - 営業日判定、前後営業日探索、夜間バッチ更新ジョブ
- データ品質チェック
  - 欠損、重複、スパイク（前日比閾値）、日付不整合の検出
  - QualityIssue オブジェクトで詳細を取得
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルで発注から約定まで追跡可能
  - UUID ベースの冪等キー（order_request_id / broker_execution_id 等）

---

## 要件

- Python 3.10+
- 主要依存パッケージ（最小限）:
  - duckdb
  - defusedxml

（プロジェクトに合わせて追加の依存が必要になる場合があります）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（例）

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール

   ```bash
   pip install duckdb defusedxml
   ```

   （実プロジェクトでは requirements.txt / pyproject.toml を用意して pip install -r でインストールしてください）

3. 環境変数の設定

   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（読み込みは config モジュールが行います）。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（最低限）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 送信先チャネル ID

   オプション（デフォルトあり）:

   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - KABUS_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite 用パス（デフォルト: data/monitoring.db）

   例 `.env`（簡易）:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（基本例）

下記は主要なユースケースのサンプルコードです。実行はプロジェクトルートから Python スクリプト / REPL で行ってください。

- DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection オブジェクト
```

- 監査ログ（Audit）テーブル初期化

```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # 既存 conn に audit テーブルを追加
```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- 個別 ETL（株価のみ）

```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl

fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- J-Quants API から直接データ取得・保存

```python
from kabusys.data import jquants_client as jq
from datetime import date

token = jq.get_id_token()  # settings.jquants_refresh_token を使用して取得
records = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

- RSS ニュース収集

```python
from kabusys.data.news_collector import run_news_collection

# known_codes を与えると記事中の4桁銘柄コードを紐付ける
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- マーケットカレンダー夜間更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"saved_calendar_records={saved}")
```

- データ品質チェックを単独で走らせる

```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn)
for issue in issues:
    print(issue)
```

---

## 設定と動作上の注意点

- 環境変数の自動ロードは `kabusys.config` モジュールで行われます。プロジェクトルートに `.env` / `.env.local` を配置すると読み込まれます。テスト等で自動ロードを禁止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- J-Quants API のレート制限（120 req/min）に対応するため内部でスロットリングしています。bulk 取得時はページネーションを利用します。
- ニュース収集では SSRF や XML Bomb、gzip サイズ上限などの防御を組み込んでいます。外部 URL のスキームは http/https のみ許可します。
- DuckDB への保存は基本的に冪等（ON CONFLICT ... DO UPDATE / DO NOTHING）で実装してあります。
- 全てのタイムスタンプは UTC を推奨して扱っています（監査ログでは SET TimeZone='UTC' を利用）。

---

## ディレクトリ構成

リポジトリの主要なファイル・ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 ：環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py       ：J-Quants API クライアント（取得・保存）
    - news_collector.py       ：RSS ニュース収集・保存ロジック
    - schema.py               ：DuckDB スキーマ定義 / 初期化
    - pipeline.py             ：ETL パイプライン（差分取得・保存・品質チェック）
    - calendar_management.py  ：マーケットカレンダー管理・バッチ
    - audit.py                ：監査ログ（発注→約定トレーサビリティ）
    - quality.py              ：データ品質チェック
  - strategy/
    - __init__.py             ：戦略層（拡張ポイント）
  - execution/
    - __init__.py             ：発注 / 実行層（拡張ポイント）
  - monitoring/
    - __init__.py             ：監視・メトリクス（拡張ポイント）

---

## 拡張ポイント

- strategy パッケージ：特徴量（features）や ai_scores を消費してシグナルを生成する戦略を実装できます。
- execution パッケージ：signal_queue → 発注ロジック → orders/trades 管理を実装する場所です。kabuステーション等のブローカー接続をここで実装します。
- monitoring：ETL や実行の可観測性を高めるためのモジュール（監視・アラート）を追加できます。

---

## 貢献・テスト

この README はコードベースの概要ドキュメントです。実運用に導入する場合は以下を検討してください。

- 追加の依存管理（pyproject.toml / requirements.txt）
- 単体テスト・統合テスト（外部 API モック）
- CI（Lint / 型チェック / テスト）
- サンプル設定ファイル（.env.example）
- ロギングおよびエラーハンドリングの運用ルール

---

ご不明点や README に追加したいサンプルがあれば教えてください。必要に応じて .env.example や簡易起動スクリプトのテンプレートも作成します。