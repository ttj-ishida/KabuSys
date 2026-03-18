# KabuSys

日本株自動売買プラットフォームのためのライブラリ群（KabuSys）。  
データ取得・ETL・品質チェック・ニュース収集・マーケットカレンダー管理・監査ログ（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なデータ基盤とユーティリティを提供する Python パッケージです。主に以下を扱います。

- J-Quants API から株価・財務・市場カレンダーを取得し DuckDB に保存
- RSS からニュースを収集して前処理・DB保存（銘柄紐付け含む）
- ETL（差分更新・バックフィル）パイプライン
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダーの管理（営業日判定、前後営業日の取得など）
- 監査ログ（シグナル→発注→約定のトレース）用スキーマ初期化

設計上のポイント:
- J-Quants API のレート制限（120 req/min）を順守するレートリミッタを実装
- リトライ（指数バックオフ、最大3回）・401時のトークン自動リフレッシュ対応
- DuckDB への保存は冪等（ON CONFLICT を使用）
- ニュース収集は SSRF/XML BOM 等の脆弱性対策あり
- すべてのタイムスタンプは UTC を想定（監査等で UTC 固定）

---

## 機能一覧

- config: 環境変数の読み込み（.env / .env.local 自動読込、保護・上書き制御）
- data:
  - jquants_client: J-Quants API クライアント（取得/保存/認証/ページネーション/リトライ）
  - news_collector: RSS 取得・正規化・前処理・DuckDB への保存・銘柄抽出
  - schema: DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 日次 ETL（差分取得・バックフィル・品質チェック）
  - calendar_management: カレンダー更新ジョブ・営業日判定ユーティリティ
  - audit: 監査用スキーマ初期化（signal / order_request / executions）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
- strategy / execution / monitoring: パッケージ構成のプレースホルダ（将来的な戦略・実行・監視モジュール）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の | 型注釈を使用）
- duckdb, defusedxml などの依存パッケージ

例: 仮想環境作成と依存インストール（適宜プロジェクトの requirements を用意してください）

```bash
# 仮想環境 (例)
python -m venv .venv
source .venv/bin/activate

# 必要パッケージをインストール
pip install duckdb defusedxml
# 追加で requests 等が必要ならインストールしてください
```

環境変数
- 必須:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API のパスワード
  - SLACK_BOT_TOKEN: Slack 通知用トークン
  - SLACK_CHANNEL_ID: 通知先チャンネル ID
- 任意 / デフォルト:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます

自動的にプロジェクトルート（.git または pyproject.toml の存在）を探して
`.env` → `.env.local` の順で読み込みます（OS 環境変数優先）。  
テストなどで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

## 使い方（主要な例）

以下は Python スクリプトやインタラクティブでの利用例です。

1) DuckDB スキーマ初期化

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection オブジェクト
```

2) 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # 引数省略で当日を対象に実行
print(result.to_dict())
```

3) ニュース収集ジョブを実行する

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes を与えると記事と銘柄の紐付けを行う
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source_name: new_count, ...}
```

4) J-Quants から直接データ取得（テスト用など）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

5) マーケットカレンダー更新ジョブ（夜間バッチ）

```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
```

6) 監査スキーマ初期化（監査専用 DB を使う場合）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# もしくは既存 conn に対して init_audit_schema(conn)
```

7) 品質チェックを個別に / 一括で実行

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for issue in issues:
    print(issue)
```

ログレベルは環境変数 LOG_LEVEL で制御できます。

---

## ディレクトリ構成

主要ファイルを抜粋したツリー構成（src 側）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - calendar_management.py
      - schema.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主要モジュールの概要:
- kabusys.config: 環境変数読み取り・管理（.env 自動ロード、必須キーチェック）
- kabusys.data.schema: DuckDB の全テーブル（Raw/Processed/Feature/Execution）定義と初期化
- kabusys.data.jquants_client: J-Quants API クライアント（レート制御・リトライ・保存）
- kabusys.data.news_collector: RSS 取得 → 前処理 → raw_news 保存、銘柄コード抽出
- kabusys.data.pipeline: 日次 ETL の orchestration（差分更新・バックフィル・品質チェック）
- kabusys.data.calendar_management: カレンダー更新・営業日操作ユーティリティ
- kabusys.data.audit: 監査ログ用スキーマ（signal / order_request / executions）
- kabusys.data.quality: 各種データ品質チェック

---

## 注意事項 / 補足

- Python バージョン: 3.10 以上を想定（型注釈の | 記法等）。
- 依存ライブラリ: duckdb, defusedxml 等（プロジェクトの requirements.txt を用意してください）。
- J-Quants API 利用時は API 利用規約・商用利用の制限を確認してください。
- jquants_client はレートリミッタ・リトライ・401リフレッシュ等を組み込んでいますが、実運用ではログ監視やモニタリングを追加してください。
- ニュース収集では SSRF・XML 脆弱性対策（リダイレクト検査・defusedxml・受信サイズ制限）を実装していますが、追加のセキュリティ要件に応じて設定を調整してください。
- DuckDB に保存される日時は UTC を想定しています（監査用スキーマは明示的に TimeZone を UTC に設定します）。

---

もし README に追加したい情報（例: 実運用の Docker 設定、CI/CD、より詳細な API 使用例、requirements.txt の候補など）があれば教えてください。必要に応じて追記します。