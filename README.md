# KabuSys

日本株向けの自動売買データ基盤・ETL・監査モジュール群です。  
J-Quants や RSS 等の外部データを取得して DuckDB に格納し、品質チェック・カレンダー管理・ニュース収集・監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象とする自動売買システムのデータプラットフォーム部分を実装した Python パッケージです。主に以下を目的とします。

- J-Quants API を用いた株価（日足）・財務・市場カレンダーの取得
- RSS からのニュース収集と銘柄紐付け
- DuckDB を用いたスキーマ管理（Raw / Processed / Feature / Execution 層）
- ETL（差分取得・バックフィル・品質チェック）のパイプライン化
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマ
- SSRF / XML Bomb 等を考慮した安全な外部データ収集

設計上の特徴：
- J-Quants クライアントにレートリミッター（120 req/min）とリトライ（指数バックオフ）を実装
- ETL は冪等（ON CONFLICT ...）で何度実行しても安全
- ニュース収集は URL 正規化・トラッキングパラメータ除去・ID は SHA-256 を利用して冪等化
- DuckDB により軽量で高速なオンディスク DB を利用

---

## 機能一覧

- data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
  - レート制御・リトライ・自動トークンリフレッシュ
- data.news_collector
  - RSS フィード取得（SSRF 対策・gzip サイズ制限）
  - テキスト前処理、記事ID生成、DuckDB への冪等保存（raw_news / news_symbols）
  - 銘柄コード抽出ロジック（4桁コード）
- data.schema
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution 層）と初期化関数 init_schema/get_connection
- data.pipeline
  - 差分 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 日次統合 ETL run_daily_etl（品質チェックを含む）
- data.calendar_management
  - 営業日判定・次/前営業日・期間の営業日リスト取得
  - カレンダーの夜間更新ジョブ calendar_update_job
- data.quality
  - 欠損・スパイク・重複・日付不整合のチェック（run_all_checks）
- data.audit
  - 監査ログ用テーブル定義・初期化（init_audit_schema / init_audit_db）
- settings/config
  - .env / .env.local / OS 環境変数からの設定読み込み、自動ロード機能

---

## セットアップ手順

前提
- Python 3.9+（型注釈により 3.9 以上を想定）
- duckdb, defusedxml 等のパッケージが必要

例: 仮想環境作成・基本パッケージインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# その他プロジェクト依存があれば追加でインストールしてください
```

環境変数 / .env
- プロジェクトルートに `.env` と `.env.local` を置くと自動読み込みされます（優先度: OS 環境 > .env.local > .env）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

推奨する環境変数（例）
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
# KABU_API_BASE_URL はオプション（デフォルト http://localhost:18080/kabusapi）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development  # (development|paper_trading|live)
LOG_LEVEL=INFO
```

DuckDB スキーマ初期化（例）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

監査ログスキーマ（別DBまたは同一接続）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
# または独立DBで
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（サンプル）

1) スキーマ作成と ETL の実行（日次）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

2) ニュース収集ジョブ（既知銘柄セットを与えて紐付け）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードセット（例: {"7203", "6758"}）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)  # {source_name: 新規保存数}
```

3) J-Quants から直接取得
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

4) 品質チェックのみ実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

ログレベルは環境変数 `LOG_LEVEL` で制御できます。

---

## 注意事項・設計上のポイント

- J-Quants クライアントは 120 req/min のレート制限を遵守するよう固定間隔スロットリングを行います。エラー時は指数バックオフで最大 3 回リトライします。401 は自動でリフレッシュ（1 回）して再試行します。
- ニュース収集は SSRF、XML Bomb、GZip ブロット等の攻撃に対する対策を実装しています。最大受信サイズは 10MB に制限されています。
- ETL・保存処理は冪等に設計されています（DuckDB 側で ON CONFLICT を使用）。再実行による二重挿入リスクは低くなっています。
- .env のパースはシェル形式をある程度サポートしています（export キーワード、クォート、コメント処理など）。
- テストや CI で自動環境変数ロードを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

主要モジュール / ファイル一覧（src/kabusys）

- __init__.py
- config.py  — 環境変数/設定管理
- data/
  - __init__.py
  - jquants_client.py         — J-Quants API クライアント、保存ロジック
  - news_collector.py        — RSS 取得・前処理・保存・銘柄抽出
  - schema.py                — DuckDB スキーマ定義と init_schema/get_connection
  - pipeline.py              — ETL パイプライン（差分更新、run_daily_etl）
  - calendar_management.py   — 市場カレンダー管理（営業日判定等）
  - audit.py                 — 監査ログスキーマの初期化
  - quality.py               — データ品質チェック
- strategy/                   — 戦略関連（将来的に拡張）
- execution/                  — 発注・ブローカー連携（将来的に拡張）
- monitoring/                 — 監視関連（将来的に拡張）

---

## 開発・拡張ガイド（簡単に）

- 新しい ETL ジョブを追加する場合は data.pipeline にて差分取得ロジック + jq.fetch_*/save_* の組合せで実装してください。
- 新しいテーブルを追加する場合は data.schema の DDL に追加し、init_schema に反映してください（外部キー順に注意）。
- ニュースのパーサや RSS ソース追加は data.news_collector の DEFAULT_RSS_SOURCES を拡張できます。

---

README はここまでです。必要であれば、実行例の詳細や CI 設定用のサンプル（GitHub Actions）・.env.example を追記します。どの情報を優先して追加しますか？