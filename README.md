# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。J-Quants や RSS などから市場データ・ニュースを収集して DuckDB に保存し、品質チェック・ETL・監査ログ・カレンダー管理などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された内部ライブラリです。

- J-Quants API から株価日足・財務データ・JPX カレンダーを安全に取得する（レート制御・リトライ・トークン自動リフレッシュ）
- RSS フィードからニュースを収集し、記事と銘柄コードの紐付けを行う（SSRF 対策・XML 攻撃対策・受信サイズ制限）
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定・next/prev_trading_day 等）
- 監査ログ（シグナル → 発注 → 約定のトレースを可能にする監査スキーマ）

設計上のポイント:
- 冪等性を重視（DB へは ON CONFLICT DO UPDATE / DO NOTHING を使用）
- Look-ahead bias を防ぐために fetched_at / created_at を保存
- ネットワーク・XML に対して複数の防御策を実装

対応 Python バージョン: Python 3.10 以降（型表記に | 演算子等を使用）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得 helper（settings）
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レートリミット（120 req/min）・リトライ（指数バックオフ）・401 時トークン自動リフレッシュ
  - DuckDB へ保存する save_* 関数（冪等）
- ニュース収集
  - RSS 取得（SSRF・XML 攻撃対策・gzip 解凍・サイズ制限）
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等保存
  - raw_news, news_symbols への保存ロジック（バルク挿入・トランザクション）
  - テキスト前処理・銘柄コード抽出（4桁コード検出）
- スキーマ定義 / 初期化
  - data.schema.init_schema(db_path) による DuckDB の初期化
  - 3 層（Raw / Processed / Feature / Execution）と監査テーブル（audit）用の初期化関数
- ETL パイプライン
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェックの一連処理
  - 差分更新、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - calendar_update_job: 夜間でのカレンダー差分更新
- 監査ログ
  - signal_events / order_requests / executions 等のテーブル定義・初期化
  - init_audit_db / init_audit_schema

---

## 依存関係

最低限必要なパッケージ（例）
- Python >= 3.10
- duckdb
- defusedxml

（HTTP は標準ライブラリの urllib を使用）

インストール例（pip）:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン／展開する
2. Python 仮想環境を作成して依存関係をインストールする
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -U pip
   - pip install duckdb defusedxml
3. 環境変数を設定（.env / .env.local 推奨）
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env を読み込みます
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ...
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
5. DuckDB スキーマの初期化
   - Python から data.schema.init_schema を実行して DB を作成します（以下参照）

例: .env.example（プロジェクトルート）
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（基本的な例）

以下は基本的な Python スニペット例です。実行はプロジェクトのルートから行ってください。

1) スキーマ初期化（DuckDB ファイルの作成）
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")

2) 日次 ETL の実行（カレンダー取得 → 株価 → 財務 → 品質チェック）
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")  # 事前に init_schema を実行済みの場合
result = run_daily_etl(conn)
print(result.to_dict())

主な引数:
- target_date: ETL 対象日（省略時は今日）
- id_token: J-Quants の id_token（省略可、内部で refresh token から取得）
- run_quality_checks: 品質チェックを実行するか（デフォルト True）
- backfill_days: 最終取得日から何日分を再取得して API の修正を吸収するか（デフォルト 3）

3) ニュース収集の実行
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使う有効な銘柄コードのセット（任意）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)

4) J-Quants からの直接取得例
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して id_token を取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

5) 監査 DB 初期化（監査専用 DB を別に管理する場合）
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")

---

## 環境設定・settings

kabusys.config.Settings オブジェクト（kabusys.config.settings）からアプリ設定を取得できます。主なプロパティ:

- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
- settings.slack_bot_token
- settings.slack_channel_id
- settings.duckdb_path (Path)
- settings.sqlite_path (Path)
- settings.env, settings.log_level, settings.is_live, settings.is_paper, settings.is_dev

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を基準に .env, .env.local を読み込みます
- 優先順位: OS 環境変数 > .env.local > .env
- テストや特殊環境で無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

必須設定が未設定の場合は settings の該当プロパティで ValueError が発生します。

---

## ディレクトリ構成

リポジトリ内の主要ファイル / モジュール構成（抜粋）

src/kabusys/
- __init__.py
- config.py                       # 環境変数・設定読み込み
- data/
  - __init__.py
  - jquants_client.py             # J-Quants API クライアント（取得・保存）
  - news_collector.py             # RSS ベースのニュース収集
  - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
  - calendar_management.py        # カレンダー管理（営業日判定・夜間更新ジョブ）
  - schema.py                     # DuckDB スキーマ定義・初期化
  - audit.py                      # 監査ログスキーマ（signal/events/order_requests/executions）
  - quality.py                    # データ品質チェック
- strategy/
  - __init__.py                    # 戦略層（未展開: 戦略実装用モジュール）
- execution/
  - __init__.py                    # 発注実行層（未展開: ブローカー連携等）
- monitoring/
  - __init__.py                    # 監視 / メトリクス（未展開）

---

## 実運用上の注意・ベストプラクティス

- J-Quants のレート制限や 401 の扱いは内部で処理されますが、運用時は適切な監視とログ出力（LOG_LEVEL）を設定してください。
- run_daily_etl を定期実行する際は、監査ログ・エラーの保存方法を決め、失敗ケースのハンドリング（Slack 通知など）を実装してください。
- DuckDB ファイルはバックアップ／スナップショットを検討してください。監査 DB は可能なら別ファイルに分けて管理すると安全です。
- ニュース収集では外部接続の検査（SSRF 対策、Private IP 拒否、最大受信サイズ）を実装していますが、社内ポリシーに従った追加制限を検討してください。
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと .env の自動ロードを抑制できます。

---

## 参考・デバッグ

- ログ: 各モジュールは標準 logging を使用します。環境変数 LOG_LEVEL を設定して出力レベルを調整してください。
- 開発中は settings.is_dev を参照して挙動を分岐できます。
- データ不整合は data.quality のチェックで検出できます。ETL 実行後に run_all_checks の結果を監査してください。

---

必要であれば README に「運用手順（cron/Cloud Scheduler / Airflow での定期実行例）」「.env.example の完全版」「追加の使用例（Slack 通知例など）」を追記できます。どの情報を優先して追加しますか？