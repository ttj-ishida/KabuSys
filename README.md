# KabuSys

日本株自動売買システムのライブラリ群。データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ（注文→約定のトレース）など、アルゴリズムトレード基盤で必要な機能を提供します。

主な設計方針：
- データ取得は冪等（ON CONFLICT / DO UPDATE）で安全に保存
- API レート制御・リトライ・トークン自動更新を備えたクライアント
- DuckDB をデータレイク（オンディスク/インメモリ）として利用
- ニュース収集は SSRF / XML Bomb 等の安全対策を考慮
- データ品質チェックを組み込みで実行可能

バージョン: 0.1.0

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（トークン取得、日足・財務・市場カレンダー取得）
  - RateLimiter、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - DuckDB へ保存する save_* 関数（冪等）

- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - スキーマ初期化（init_schema）と接続取得（get_connection）

- data/pipeline.py
  - 日次 ETL（run_daily_etl）
  - 差分取得、バックフィル、品質チェック（quality モジュール呼び出し）

- data/news_collector.py
  - RSS フィード取得、前処理、記事ID生成（URL 正規化 + SHA256）、DuckDB への保存（save_raw_news）
  - SSRF / gzip bomb / defusedxml 対策
  - 銘柄コード抽出と news_symbols への紐付け

- data/calendar_management.py
  - market_calendar の夜間更新ジョブ（calendar_update_job）
  - 営業日判定・前後営業日取得・期間内営業日取得

- data/quality.py
  - 欠損値 / 重複 / スパイク / 日付不整合 のチェック（run_all_checks）

- data/audit.py
  - 監査用テーブル（signal_events / order_requests / executions）初期化、監査DB作成

- config.py
  - 環境変数読み込み（.env / .env.local 自動ロード, KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - settings オブジェクトを通じてアプリ設定にアクセス

---

## 必要条件（推奨）

- Python 3.10 以上（型付け・Union 演算子で | を使用）
- ネットワークアクセス（J-Quants API、RSS 等）
- 推奨パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトに requirements ファイルがある場合はそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（開発モード）
   - pip を使う例:
     - pip install -e .

2. 必要パッケージをインストール（例）
   - pip install duckdb defusedxml

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` として必要な値を置きます。
   - 自動読み込み順序: OS 環境 > .env.local > .env
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

4. DuckDB データベース初期化（下記「使い方」参照）

---

## 必要な環境変数（例）

以下は本ライブラリが参照する主な環境変数です。必須なものには注記します。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知のチャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

例 .env（実運用ではシークレットを直接コミットしないこと）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要なコード例）

以下は Python REPL やスクリプト内で利用する際の簡単な例です。

1) DuckDB スキーマ初期化

from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# 以降 conn を ETL / ニュース収集等で使う

2) 監査 DB の初期化（監査専用 DB を分ける場合）

from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

3) J-Quants トークンを取得（テストや確認用）

from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用

4) 日次 ETL を実行する（市場データ・財務・カレンダー・品質チェック）

from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)
# result は ETLResult オブジェクト。result.to_dict() で辞書に変換可能

5) ニュース収集ジョブを実行する

from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# known_codes を渡すと記事から銘柄コード抽出して紐付けを行う
known_codes = {"7203", "6758", "9984"}
summary = run_news_collection(conn, sources=None, known_codes=known_codes)
# summary は {source_name: saved_count} を返す

6) カレンダー関連ユーティリティ

from kabusys.data import calendar_management as cm
conn = schema.init_schema("data/kabusys.duckdb")
from datetime import date
d = date(2024, 1, 1)
is_trading = cm.is_trading_day(conn, d)
next_td = cm.next_trading_day(conn, d)
trading_days = cm.get_trading_days(conn, date(2024,1,1), date(2024,1,31))

7) データ品質チェックを個別実行

from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=None)
# QualityIssue オブジェクトのリストが返る（severity に基づき処理判断）

---

## 注意点 / 運用上のヒント

- .env の自動読み込み:
  - パッケージ import 時点でプロジェクトルートを .git または pyproject.toml から探索し、.env/.env.local を自動読み込みします。
  - テストや特殊環境で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- API レート制御:
  - J-Quants のレート制限（120 req/min）を守るためにモジュール内部で待機を行います。高頻度の並列リクエストは設計に慎重になってください。

- DuckDB のトランザクション:
  - bulk INSERT はトランザクション（conn.begin()/commit()/rollback()）でまとめています。長時間ロックや大きなトランザクションに注意してください。

- セキュリティ:
  - news_collector には SSRF / XML Bomb 対策が施されていますが、運用では RSS の信用できるソースを使用してください。
  - シークレットは .env に保存する場合もアクセス権管理を厳格に。

---

## ディレクトリ構成

リポジトリの主要構成（src 配下のパッケージ構造）:

src/
  kabusys/
    __init__.py              # パッケージ初期化、__version__ など
    config.py                # 環境変数・設定管理（settings）
    data/
      __init__.py
      jquants_client.py      # J-Quants API クライアント + DuckDB 保存ユーティリティ
      news_collector.py      # RSS ニュース収集・前処理・DB保存
      schema.py              # DuckDB スキーマ定義と初期化
      pipeline.py            # ETL パイプライン（run_daily_etl 等）
      calendar_management.py # マーケットカレンダーの管理
      quality.py             # データ品質チェック
      audit.py               # 監査ログ向けスキーマと初期化
    strategy/                 # 戦略関連（未実装のエントリポイント）
      __init__.py
    execution/                # 発注・実行管理（未実装のエントリポイント）
      __init__.py
    monitoring/               # 監視関連（未実装のエントリポイント）
      __init__.py

---

## 貢献 / 開発

- 新しい機能や修正を行う際は、既存の DB スキーマやマイグレーションに注意してください。
- ユニットテストはネットワーク依存部分をモック化して実行することを推奨します（jquants_client の _urlopen や news_collector._urlopen は差し替え可能）。
- 自動ロードされる .env のテスト影響を避けるためには KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

この README はコードベース（src/kabusys/*）の解説に基づいてまとめています。追加で README に含めたい使い方の具体例や運用手順があれば教えてください。