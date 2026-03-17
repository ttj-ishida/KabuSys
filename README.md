# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群（プロトタイプ実装）

このリポジトリは、J-Quants 等の外部データソースからのデータ取得、DuckDB を使ったスキーマ管理・ETL、ニュース収集、データ品質チェック、及び監査ログ（発注→約定のトレーサビリティ）を中心としたコンポーネントを含むモジュール群です。戦略や発注実装（execution／strategy／monitoring）は別レイヤとして想定されています。

主な設計方針
- データ取得はレート制限・リトライ・トークン自動更新を組み込んだ堅牢な実装
- DuckDB を中心とした三層（Raw / Processed / Feature） + Execution 層のスキーマ設計
- ニュース収集は SSRF や XML Bomb 等を考慮した安全実装
- 品質チェック（欠損・重複・スパイク・日付不整合）を ETL 流れに組み込み
- 監査ログでシグナル→発注→約定のフローを UUID 連鎖で完全トレース可能に

---

## 機能一覧

- 環境変数管理（自動 .env ロード、必須チェック）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 四半期財務データ取得
  - マーケットカレンダー取得
  - レートリミット（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- ニュース収集モジュール
  - RSS フィード取得、前処理、記事ID生成（正規化URL→SHA-256先頭32文字）
  - SSRF対策、受信サイズ制限、defusedxml による安全パース
  - DuckDB への冪等保存（INSERT ... RETURNING）、銘柄抽出と紐付け
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義、初期化ユーティリティ（init_schema, init_audit_schema）
- ETL パイプライン
  - 差分更新（バックフィル対応）、カレンダー先読み、品質チェック統合
  - run_daily_etl による一括実行（結果は ETLResult オブジェクト）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue）
- 監査ログ（audit）
  - signal_events / order_requests / executions の初期化ユーティリティ

注: strategy、execution、monitoring の実装はパッケージ構成に準備されていますが、個別のロジックは用途に合わせて実装してください。

---

## 動作環境・依存

- Python 3.10 以上（PEP 604 の | 型注釈などを使用）
- 必要パッケージ（一例）
  - duckdb
  - defusedxml

開発時は requirements.txt を用意して pip install することを推奨します。最低限は以下をインストールしてください。

例:
pip install duckdb defusedxml

（プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローンし仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml

   （プロジェクトに依存リストがあれば pip install -r requirements.txt または pip install -e .）

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると自動で読み込まれます（読み込みは起動時に行われます）。
   - 自動ロードを無効化する場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
   - KABU_API_PASSWORD: kabu API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

   例 .env（サンプル）
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

---

## データベース初期化

DuckDB スキーマを初期化するには、Python から以下を実行します:

例: Python 一行コマンドで初期化
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

また監査ログテーブルを追加で初期化する場合:
python -c "from kabusys.data.schema import init_schema; conn=init_schema('data/kabusys.duckdb'); from kabusys.data.audit import init_audit_schema; init_audit_schema(conn)"

- db_path に ":memory:" を与えるとインメモリ DB が作成されます。
- 親ディレクトリが存在しない場合は自動作成されます。

---

## 使い方（主な API）

以下は代表的な利用例の抜粋です。実運用向けには適宜ラッパーや CLI を実装してください。

1) ETL（日次パイプライン）の実行

from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回のみ）
conn = init_schema("data/kabusys.duckdb")

# 日次ETL 実行（引数で target_date, id_token, etc. を与えられる）
result = run_daily_etl(conn)
print(result.to_dict())

2) ニュース収集の実行（RSS）

from datetime import datetime
import duckdb
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = duckdb.connect("data/kabusys.duckdb")
# known_codes は銘柄コードセット（抽出用）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)

3) J-Quants からデータを直接取得して保存

from kabusys.data import jquants_client as jq
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# トークン省略時は settings.jquants_refresh_token を利用
records = jq.fetch_daily_quotes(date_from=datetime(2024,1,1).date(), date_to=datetime(2024,1,31).date())
saved = jq.save_daily_quotes(conn, records)
print(f"saved={saved}")

4) 品質チェック（手動実行）

from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i)

---

## 自動 .env 読み込みの挙動

- 起動時にプロジェクトルート（.git または pyproject.toml が見つかったディレクトリ）から `.env` を読み込みます。
- 読み込み順: OS 環境変数 > .env.local (override=True) > .env (override=False)
- テスト等で自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env のパースは export KEY=val 形式やクォート付き値、行内コメント等に対応しています。

---

## 注意点・実装上のポイント

- J-Quants クライアントはレート制限（120 req/min）を守るため固定間隔スロットリングを行います。大量の並列リクエストは避けてください。
- HTTP リトライは指数バックオフ（最大3回）。401 受信時はリフレッシュトークンで id_token を自動取得して 1 回リトライします。
- ニュース収集は SSRF、XML Bomb、Gzip Bomb といった攻撃を意識した実装になっています。外部から RSS URL を受け付ける際は追加の検証を行ってください。
- DuckDB の保存は冪等性を意識した SQL（ON CONFLICT）を使用していますが、外部から DB を直接書き換えた場合は重複検出などの整合性チェックが必要です。
- 現状、strategy / execution / monitoring の具象実装は含まれていません。フレームワークとしてデータ層・監査層を提供する構成です。

---

## ディレクトリ構成

リポジトリの主要ファイル構成（抜粋）:

src/
  kabusys/
    __init__.py
    config.py                    # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py          # J-Quants API クライアント（取得＋DuckDB保存）
      news_collector.py          # RSS ニュース収集・前処理・DB保存
      pipeline.py                # ETL パイプライン（差分更新 / 品質チェック）
      schema.py                  # DuckDB スキーマ定義と初期化
      audit.py                   # 監査ログ（signal/order/execution）用DDLと初期化
      quality.py                 # データ品質チェック
    strategy/
      __init__.py                # 戦略層（実装は利用者が追加）
    execution/
      __init__.py                # 発注・ブローカ連携層（実装は利用者が追加）
    monitoring/
      __init__.py                # 監視・アラート層（実装は利用者が追加）

---

## 開発・テストに関するヒント

- テスト時に本番 API を叩かない場合は、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` やモジュール内の HTTP 呼び出し (`kabusys.data.news_collector._urlopen` や `urllib.request.urlopen`) をモックして使ってください。
- DuckDB の :memory: を使うとテスト容易性が高まります（db_path=":memory:"）。
- ロギングは settings.log_level に従います。開発時は DEBUG を指定すると内部処理ログが確認しやすいです。

---

README にある使い方はライブラリレベルの基本的な利用例に留めています。本プロジェクトを運用環境で使用する場合は、運用用のラッパー・ジョブ管理（cron / Airflow / Prefect 等）、監視、リスク管理（発注前の制御）、およびセキュリティ要件に基づく追加実装を行ってください。