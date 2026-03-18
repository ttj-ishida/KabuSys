# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）。  
J-Quants や RSS からデータを収集し、DuckDB に保存・品質チェックを行い、戦略・発注層へデータを提供することを目的としています。

---

## 概要

KabuSys は以下の主要コンポーネントを持つパッケージです。

- J-Quants API クライアント（株価・財務・マーケットカレンダー取得、トークン自動更新、レートリミット／リトライ対応）
- DuckDB 用スキーマ定義と初期化機能（Raw / Processed / Feature / Execution 層、監査テーブル含む）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- ニュース収集器（RSS 取得、前処理、記事の冪等保存、銘柄抽出）
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）

設計方針として、API レート制御・再試行・冪等性・Look-ahead Bias 回避（fetched_at の記録）を重視しています。

---

## 機能一覧

- J-Quants からの日足（OHLCV）・財務データ・市場カレンダー取得
  - レート制限（120 req/min）対応
  - リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - ページネーション対応
- DuckDB スキーマ定義・初期化（多層スキーマ）
  - raw_prices / raw_financials / market_calendar / raw_news / … 等
  - 監査ログ（signal_events / order_requests / executions）用スキーマ
- ETL パイプライン
  - 差分更新（DB の最終取得日を確認）
  - backfill 対応（直近数日を再取得して後出し修正を吸収）
  - 品質チェック実行（欠損・重複・スパイク・日付整合性）
- ニュース収集（RSS）
  - XML セキュリティ（defusedxml）
  - SSRF 対策（スキーム検証、プライベート IP へのアクセスブロック）
  - トラッキングパラメータ除去、URL 正規化、記事ID は SHA-256（先頭32文字）
  - 冪等保存（INSERT ... ON CONFLICT / RETURNING を利用）
  - テキストから銘柄コード（4桁）抽出
- カレンダー管理
  - 営業日判定、前後営業日の取得、期間内営業日リスト取得
  - カレンダー差分更新ジョブ
- 品質チェック（quality モジュール）
  - 欠損データ、重複、スパイク、未来日付・非営業日の検出

---

## 要件（開発時想定）

- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - defusedxml
- （プロダクションで Slack 等を使う場合は別途 slack-sdk 等を用意）

実行環境に合わせて requirements.txt を作成してください。最低限は以下をインストールしておくと良いです：

pip install duckdb defusedxml

（パッケージを pip パッケージ化している場合は pip install . / pip install -e . を使用）

---

## 環境変数（設定）

自動でプロジェクトルートにある `.env` および `.env.local` を読み込みます（ただし CWD に依存せずパッケージ起点で探索）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（アプリ起動時に必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
- KABU_API_PASSWORD: kabuステーション等の API パスワード
- SLACK_BOT_TOKEN: Slack Bot トークン（通知等で使用する場合）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト "http://localhost:18080/kabusapi"）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite モニタリング DB パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live"), デフォルト "development"
- LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト "INFO"）

注意: Settings クラスは読み込み時に値の妥当性チェックを行います。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （必要に応じて他のライブラリも追加）

4. 環境変数ファイルを作成
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を作成し、必須のキーを設定してください。
   - 例（.env.example を参考に）:
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

5. DuckDB スキーマ初期化（Python REPL / スクリプト）
   - 以下のようにして DB を初期化します（parent ディレクトリが自動作成されます）。

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

6. 監査用 DB 初期化（独立 DB を使う場合）
   - from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（サンプルコード）

以下は主要な操作の最小サンプルです。実際はロギング設定や例外処理を追加してください。

- J-Quants トークン取得（明示的に取得したい場合）

from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して id_token を取得

- DuckDB スキーマ初期化

from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL 実行

from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
result = run_daily_etl(conn)  # デフォルトは今日を対象に ETL を実行
print(result.to_dict())

- ニュース収集ジョブ（RSS）

from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に有効コードを準備
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規記事数}

- マーケットカレンダー更新ジョブ（夜間バッチ向け）

from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)

- 監査スキーマ初期化（既存接続へ追加）

from kabusys.data import audit, schema

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=True)

---

## 注意点 / 運用上のポイント

- API レート・リトライ
  - J-Quants クライアントは 120 req/min に基づくスロットリングを行います。スレッドやプロセスを複数立てる場合は注意してください（モジュールレベルの RateLimiter はプロセス内で共有されます）。
- 設定の自動ロード
  - パッケージはプロジェクトルート（.git または pyproject.toml がある場所）から自動的に .env を読み込みます。テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のファイルパーミッション / バックアップ
  - DuckDB ファイルは単一ファイルのため、定期バックアップと排他アクセス方針を検討してください。
- セキュリティ
  - RSS 取得は SSRF 対策や gzip 上限チェックを行いますが、外部入力を扱う場合は追加の検証を検討してください。
- 品質チェック
  - ETL 後に run_all_checks() を呼んで問題を検出します。重大度に応じてアラートや処理の停止をアプリ側で判断してください。

---

## ディレクトリ構成

リポジトリ（抜粋）:

src/
  kabusys/
    __init__.py
    config.py                        # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py              # J-Quants API クライアント（取得・保存ロジック）
      news_collector.py              # RSS ニュース収集・前処理・DB保存
      schema.py                      # DuckDB スキーマ定義・初期化
      pipeline.py                    # ETL パイプライン（差分取得 / 品質チェック）
      calendar_management.py         # マーケットカレンダー管理（営業日判定等）
      audit.py                       # 監査ログ（signal/order/execution）スキーマ
      quality.py                     # データ品質チェック
    strategy/                         # 戦略関連（空のパッケージ）
      __init__.py
    execution/                        # 発注/実行管理（空のパッケージ）
      __init__.py
    monitoring/                       # 監視用モジュール（未実装）
      __init__.py

README.md (このファイル)
pyproject.toml / setup.cfg / .gitignore 等（プロジェクトルート）

---

## 今後の拡張アイデア

- 発注実行層と証券会社 API（kabu/station）とのインテグレーション
- Slack / PagerDuty などへの自動通知機能（品質チェックや ETL 結果の通知）
- 戦略レイヤーのプラグイン化・バージョン管理（strategy_id によるトレーサビリティ）
- モニタリング用の Web UI（監査ログやポートフォリオ推移の可視化）

---

ご不明点や README の追記希望（例えばサンプル .env.example の出力や CI/CD 用手順の追加など）があればお知らせください。