# KabuSys

日本株向け自動売買プラットフォームのコアモジュール群です。  
主にデータ収集（J‑Quants / RSS）、ETL、データ品質チェック、DuckDB スキーマ定義、監査ログ（発注→約定のトレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なデータプラットフォーム部分を担う Python パッケージです。  
主な役割は以下です。

- J‑Quants API から株価・財務・マーケットカレンダーを取得し DuckDB に永続化
- RSS ベースのニュース収集と銘柄抽出（raw_news / news_symbols）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（シグナル→発注→約定のUUIDトレース）向けスキーマ
- 品質チェック（欠損・スパイク・重複・日付不整合）

設計方針としては「冪等性」「Look‑ahead bias 回避（fetched_at 記録）」「API レート制限順守」「堅牢なエラーハンドリング」を重視しています。

---

## 主な機能一覧

- 環境設定管理（自動でプロジェクトルートの `.env` / `.env.local` をロード）
- J‑Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期BS/PL）、マーケットカレンダーを取得
  - レートリミット（120 req/min）とリトライ（指数バックオフ、401 の自動リフレッシュ含む）
  - DuckDB への冪等な保存（ON CONFLICT を利用）
- ニュース収集（RSS）
  - URL正規化・トラッキング削除・SSRF対策・XML脆弱性対策（defusedxml）
  - raw_news への冪等保存、news_symbols への銘柄紐付け
- DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit）
- ETL パイプライン（run_daily_etl）
  - 差分取得、バックフィル、品質チェックのワンストップ実行
- データ品質チェックモジュール（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（営業日判定、更新バッチ）
- 監査ログスキーマ（signal_events / order_requests / executions）

---

## セットアップ手順

前提
- Python 3.9+（型アノテーションに Path | None 構文や typing を使用）
- 適切な pip 環境

1. リポジトリをクローン／配置（例: プロジェクトルートが `.git` または `pyproject.toml` を持つこと）
2. 必要パッケージをインストール（最低限）
   - duckdb
   - defusedxml

例:
```bash
pip install duckdb defusedxml
```

（プロジェクト全体の依存管理がある場合は pyproject.toml / requirements.txt を使ってください）

3. 環境変数の準備
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を作成します。自動ロード機能により起動時に読み込まれます（無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

推奨する最小 `.env` の例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

環境変数の説明（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）: J‑Quants の refresh token
- KABU_API_PASSWORD（必須）: kabu ステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）: Slack 通知用
- DUCKDB_PATH（任意）: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（任意）: 監視用 sqlite path（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live のいずれか
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

---

## 使い方（クイックスタート）

以下は最小限の利用例です。Python スクリプトや REPL から操作します。

1) 設定読み取り
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

2) DuckDB スキーマ初期化（最初に一度だけ）
```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)  # ファイル作成 & テーブル作成
```

3) 日次 ETL の実行（株価・財務・カレンダーの差分取得 + 品質チェック）
```python
from kabusys.data import pipeline
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)  # 既存 DB に接続（init_schema済みを想定）
result = pipeline.run_daily_etl(conn)  # 引数で target_date, id_token 等を指定可
print(result.to_dict())
```

4) ニュース収集（RSS）
```python
from kabusys.data import news_collector, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
# known_codes は銘柄抽出に使う有効コードのセット（例: set(["7203","6758"])）
res = news_collector.run_news_collection(conn, known_codes=set(), sources=None)
print(res)  # {source_name: 新規保存件数}
```

5) 監査ログ DB 初期化（監査専用DBを分離する場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

6) J‑Quants の id_token を明示的に取得する
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を利用
```

注意点:
- run_daily_etl 等は内部で品質チェック（kabusys.data.quality）を呼びます。品質エラーや問題は ETLResult の quality_issues / errors に集約されます。
- J‑Quants API はレート制限（120 req/min）を守るため内部でスロットリングが働きます。
- 自動で id_token をリフレッシュするロジックがあり、401 を受けたときは 1 回だけ再取得して再試行します。

---

## よく使う API（要約）

- kabusys.config.settings — 環境変数ラッパー（プロパティで各種設定を取得）
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化（全テーブル）
- kabusys.data.schema.get_connection(db_path) — 既存 DB へ接続
- kabusys.data.jquants_client.get_id_token(refresh_token=None) — id_token 取得
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar — データ取得
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar — DuckDB へ冪等保存
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection — RSS 取得と保存
- kabusys.data.pipeline.run_daily_etl — 日次 ETL のエントリポイント
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / calendar_update_job — カレンダー関連ユーティリティ
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログ用スキーマ初期化
- kabusys.data.quality.run_all_checks — 品質チェック実行

---

## 注意事項・セキュリティ

- .env 読み込みは自動だが、テストや特殊環境では環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化できます。
- news_collector は SSRF 対策（スキーム検証、プライベートホスト拒否、リダイレクト検査）および XML 脆弱性対策（defusedxml）を実装しています。外部 URL を扱うためこれらの対策は重要です。
- DuckDB に保存するデータは一貫して UTC を意識している箇所があります（特に監査ログは SET TimeZone='UTC' を設定）。
- API 呼び出しはレート制限、リトライ、指数バックオフを備えますが、実際の運用では監視と適切なエラー処理を行ってください。

---

## ディレクトリ構成

主要なファイル／モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py  — J‑Quants API クライアント（取得・保存ロジック）
    - news_collector.py  — RSS ニュース収集・前処理・保存
    - schema.py  — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py  — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - audit.py  — 監査ログスキーマ（signal/events/order_requests/executions）
    - quality.py  — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py  — （戦略層のプレースホルダ）
  - execution/
    - __init__.py  — （発注/ブローカ連携のプレースホルダ）
  - monitoring/
    - __init__.py  — （監視モジュールのプレースホルダ）

---

## 開発・拡張のヒント

- strategy / execution / monitoring パッケージは軽量に用意されています。実際の戦略ロジックやブローカー連携はこれらに実装してください。
- ETL の再現性を高めるため、pipeline.run_daily_etl は id_token を引数で注入できます。テスト時は明示的にトークンを渡すとモックが容易です。
- DuckDB の SQL はパラメータバインド（?）を多用しており、SQL インジェクションリスクが低減されています。新しいクエリを追加する際もパラメータバインドを心がけてください。
- ニュース収集で銘柄抽出を行う際は、known_codes を最新の銘柄リストで与えると精度が向上します。

---

問題報告・貢献
- バグや改善提案は issue を立ててください。プルリクエストも歓迎します。

以上が README の要約です。環境構築や具体的な利用シナリオ（cronジョブで nightly ETL を動かす、Slack 通知、監査ログの活用等）について、必要であれば追加のサンプルや手順を書きます。どの用途の例が必要ですか？