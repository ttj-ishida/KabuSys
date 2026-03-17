# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants / kabuステーション 等の外部 API から市場データ・財務データ・ニュースを収集し、DuckDB に格納・品質チェック・ETL を行うためのモジュール群を提供します。発注／監査（audit）用のスキーマやニュース収集、マーケットカレンダー管理なども含まれています。

主な設計方針：
- データ取得は冪等（ON CONFLICT / DO UPDATE 等）に実装
- API レート制限・リトライ・トークン自動リフレッシュに対応
- Look-ahead bias を避けるため取得時刻（fetched_at）を記録
- セキュリティ配慮（SSRF 対策、XML の安全パース、レスポンスサイズ制限）

バージョン: 0.1.0

---

## 機能一覧

- J-Quants API クライアント（株価日足 / 財務データ / マーケットカレンダー）
  - レート制御、リトライ、トークン自動リフレッシュ対応
  - fetch_* / save_* による取得と DuckDB 保存
- DuckDB スキーマの定義と初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブルを生成
- ETL パイプライン
  - 日次 ETL（差分取得、バックフィル、品質チェックを実行）
  - 個別ジョブ（株価・財務・カレンダー）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合等の検出
- ニュース収集モジュール
  - RSS フィード取得、前処理、記事ID生成（URL 正規化 + SHA-256）
  - SSRF 対策、gzip 上限、XML の安全パース
- マーケットカレンダー管理（営業日判定・次/前営業日取得）
- 監査ログ（audit）スキーマ
  - シグナル → 発注 → 約定 までのトレースを保証するテーブル群

---

## 要件

- Python 3.9+
- 必要パッケージ（代表例）:
  - duckdb
  - defusedxml
  - （その他、標準ライブラリのみで動く部分もあります）
- ネットワーク（J-Quants / RSS フィード 等へアクセス）

実行前に pip 等で依存関係をインストールしてください（プロジェクトに requirements ファイルがある場合はそれに従ってください）。

例:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
3. 依存パッケージをインストール
   - pip install -r requirements.txt  # があれば
   - または個別に: pip install duckdb defusedxml
4. 環境変数または .env ファイルの設定（必須項目は後述）
5. DuckDB スキーマ初期化（下記参照）

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml）を起点に `.env` と `.env.local` を自動読み込みします。
- 読込順序: OS 環境変数 > .env.local > .env
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 環境変数（設定）例

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると自動 .env 読み込みを無効化

例 `.env`（プロジェクトルート）:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要な API と実行例）

以下は Python から簡単に各処理を実行する例です。実行前に必要な環境変数を設定してください。

1) DuckDB スキーマ初期化
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ可

2) 監査ログ DB 初期化（別 DB に分ける場合）
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

3) J-Quants の id_token を取得
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使う

4) 日次 ETL を実行
from kabusys.data import pipeline
result = pipeline.run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())

5) ニュース収集ジョブを実行
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
new_counts = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(new_counts)

6) マーケットカレンダー夜間更新ジョブ
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved {saved} calendar rows")

7) 品質チェックを個別で実行
from kabusys.data import quality
issues = quality.run_all_checks(conn)
for i in issues:
    print(i)

注意点:
- pipeline.run_daily_etl は内部でカレンダー取得 → 株価ETL → 財務ETL → 品質チェックを順次実行します。各ステップは例外処理され、1 ステップの失敗が他を止めない設計です（結果オブジェクトにエラー情報を格納）。
- jquants_client はレートリミット（120 req/min）とリトライロジックを備えています。

---

## よく使うユーティリティ / 挙動メモ

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時などに無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API の 401 応答時には自動で get_id_token を呼び、トークン更新 → 1 回だけリトライします。
- ニュース収集では URL を正規化して SHA-256（先頭32文字）を記事 ID とし、冪等性を担保します。
- DuckDB への保存関数は多くが ON CONFLICT を使って冪等に設計されています。
- market_calendar が存在しない場合は営業日の判定に曜日ベース（土日休みのフォールバック）を使用します。

---

## ディレクトリ構成

（主要ファイル・モジュール）
- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（fetch/save）
      - news_collector.py      # RSS ニュース収集・前処理・DB 保存
      - schema.py              # DuckDB スキーマ定義・初期化
      - pipeline.py            # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py # マーケットカレンダー管理/ジョブ
      - audit.py               # 監査ログ（トレーサビリティ）スキーマ
      - quality.py             # データ品質チェック
    - strategy/                 # 戦略実装用パッケージ（骨格）
      - __init__.py
    - execution/                # 発注 / 実行管理パッケージ（骨格）
      - __init__.py
    - monitoring/               # 監視関連（骨格）
      - __init__.py

---

## サンプルワークフロー（一例）

1. 環境変数を設定 / .env を配置
2. schema.init_schema() で DB を作成
3. 毎朝（もしくは CI / cron）で pipeline.run_daily_etl() を実行
4. 夜間に calendar_update_job() を実行して先読み（lookahead）を行う
5. RSS ニュースは定期的に run_news_collection() で収集し、news_symbols と紐付ける
6. 品質チェック結果や ETLResult を Slack 等に通知して監視

---

## 開発・テスト関連メモ

- 自動 .env 読み込みはテスト時に副作用となる場合があるため、テストプロセスでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨します。
- jquants_client._urlopen 等はテストでモック差替え可能な実装になっています（モジュール内部での抽象化ポイントを利用）。

---

この README はコードベースの主要機能と使い方を簡潔にまとめたものです。詳細な仕様（DataPlatform.md 等）や運用方針に関しては別途ドキュメントを参照してください。質問や追加ドキュメントの要望があれば教えてください。