# KabuSys

日本株自動売買システムのコアライブラリ（モジュール群）。データ取得・ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査（オーディット）スキーマなど、取引戦略や注文実行レイヤーの基盤となる機能を提供します。

主な設計方針：
- データの冪等性（ON CONFLICT / DO UPDATE / DO NOTHING）
- Look-ahead Bias 回避（fetched_at に UTC タイムスタンプを記録）
- API レート制御、リトライ、トークン自動リフレッシュの実装
- DuckDB を用いたローカル永続化
- SSRF / XML Bomb / メモリ DoS 対策等のセキュリティ考慮

---

## 機能一覧

- 環境変数 / .env 読み込みと設定管理（kabusys.config）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可能）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、四半期財務データ、マーケットカレンダー取得
  - レート制御（120 req/min）、指数バックオフのリトライ、401時の自動トークンリフレッシュ
  - DuckDB への保存（冪等）
- RSS ニュース収集（kabusys.data.news_collector）
  - RSS 取得、XML パース、URL 正規化、記事ID の生成（SHA-256 先頭32文字）
  - SSRF / Gzip Bomb / トラッキングパラメータ除去等の対策
  - raw_news / news_symbols への冪等保存
- スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義・初期化ユーティリティ
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（カレンダー・株価・財務）／差分取得／バックフィル／品質チェック
  - 品質チェックは stop-fail ではなく検出結果を返す（呼び出し元で判断）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、翌営業日/前営業日取得、夜間カレンダー更新ジョブ
- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定までのトレース用テーブル群と初期化関数
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付整合性チェック
- 環境 / モード判定（development / paper_trading / live）とログレベル管理

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.9+）
   - 仮想環境の作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 最低限必要なパッケージ（コードからの推奨）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトでは他に標準ライブラリのみを使用していますが、実運用ではログ送信や Slack 通知用に slack_sdk 等が必要になる場合があります）

3. リポジトリからのインストール（開発向け）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション等の API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: 通知先チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（モニタリング）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: environment（development, paper_trading, live）デフォルト development
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）デフォルト INFO

   .env のサンプルはプロジェクト側で `.env.example` を用意しておくことを推奨します。

---

## 使い方

以下は簡単な利用例と API 呼び出し例です。実際はアプリケーションのエントリポイントから呼び出してください。

1) DuckDB スキーマ初期化

Python REPL / スクリプトで：

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

- ":memory:" を渡すとインメモリ DB を利用できます。

2) 日次 ETL の実行

from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date 等をオプション指定可能
print(result.to_dict())

- run_daily_etl は market_calendar → prices → financials → quality checks の順で実行します。
- id_token は引数で注入可能（テスト用）。既定では設定から取得したリフレッシュトークンで自動的に ID トークンを取得・キャッシュします。
- backfill_days（デフォルト 3）により最終取得の数日前から再取得して API の後出し修正を吸収します。

3) ニュース収集ジョブ

from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758"}  # 抽出対象の銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}

- fetch_rss は RSS の安全性チェック（スキーム検証、プライベートIP拒否、最大サイズ制限 等）を行います。
- save_raw_news は INSERT ... RETURNING で実際に挿入された記事 ID を返します。

4) マーケットカレンダーの夜間更新ジョブ

from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved", saved)

5) 監査スキーマの初期化（監査専用 DB を分けたい場合）

from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.db")

- init_audit_db は TIMESTAMP を UTC に固定します。

6) 品質チェックの単体実行

from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)

---

## 主なパラメータ／設定のメモ

- レート制限: J-Quants API に対して 120 req/min を守るための固定間隔スロットリングを実装（_RateLimiter）。
- リトライ: 指数バックオフ、最大 3 回。HTTP 408/429/5xx に対してリトライ。429 の Retry-After を優先。
- ID トークン: モジュールレベルでキャッシュし、401 の場合は一度だけ自動リフレッシュして再試行。
- NewsCollector:
  - 最大受信バイト数: 10 MB（Gzip も含めてチェック）
  - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字
  - SSRF 対策: リダイレクト時に検査、ホストがプライベートか DNS で検査
- ETL の差分処理: DB の最終取得日から差分のみ取得。初回は _MIN_DATA_DATE を使用。

---

## ディレクトリ構成

以下は本リポジトリ（src/kabusys）内の主なファイル・モジュール構成です。

src/
  kabusys/
    __init__.py               -- パッケージ定義（__version__ 等）
    config.py                 -- 環境変数 / .env 読み込みと Settings
    data/
      __init__.py
      jquants_client.py       -- J-Quants API クライアント（取得 & DuckDB 保存）
      news_collector.py       -- RSS ニュース収集・保存・紐付けロジック
      schema.py               -- DuckDB スキーマ定義と init_schema / get_connection
      pipeline.py             -- ETL パイプライン（run_daily_etl 等）
      calendar_management.py  -- マーケットカレンダー管理（is_trading_day 等）
      audit.py                -- 監査ログスキーマと初期化
      quality.py              -- データ品質チェック
    strategy/
      __init__.py             -- 戦略モジュール（将来的な戦略実装用）
    execution/
      __init__.py             -- 発注・ブローカー連携用（将来的に実装）
    monitoring/
      __init__.py             -- モニタリング関連（将来的に実装）

---

## 追加の注意点 / 推奨

- .env ファイルの管理:
  - プロジェクトルートに `.env.example` を置き、実際の `.env` には機密情報（トークン・パスワード）を入れる。
  - CI / 本番では OS 環境変数で設定するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して自動ロードを無効にする。
- ロギング:
  - Settings.log_level によりログレベルを制御します。運用では INFO 〜 WARNING、デバッグ時は DEBUG を利用してください。
- テスト:
  - jquants_client のネットワーク呼び出しや news_collector._urlopen 等はモック可能な設計です（テスト容易性を考慮）。
- 運用モード:
  - KABUSYS_ENV の値は "development" / "paper_trading" / "live" のいずれか。is_live / is_paper / is_dev により挙動を切替可能。

---

必要であれば、README にサンプルの .env.example、requirements.txt、CI ワークフロー例（ETL の cron / GitHub Actions 実行）、および運用時の監視・アラート設計（Slack連携等）を追記しますか？