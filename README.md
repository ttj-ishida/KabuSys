# KabuSys

日本株自動売買プラットフォーム向けのライブラリ群です。データ取得（J‑Quants）、ETL、データ品質チェック、特徴量算出、ニュース収集、マーケットカレンダー管理、監査ログなど、戦略開発〜運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムの基盤ライブラリです。主に以下を目的とします。

- J‑Quants API からの株価・財務・カレンダー取得（レートリミット・リトライ・トークン自動更新対応）
- DuckDB を用いたデータスキーマの定義・永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプラインの差分更新（backfill 対応）と品質チェック
- RSS からのニュース収集（SSRF 対策・トラッキング除去・冪等保存）
- ファクター（モメンタム、ボラティリティ、バリュー等）と研究用ユーティリティ（IC、forward returns、統計サマリー）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- マーケットカレンダー管理（営業日判定等）

設計方針として、外部依存は最小化し（標準ライブラリ＋必須ライブラリ）、DuckDB を中核に冪等にデータを保存することで再現性・監査性を確保しています。

---

## 主な機能一覧

- data/jquants_client
  - J‑Quants API クライアント（ページネーション・レート制御・リトライ・トークン自動リフレッシュ）
  - fetch/save で DuckDB に冪等保存
- data/schema
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- data/pipeline
  - 日次 ETL（差分取得・backfill・品質チェック）: run_daily_etl
- data/quality
  - 欠損、スパイク、重複、日付不整合チェック
- data/news_collector
  - RSS 取得・前処理・記事ID生成・DB保存・銘柄抽出（SSRF・サイズ制限・XML 安全化）
- data/calendar_management
  - 市場カレンダーの更新・営業日判定・next/prev_trading_day 等
- research
  - calc_momentum / calc_volatility / calc_value（prices_daily/raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats）
- audit
  - 監査ログ用テーブル（signal_events / order_requests / executions）と初期化
- その他
  - 環境変数管理（自動 .env ロード機能）: kabusys.config.Settings

---

## セットアップ手順

前提
- Python 3.9+（型注釈に union types を使用している箇所があるため、3.10 推奨）
- DuckDB を利用可能な環境

1. リポジトリをチェックアウト
   - 例: git clone ...

2. 必要パッケージをインストール
   - 最低限必要な外部パッケージ:
     - duckdb
     - defusedxml
   - 例:
     - python -m pip install duckdb defusedxml
   - （開発時は pip install -e . が利用できるパッケージ構成であれば推奨）

3. 環境変数／.env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動的に読み込まれます（kabusys.config が起動時に自動ロード）。
   - 自動ロードを無効にしたい場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（監視等で使用）
- SLACK_CHANNEL_ID: Slack のチャンネル ID
- KABU_API_PASSWORD: kabu API 接続パスワード

オプション
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）

.example .env（参考）
KABUSYS_ENV=development
LOG_LEVEL=INFO
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb

---

## データベース初期化

DuckDB スキーマを初期化します。

Python REPL からの例:

from kabusys.data import schema
# ファイル DB に初期化（親ディレクトリがなければ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")

インメモリ DB（テスト用）:
conn = schema.init_schema(":memory:")

監査ログ用 DB を別途初期化:
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主要ユースケース）

以下はライブラリ API を使ったサンプル的な利用例です。実運用ではエラーハンドリングやロギングを付与してください。

1) 日次 ETL を実行する
- ETL は J‑Quants から差分データを取得し、DuckDB に保存、最後に品質チェックを実行します。

from datetime import date
from kabusys.data import schema, pipeline
conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

2) ニュース収集ジョブを実行する
- RSS を取得して raw_news に保存し、既知銘柄（known_codes）と紐付けることができます。

from kabusys.data.news_collector import run_news_collection
saved_map = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(saved_map)

3) ファクター計算（研究用）
- DuckDB 接続と対象日を与えてファクター群を計算します。

from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, zscore_normalize
d = date(2025, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
# 2つのレコード集合を用いて IC を計算
# 例: calc_ic(factor_records=mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")

4) J‑Quants から生データを直接取得して保存する（細かな制御が必要な場合）
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
n = jq.save_daily_quotes(conn, records)

5) マーケットカレンダー操作
from kabusys.data import calendar_management as cal
is_td = cal.is_trading_day(conn, date.today())
next_td = cal.next_trading_day(conn, date.today())

---

## ディレクトリ構成

リポジトリ内の主要なファイル・パッケージ構成（抜粋）:

src/
  kabusys/
    __init__.py
    config.py                   # 環境変数/設定管理（.env 自動ロード含む）
    data/
      __init__.py
      jquants_client.py         # J‑Quants API クライアント（取得/保存）
      news_collector.py         # RSS ニュース収集・正規化・銘柄抽出
      schema.py                 # DuckDB スキーマ定義・初期化
      pipeline.py               # ETL パイプライン（差分更新・品質チェック）
      quality.py                # データ品質チェック
      stats.py                  # 統計ユーティリティ（zscore_normalize）
      features.py               # features の再エクスポート
      calendar_management.py    # マーケットカレンダー管理
      audit.py                  # 監査ログテーブル初期化
      etl.py                    # ETLResult の再エクスポート
    research/
      __init__.py
      factor_research.py        # モメンタム/ボラティリティ/バリュー計算
      feature_exploration.py    # forward returns / IC / summary
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py

（上記以外にユーティリティや将来のモジュールが追加される想定）

---

## 開発・テスト時の注意点

- 環境変数の自動ロードは kabusys.config がプロジェクトルート（.git または pyproject.toml）から .env/.env.local を読み込みます。テスト時に自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB を使っているため、ローカルおよび CI での高速なテストが可能です。テストでは `:memory:` を使うと便利です。
- news_collector は外部 HTTP を行うため、単体テストでは _urlopen をモックしてネットワーク依存を排除してください。
- jquants_client は API レート制御・リトライ・トークン更新のロジックを持ちます。実際の実行では API キーやネットワークのレート制御に注意してください。
- audit.init_audit_schema は `SET TimeZone='UTC'` を実行します。監査ログは UTC タイムスタンプで統一されています。

---

## 参考・補足

- ログレベルや環境（development / paper_trading / live）は環境変数 `LOG_LEVEL`, `KABUSYS_ENV` で制御されます。`settings.is_live` 等でランタイムでの挙動分岐が可能です。
- 多くの保存処理は ON CONFLICT（DuckDB の対応範囲内）で冪等に実装されています。
- research モジュールの関数群は “本番 API への発注等は行わない” 方針で実装されています。価格・財務テーブルのみを参照します。

---

必要があれば、README に実行例スクリプト、さらに細かい .env.example ファイル、依存関係（requirements.txt または pyproject.toml）や運用手順（cron/airflow ジョブ化、Slack 通知設定等）を追記します。どの情報を優先して追記しましょうか？