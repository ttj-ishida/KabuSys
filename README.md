# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
J-Quants API から市場データ・財務データ・マーケットカレンダーを取得・保存し、ニュース収集、ETL、品質チェック、監査ログ（発注〜約定のトレーサビリティ）などの基盤処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした内部ユーティリティ群を含む Python パッケージです。

- J-Quants API からのデータ取得（株価日足、財務四半期データ、マーケットカレンダー）
- DuckDB を用いたデータスキーマ定義・初期化・接続管理
- ETL（差分取得・バックフィル）パイプライン
- ニュース（RSS）収集と記事→銘柄の紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）用スキーマ
- カレンダー管理（営業日判定・next/prev trading day 等）

設計上の特徴:
- API レート制限やリトライ、トークン自動リフレッシュ対応
- DuckDB への冪等保存（ON CONFLICT / ON CONFLICT DO UPDATE）
- SSRF 対策、XML パース安全化（defusedxml）、レスポンスサイズ制限などの堅牢性配慮
- ETL は差分更新・バックフィルを標準とし、品質チェックは全件収集型

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（レート制御、リトライ、トークンリフレッシュ）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存: save_daily_quotes, save_financial_statements, save_market_calendar

- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) / get_connection(db_path)

- data/pipeline.py
  - 日次 ETL 実行（run_daily_etl）
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 差分更新・バックフィルロジック・品質チェック統合

- data/news_collector.py
  - RSS フィード取得・前処理・記事ID生成（SHA-256）・DB保存（raw_news）・銘柄抽出・news_symbols への紐付け

- data/calendar_management.py
  - market_calendar の夜間差分更新ジョブ（calendar_update_job）
  - 営業日判定 API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）

- data/quality.py
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - run_all_checks による一括実行

- data/audit.py
  - 監査ログ用テーブル初期化（signal_events / order_requests / executions）
  - init_audit_schema / init_audit_db

- config.py
  - 環境変数読み込み（.env, .env.local）と Settings インターフェイス
  - 自動読み込みはプロジェクトルート (.git または pyproject.toml) を基準に行う
  - 必須環境変数チェック（_require）

---

## セットアップ手順

前提:
- Python 3.10 以上（typing における X | None を使用）
- duckdb, defusedxml などの依存パッケージ

最低インストール例（pip）:

```bash
python -m pip install --upgrade pip
pip install duckdb defusedxml
# パッケージを editable install する場合（プロジェクトルートで）
pip install -e .
```

（プロジェクトで requirements.txt や setup.cfg/pyproject.toml があればそれに従ってください。）

環境変数:
- 自動で .env / .env.local を読み込みます（プロジェクトルートが特定できる場合）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで便利）。

必須環境変数（Settings が要求するもの）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルト値あり）:
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

例: .env（プロジェクトルートに配置）

```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（簡単なコード例）

1) DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema

# ファイル DB を作成・初期化（親ディレクトリは自動作成）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants から株価・財務・カレンダー取得、品質チェック含む）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブを実行（RSS → raw_news 保存、銘柄紐付け）

```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection("data/kabusys.duckdb")
# known_codes を指定すると記事中の 4 桁数字を有効銘柄のみ抽出して紐付ける
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)  # {source_name: saved_count}
```

4) 監査ログ DB 初期化（監査専用 DB を別ファイルに持つことも可能）

```python
from kabusys.data.audit import init_audit_db

aud_conn = init_audit_db("data/audit.duckdb")
```

5) カレンダー差分更新バッチ（夜間ジョブとしてスケジューリング）

```python
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved={saved}")
```

6) 環境変数自動読み込みを無効にしてテスト時に明示的に設定

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print(settings.log_level)"
```

---

## よく使う関数一覧（参考）

- init_schema(db_path)
- get_connection(db_path)
- run_daily_etl(conn, target_date=None, run_quality_checks=True, ...)
- fetch_daily_quotes / save_daily_quotes
- fetch_financial_statements / save_financial_statements
- fetch_market_calendar / save_market_calendar
- fetch_rss / save_raw_news / run_news_collection
- run_all_checks(conn, target_date=None, ...)
- init_audit_db(db_path) / init_audit_schema(conn)
- calendar_update_job(conn)

各関数はドキュメント文字列（docstring）で詳細な引数・挙動・戻り値を記載しています。IDE や pydoc で参照してください。

---

## ディレクトリ構成

以下はコードベースの主要ファイル・モジュール構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主に data パッケージが ETL・DB・API クライアント・品質チェック・ニュース収集・監査ログを提供し、strategy / execution / monitoring は戦略や実発注、監視に関する拡張ポイントです。

---

## 運用上の注意点

- J-Quants API のレート制限（120 req/min）を意識して設計されていますが、バッチの呼び出し頻度には注意してください。
- 環境変数の取り扱いやトークンは安全に管理してください（.env はバージョン管理に含めない）。
- DuckDB ファイルは複数プロセスでの同時書き込みに注意が必要です。運用ではシングルライター設計やロックを検討してください。
- news_collector は外部 URL にアクセスします。SSRF 対策・受信サイズ制限・defusedxml による安全化等の対策を導入済みですが、運用環境での監査を推奨します。
- 品質チェックは Fail-Fast ではなく検出内容を返す設計です。検出結果に基づいて運用側でアクションを決定してください。

---

## テスト / 開発

- 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、テスト内で必要な環境変数を注入してください。
- 一部のネットワーク呼び出しはモックしやすいように内部関数を分離（例: news_collector._urlopen のモック）しています。

---

問題報告・コントリビュートの方法やライセンス情報はこのリポジトリの上位ドキュメント（LICENSE, CONTRIBUTING）に従ってください。README の追加説明やサンプルワークフローが必要であれば教えてください。