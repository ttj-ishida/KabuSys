# KabuSys

日本株向け自動売買プラットフォームの基盤ライブラリです。データ収集（J-Quants / RSS）、ETL パイプライン、DuckDB ベースのスキーマ、品質チェック、マーケットカレンダー管理、監査ログなどの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得（レート制御・リトライ・トークン自動更新）
- RSS フィードからニュースを収集して DuckDB に保存（SSRF 対策・XML 脆弱性対策・トラッキング除去）
- DuckDB を用いたデータスキーマの初期化と接続管理
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー判定ユーティリティ（営業日/前後営業日/期間内営業日取得）
- 監査ログ（シグナル→発注→約定までのトレーサビリティ）
- データ品質チェック（欠損、重複、スパイク、日付不整合）

設計上の特徴として、API レート制限遵守、冪等性を考慮した DB 保存（ON CONFLICT）、Look-ahead バイアス対策（fetched_at の記録）、セキュリティ（defusedxml・SSRF ブロック）などに配慮しています。

---

## 機能一覧

- 環境変数/設定管理（kabusys.config）
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - 必須設定の取得ヘルパー
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（fetch_daily_quotes）
  - 財務データ（fetch_financial_statements）
  - マーケットカレンダー（fetch_market_calendar）
  - DuckDB への保存関数（save_daily_quotes 等）
  - レートリミッタ、リトライ、トークン自動更新
- RSS ニュース収集（kabusys.data.news_collector）
  - RSS 取得・XML パース（defusedxml 使用）
  - URL 正規化・トラッキング除去、記事ID 生成（SHA-256）
  - SSRF 対策（リダイレクトやホスト検証）、レスポンスサイズ制限
  - DuckDB へ冪等保存（INSERT ... ON CONFLICT / RETURNING）
  - 銘柄コード抽出・紐付け
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema(db_path) でスキーマ初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日ベース）・バックフィル
  - 日次 ETL 実行（run_daily_etl）
  - 品質チェック連携（kabusys.data.quality）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・前後営業日取得・期間内営業日列挙
  - 夜間バッチ更新ジョブ（calendar_update_job）
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions など監査用テーブルの初期化
  - init_audit_schema / init_audit_db
- 品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク、重複、日付不整合チェック
  - QualityIssue を返し、ETL 側で判定・ログ化可能

---

## 要件 / 事前準備

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml

インストール例（仮）:
pip install duckdb defusedxml

（プロジェクト配布形式に合わせて requirements.txt / pyproject.toml を用意してください。）

---

## 環境変数

自動的にプロジェクトルートの `.env` → `.env.local` を読み込みます（優先度: OS 環境 > .env.local > .env）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意): kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意): 'development'|'paper_trading'|'live'（デフォルト: development）
- LOG_LEVEL (任意): 'DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL'（デフォルト: INFO）

例 (.env):
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトルートへ移動
2. Python 環境を準備（venv, pyenv など）
3. 依存パッケージをインストール
   pip install duckdb defusedxml
   （プロジェクトに pyproject.toml または requirements.txt があればそれに従う）
4. .env を作成して必要な環境変数を設定
5. DuckDB スキーマを初期化
   - Python REPL / スクリプト例:

     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

   - これにより parent ディレクトリが存在しない場合は自動作成され、全テーブルとインデックスが作成されます。

6. （監査ログ用 DB を分離したい場合）
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（コード例）

基本的な流れ（DuckDB 初期化 → 日次 ETL 実行）:

from kabusys.data import schema, pipeline
# スキーマ初期化（ファイルが無ければ作成）
conn = schema.init_schema("data/kabusys.duckdb")
# 日次 ETL を実行（target_date を省略すると今日）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())

ニュース収集（RSS）実行例:

from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758"}  # 必要に応じて銘柄コードセットを渡す
results = run_news_collection(conn, known_codes=known_codes)
print(results)

マーケットカレンダー更新ジョブ:

from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved calendar records: {saved}")

監査スキーマの初期化（既存接続に追加）:

from kabusys.data.audit import init_audit_schema
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)

J-Quants API を直接呼んでデータ取得（テスト／デバッグ向け）:

from kabusys.data import jquants_client as jq
# id_token を明示的に渡すことも可能。省略時は内部キャッシュから取得。
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,10))
print(len(records))

品質チェックの実行:

from kabusys.data import quality, schema
conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn)
for i in issues:
    print(i)

注意点:
- run_daily_etl 等は内部で例外を捕捉して処理を継続しますが、result.errors にエラー概要を格納します。詳細ログは logger で出力されます。
- J-Quants のリクエストにはレート制御があるため、短時間に大量のリクエストを投げないでください。

---

## ディレクトリ構成

リポジトリの主要なファイル / モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save 関数）
    - news_collector.py      — RSS ニュース収集 / 保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー関連ユーティリティ
    - audit.py               — 監査ログテーブル定義・初期化
    - quality.py             — データ品質チェック
  - strategy/                 — 戦略関連（空のパッケージ。拡張ポイント）
  - execution/                — 発注/ブローカ連携（空のパッケージ。拡張ポイント）
  - monitoring/               — 監視用モジュール（未実装 / 拡張ポイント）

その他:
- pyproject.toml / setup.cfg 等（プロジェクトルートに配置する想定）
- .env / .env.local（ローカルで管理する設定ファイル。機密情報はバージョン管理しないこと）

---

## 開発・拡張する際のポイント

- 環境自動ロード: config._find_project_root() は .git または pyproject.toml を基準にプロジェクトルートを探します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを抑制できます。
- DuckDB への保存は可能な限り冪等（ON CONFLICT）で行う設計です。外部から直接 DB を操作する場合はスキーマ整合性に注意してください。
- ニュース収集は SSRF / XML 攻撃対策が組み込まれています。外部 URL を扱う処理を追加する際は同様の検査を行ってください。
- 品質チェックは Fail-Fast しない設計です。運用ポリシーに応じて「致命的な品質問題発生時に ETL を停止する」などのロジックを上位で実装してください。
- strategy/ execution/ monitoring/ は拡張ポイントです。実際の戦略ロジックやブローカ API 連携、モニタリング（Slack 通知等）はここを拡張して実装します。

---

もし README に追記したい実行コマンド例（CLI スクリプトの作成方法）や、CI / デプロイ手順、サンプル .env.example を含めたい場合は指示してください。