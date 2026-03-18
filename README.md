# KabuSys

日本株自動売買のためのデータ基盤・ETL・監査ライブラリ群。J-Quants API からの市場データ取得、RSS ニュース収集、DuckDB を用いたスキーマ管理、日次 ETL パイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ（発注・約定トレース）などを提供します。

主な用途
- J-Quants からの OHLCV / 財務データ / JPX カレンダーの取得と DuckDB への保存
- RSS からのニュース収集と記事 → 銘柄の紐付け
- 日次差分 ETL（差分取得・バックフィル・品質チェック）の実行
- DuckDB ベースのスキーマ初期化と監査ログ用テーブルの初期化

バージョン: 0.1.0

---

## 機能一覧

- 環境変数管理
  - .env / .env.local を自動読み込み（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化可）
  - 必須項目は Settings プロパティで取得（未設定時は ValueError）

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーの取得
  - レート制限（120 req/min）に従ったスロットリング
  - リトライ（指数バックオフ、最大3回、408/429/5xx を対象）
  - 401 受信時は自動トークンリフレッシュして 1 回再試行
  - 取得時刻 fetched_at を UTC で記録（Look-ahead bias 対策）
  - DuckDB への保存は冪等（ON CONFLICT を使用）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、XML パースは defusedxml を使用（安全対策）
  - URL 正規化（utm_* 等のトラッキングパラメータ除去）、記事ID は normalized URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証、プライベート IP 検出、リダイレクト検査）
  - レスポンスサイズ制限（最大 10 MB）
  - DuckDB への冪等保存（INSERT ... ON CONFLICT / RETURNING を利用）
  - テキスト前処理と銘柄コード抽出（4桁数字、known_codes フィルタ）

- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマを定義
  - テーブル定義およびインデックス作成
  - init_schema(db_path) で初期化（冪等）

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 差分更新（DB の最終取得日をもとに必要な範囲のみ取得）
  - バックフィル（デフォルト 3 日）による API 側修正の吸収
  - 品質チェックは続行型（問題は集約して返す）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job で夜間差分更新を実行

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions を持つ監査用スキーマ
  - UUID ベースのトレーサビリティ（order_request_id は冪等キー）
  - init_audit_schema / init_audit_db による初期化（UTC タイムゾーン固定）

- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク（前日比）、日付不整合（未来日・非営業日）を検出
  - QualityIssue オブジェクトのリストで問題を返す

---

## セットアップ手順

前提
- Python 3.9+（コードは typing の新しい表記などを使用）
- 必要パッケージ: duckdb, defusedxml（お好みで logging 設定や追加の HTTP ライブラリは任意）

例（pip によるインストール）:
- requirements.txt がない場合は最低限下記をインストールしてください。
  - pip install duckdb defusedxml

ローカル開発（editable install、もし pyproject.toml があれば）:
- git clone ...
- cd <project_root>
- python -m pip install -e .

環境変数 (.env)
- プロジェクトルート（.git または pyproject.toml を基準）に .env / .env.local を置くと、自動で読み込まれます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - テスト等で自動ロードを無効にしたい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

代表的な環境変数
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL (任意): デフォルト http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須): Slack 通知用（このリポジトリで実装されていない機能のため将来用）
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH (任意): デフォルト data/kabusys.duckdb
- SQLITE_PATH (任意): デフォルト data/monitoring.db
- KABUSYS_ENV (任意): development, paper_trading, live のいずれか（デフォルト development）
- LOG_LEVEL (任意): DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

例 .env（最小）
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（基本的なサンプル）

以下は Python REPL／スクリプト内での利用例です。

1) DuckDB スキーマを初期化する
- 初回はスキーマを作成して接続を取得します

from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # または init_schema(":memory:")

2) 日次 ETL を実行する

from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

- ETLResult には取得件数・保存件数・品質チェック結果・エラー一覧が含まれます。

3) 市場カレンダーの夜間更新ジョブを実行する

from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved calendar rows:", saved)

4) ニュース収集ジョブを実行する

from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出に使用する有効コードセット（例: {'7203','6758',...}）
res = run_news_collection(conn, known_codes=set())
print(res)  # {source_name: 新規保存件数}

5) J-Quants の ID トークンを取得する（明示的に必要な場合）

from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して取得

6) 監査DBの初期化（監査専用 DB を別ファイルで用意したい場合）

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")

7) 品質チェックのみ実行する

from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i)

ログ出力
- 標準 logging を使っているため、アプリ側で logging.basicConfig やハンドラを設定してお使いください。
- 環境変数 LOG_LEVEL により既定のログレベルを検証します（Settings.log_level）。

---

## 注意点 / 実装上のポイント

- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml で検出して行います。配布後やテストで不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants API へのリクエストは内部でレート制限（120 req/min）を守るためにスリープ制御を行います。大量の同期リクエストは時間がかかる点に注意してください。
- jquants_client の _request は 401 を検知すると自動的に get_id_token() を呼びトークンをリフレッシュしたうえで 1 回だけリトライします。
- news_collector は SSRF 対策、レスポンスサイズ制限、gzip 解凍後のサイズチェックなど攻撃耐性を考慮しています。
- DuckDB のテーブル定義は多くの CHECK や PRIMARY KEY を含んでおり、ETL 側は冪等な保存（ON CONFLICT DO UPDATE / DO NOTHING）を行います。
- audit.init_audit_schema は UTC タイムゾーンに固定します（SET TimeZone='UTC' を実行）。

---

## ディレクトリ構成

プロジェクトの主要ファイル／モジュール（src 以下）:

src/
  kabusys/
    __init__.py            # パッケージ定義 (version, __all__)
    config.py              # 環境変数 / Settings
    data/
      __init__.py
      jquants_client.py    # J-Quants API クライアント (fetch/save)
      news_collector.py    # RSS → raw_news ETL
      schema.py            # DuckDB スキーマ定義と初期化
      pipeline.py          # ETL パイプライン（run_daily_etl 等）
      calendar_management.py  # マーケットカレンダー関係のユーティリティ
      audit.py             # 監査ログ（signal/order/execution）スキーマ
      quality.py           # データ品質チェック
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py

- strategy / execution / monitoring のディレクトリは骨組み（__init__.py）として用意されています。戦略・発注実装やモニタリング機能はここに実装を追加します。

---

## 開発・テスト時のヒント

- 自動 .env 読み込みを無効化してユニットテストを実行する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB を :memory: にしてテスト用 DB を素早く用意できます:
  - conn = init_schema(":memory:")
- news_collector の _urlopen 等はモジュール内で差し替え（モック）しやすい設計になっています。

---

## 今後の拡張案（例）

- 実際の発注ロジック（kabuステーション連携）を execution パッケージに実装
- Slack 通知や監視ダッシュボードの実装（monitoring）
- 戦略バージョニングとバックテストツールの追加（strategy）
- 非同期化 / 並列化による API スループット向上（ただしレート制限に注意）

---

ご不明な点や README に追加したいサンプル・コマンドがあれば教えてください。必要に応じて README に実行例や .env.example を追記します。