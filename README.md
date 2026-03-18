# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
J-Quants API から市場データや財務データを取得し、DuckDB に蓄積して ETL・データ品質チェック・ニュース収集・監査ログなどを行うためのモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から株価（日足）・財務情報・市場カレンダーを取得して DuckDB に永続化
- RSS フィードからニュースを収集・正規化して DuckDB に保存し、銘柄コードと紐付け
- ETL パイプライン（差分取得・バックフィル・品質チェック）を提供
- 市場カレンダーの管理（営業日の判定や翌営業日の検索）
- 監査ログ（シグナル→発注→約定 のトレーサビリティ）を DuckDB に作成

設計上のポイント:

- API レート制限（J-Quants: 120 req/min）に準拠するレートリミッタ実装
- リトライ＋指数バックオフ（HTTP 408/429/5xx 対応）、401 発生時はトークン自動リフレッシュ
- DuckDB への保存は冪等性（ON CONFLICT）を考慮
- XML の安全パース（defusedxml）や SSRF / Gzip Bomb 等の防御を考慮

---

## 機能一覧

主な提供機能:

- data:
  - jquants_client: J-Quants API クライアント（株価・財務・カレンダー取得、DuckDB 保存用関数）
  - pipeline: 日次 ETL（差分取得・バックフィル・品質チェック）
  - news_collector: RSS 取得・記事正規化・DuckDB 保存・銘柄抽出
  - schema: DuckDB スキーマ定義/初期化
  - calendar_management: 営業日判定 / next/prev_trading_day / カレンダー更新ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ用スキーマ（signal, order_request, executions 等）
- config:
  - 環境変数から設定を読み込み、Settings オブジェクトを提供
  - .env / .env.local を自動ロード（無効化可能）
- strategy / execution / monitoring:
  - パッケージ構造は用意済み（実装は各モジュールに拡張可能）

---

## 要件（推奨環境）

- Python 3.10 以上（型アノテーションのユニオン記法などを使用）
- 依存パッケージ（少なくとも）:
  - duckdb
  - defusedxml

インストールはプロジェクトの pyproject.toml / requirements に従ってください。簡易的には:

pip install -e . もしくは
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動

2. 仮想環境作成（推奨）

python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

pip install -e .         # パッケージを開発モードでインストール（pyproject の設定がある場合）
# または最低限
pip install duckdb defusedxml

4. 環境変数設定
プロジェクトルートに .env ファイルを作成するか、OS 環境変数として設定します。必須の環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack ボットのトークン（通知等で使用する場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID

オプション / デフォルト値:

- KABUSYS_ENV: environment ("development", "paper_trading", "live")。デフォルト "development"
- LOG_LEVEL: ログレベル（"DEBUG","INFO",...）。デフォルト "INFO"
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます（テスト向け）

5. DuckDB 初期化
デフォルトの DB 保存先は settings.duckdb_path -> "data/kabusys.duckdb"（環境変数 DUCKDB_PATH で変更可）

---

## 使い方（サンプル）

以下はいくつかの典型的な操作例です。Python REPL やスクリプトから利用できます。

1) DuckDB スキーマ初期化

from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# またはメモリDB
# conn = init_schema(":memory:")

2) 日次 ETL を実行する（価格・財務・カレンダーの差分取得＋品質チェック）

from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

3) ニュース収集（RSS）を実行して保存・銘柄紐付け

from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードの集合
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}

4) 市場カレンダー夜間更新ジョブ

from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)

5) J-Quants の価格 API を直接叩く（トークン自動リフレッシュ対応）

from kabusys.data.jquants_client import fetch_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(quotes))

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants の refresh token
- KABU_API_PASSWORD (必須): kabu API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack Bot Token
- SLACK_CHANNEL_ID (必須): Slack Channel ID
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視等に使う SQLite のパス（デフォルト data/monitoring.db）
- KABUSYS_ENV: "development"|"paper_trading"|"live"（デフォルト development）
- LOG_LEVEL: "DEBUG"|"INFO"|...（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

注意: パッケージは起動時にプロジェクトルート（.git または pyproject.toml を探索）を見つけ、.env / .env.local を自動で読み込みます。自動読み込みを無効にしたい場合は上記変数を設定してください。

---

## ディレクトリ構成

プロジェクトは src 配下にパッケージとして配置されています。主要ファイル:

- src/kabusys/
  - __init__.py
  - config.py              -- 環境変数 / Settings 管理
  - data/
    - __init__.py
    - jquants_client.py    -- J-Quants API クライアント（取得/保存/認証/リトライ）
    - news_collector.py    -- RSS ニュース収集・正規化・保存・銘柄抽出
    - pipeline.py          -- ETL パイプライン（差分取得 / 品質チェック）
    - schema.py            -- DuckDB スキーマ定義・初期化
    - calendar_management.py -- カレンダー更新 / 営業日判定ロジック
    - audit.py             -- 監査ログ用スキーマ（signal/order_request/executions）
    - quality.py           -- データ品質チェック
    - (その他)
  - strategy/               -- 戦略用モジュール（拡張ポイント）
  - execution/              -- 発注/取引実行関連（拡張ポイント）
  - monitoring/             -- 監視関連（拡張ポイント）

---

## 開発・テスト時のメモ

- XML のパースには defusedxml を使っているため、外部からの悪意ある XML に対する防御がなされています。
- RSS の取得では SSRF 防止のためスキーム検証 / ホストのプライベート判定 / リダイレクト時の検査 / レスポンス最大サイズ制限 を設けています。
- J-Quants API へのリクエストは固定間隔スロットリングでレート制御しています。
- DuckDB への保存は多くの関数で ON CONFLICT 対応があり冪等に動作します。
- テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを抑止できます。

---

## 貢献 / ライセンス

本ドキュメントではライセンス情報は含めていません。プロジェクトルートの LICENSE ファイルを参照してください。バグ報告・機能追加は Issue / Pull Request を通じて歓迎します。

---

必要であれば、運用上の具体的な systemd タスク / cron ジョブの例や、Docker コンテナでの実行例なども追加できます。必要な場合は用途（ETL スケジューリング、監視、CI 連携等）を教えてください。