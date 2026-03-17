# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォームの骨組みを提供するライブラリです。  
J-Quants API から市場データや財務データ、JPX カレンダー、RSS ニュースを取得して DuckDB に保存し、ETL／品質チェック／監査ログなどを備えたデータ基盤と自動売買処理の基礎を提供します。

主な設計方針：
- データ取得は冪等（ON CONFLICT … DO UPDATE / DO NOTHING）
- API レート制御（J-Quants: 120 req/min）とリトライ（指数バックオフ）
- トレーサビリティ（監査テーブル、UUID ベースの冪等キー）
- SSRF / XML Bomb 対策等のセキュリティ考慮

バージョン: 0.1.0

---

## 機能一覧

- 環境変数／設定管理（kabusys.config）
  - .env / .env.local 自動ロード（オプションで無効化可能）
  - 必須値の取り出し・検証（環境ごとのフラグ等）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制御、リトライ、トークン自動リフレッシュ、fetched_at の記録
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、ID 生成（正規化URL→SHA256）
  - SSRF / XML 攻撃対策、サイズ制限、DuckDB への冪等保存
  - 記事から銘柄コード（4桁）抽出と紐付け
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit レイヤーのテーブル定義と初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（バックフィル対応）、品質チェック統合、日次 ETL 実行
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日取得、JPX カレンダー夜間更新ジョブ
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合の検出
- 監査ログ（kabusys.data.audit）
  - signal / order_request / execution の監査テーブルと初期化

（strategy / execution / monitoring のパッケージは骨組みとして用意）

---

## 動作要件

- Python 3.10+（型注釈に union 型や typing を使用）
- 依存パッケージ（主に）:
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, logging, datetime, json 等）

requirements.txt はプロジェクトに合わせて用意してください。最低限のインストール例：

pip install duckdb defusedxml

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係をインストール
   - pip install duckdb defusedxml
   - その他プロジェクトが必要とするパッケージを追加でインストール
4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成（自動で読み込まれます）
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意 / デフォルト
     - KABUSYS_ENV: development | paper_trading | live （デフォルト development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト INFO）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. DuckDB スキーマを初期化
   - Python REPL やスクリプトで下記を実行（デフォルトファイル名を使用する例）:

     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

6. 監査ログを別 DB に作りたい場合:
   - from kabusys.data.audit import init_audit_db
   - audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV — environment (development|paper_trading|live)
- LOG_LEVEL — ログレベル（INFO 等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化（値が設定されていれば無効化）

kabusys.config.Settings からプログラム内でアクセスできます:
from kabusys.config import settings
settings.jquants_refresh_token, settings.duckdb_path, settings.is_live など

---

## 使い方（基本例）

以下は主要なユースケースの簡単な利用例です。

- DuckDB スキーマ初期化（最初だけ）

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

- 日次 ETL を実行（株価 / 財務 / カレンダーの差分取得 + 品質チェック）

from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)
print(result.to_dict())

- ニュース収集を実行（RSS から raw_news へ保存し、銘柄紐付け）

from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に有効コードセットを用意
results = run_news_collection(conn, known_codes=known_codes)
print(results)

- J-Quants API から株価を直接取得

from kabusys.data.jquants_client import fetch_daily_quotes
quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))

- カレンダー夜間更新ジョブ

from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved={saved}")

- 監査テーブルを初期化

from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema
conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)

---

## 実装上の注意点 / 補足

- J-Quants API のレート制御
  - デフォルトで 120 requests/min（_MIN_INTERVAL_SEC を基に固定間隔で待機）
  - 408/429/5xx は指数バックオフで最大 3 回リトライ
  - 401 受信時は refresh token で id_token を自動更新し 1 回だけリトライ
- データ永続化
  - raw テーブルやニュース保存は冪等操作（ON CONFLICT を利用）
  - news_collector は記事IDを正規化URL → SHA-256（先頭32文字）で生成し冪等性を保証
- セキュリティ
  - RSS の XML 解析に defusedxml を使用（XML Bomb 等に対策）
  - RSS 取得時のリダイレクト・ホスト検査で SSRF を防止
  - レスポンスサイズ制限（デフォルト 10MB）でメモリ DoS を緩和
- 日付/タイムゾーン
  - fetched_at や created_at は UTC を基本に記録（監査 DB は SET TimeZone='UTC'）
- テスト
  - 設定の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効にできます（テスト時便利）

---

## ディレクトリ構成

プロジェクトの主要ファイル構成（抜粋）:

src/kabusys/
- __init__.py
- config.py                      # 環境変数 / 設定読み込み
- data/
  - __init__.py
  - jquants_client.py            # J-Quants API クライアント（取得・保存）
  - news_collector.py            # RSS ニュース収集・前処理・保存
  - schema.py                    # DuckDB スキーマ定義・初期化
  - pipeline.py                  # ETL パイプライン（差分更新・品質チェック）
  - calendar_management.py       # マーケットカレンダー管理／営業日ロジック
  - audit.py                     # 監査ログ用テーブル・初期化
  - quality.py                   # データ品質チェック
- strategy/
  - __init__.py                  # 戦略モジュールの骨組み（実装は別途）
- execution/
  - __init__.py                  # 発注・注文管理の骨組み（実装は別途）
- monitoring/
  - __init__.py                  # 監視関連（プレースホルダ）

プロジェクトルート:
- .env, .env.local (推奨: .env.example を参考に作成)
- pyproject.toml / setup.cfg 等（ビルド / 配布設定）

---

## 貢献 / ライセンス

- 貢献方法やライセンス情報はリポジトリのルートに LICENSE / CONTRIBUTING.md を用意してください（本テンプレートには含まれていません）。

---

以上が KabuSys の概要と主要な使い方です。README に不足している点（例: 具体的な requirements.txt、CI 設定、戦略実装例など）があれば、利用目的に合わせて追記します。必要なサンプルやテンプレート（.env.example、簡易 ETL スクリプト等）を生成することも可能です。どれを追加しますか？