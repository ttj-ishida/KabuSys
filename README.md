# KabuSys

日本株自動売買／データプラットフォーム (KabuSys)

簡潔な概要、主要機能、セットアップ方法、基本的な使い方、ディレクトリ構成をまとめた README です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
主に以下を目的としたモジュール群を提供します：

- J-Quants API からの市場データ（株価、財務、取引カレンダー）取得と DuckDB への冪等保存
- RSS からのニュース収集と記事 → 銘柄紐付け
- ETL（差分取得、バックフィル、品質チェック）パイプライン
- マーケットカレンダー管理、営業日判定ロジック
- 監査（signal → order → execution のトレーサビリティ）テーブル定義
- データ品質チェック（欠損、重複、スパイク、日付不整合）

設計上のポイント：
- API レート制御・リトライ・トークン自動リフレッシュを備えた堅牢な API クライアント
- DuckDB を使ったローカルデータレイヤ（Raw / Processed / Feature / Execution）
- 冪等性を重視（ON CONFLICT / RETURNING を多用）
- SSRF / XML Bomb / レスポンスサイズ制限などセキュリティ考慮

---

## 機能一覧

- 環境変数管理（.env 自動読み込み、保護機能）
- J-Quants クライアント（株価日足、財務、取引カレンダー）
  - レートリミット（120 req/min）、再試行、401時トークン再発行対応
  - データ取得日時（fetched_at）で Look-ahead Bias を回避
- DuckDB スキーマ定義・初期化（data.schema）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- ニュース収集（RSS）と raw_news / news_symbols への保存
  - URL 正規化、トラッキングパラメータ除去、SSRF対策、XMLパースの安全化
- マーケットカレンダー管理（営業日判定、前後営業日検索、夜間更新ジョブ）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal_events / order_requests / executions）と初期化支援
- (将来) 戦略・発注・モニタリング用のパッケージ骨組み（strategy / execution / monitoring）

---

## 必要条件・依存

- Python 3.10 以上（型注釈に | を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

例（pip）:
```bash
pip install duckdb defusedxml
```

その他、運用する機能に応じて追加パッケージ（Slack SDK 等）が必要になる場合があります。

---

## 環境変数

自動でルートプロジェクトの `.env` / `.env.local` を読み込みます（CWD に依存しない検出）。テストや明示的に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数：
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション等の API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

オプション：
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング等）パス（デフォルト: data/monitoring.db）

例 `.env`（簡易）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <repository-url>
cd <repository-dir>
```

2. Python 仮想環境の作成（任意）
```bash
python -m venv .venv
source .venv/bin/activate
```

3. 依存パッケージをインストール
```bash
pip install duckdb defusedxml
# 追加の依存があればここでインストール
```

4. 環境変数設定
- プロジェクトルートに `.env` ファイルを作成するか、OS 環境変数を設定してください。
- 必須変数は上記参照。

5. DuckDB スキーマ初期化（例）
Python REPL またはスクリプトで：
```python
from kabusys.data import schema
from kabusys.config import settings

# ディスク上のファイルを使う例
conn = schema.init_schema(settings.duckdb_path)
# 監査ログ用スキーマを追加する場合
from kabusys.data import audit
audit.init_audit_schema(conn)
```

---

## 使い方（主要 API の例）

ここでは代表的な利用フローを示します。詳細は各モジュールの docstring を参照してください。

1) 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from kabusys.config import settings
from datetime import date

conn = schema.init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
# known_codes は既知の銘柄コードセット（抽出用）
known_codes = {"7203", "6758", "9984"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

3) J-Quants から株価取得（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings からリフレッシュトークンを使用して取得
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

4) マーケットカレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print("saved", saved)
```

5) 品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data import schema
conn = schema.get_connection(settings.duckdb_path)
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

注意:
- ETL / API 呼び出しはネットワーク・API レート・認証に依存します。ログレベルを上げて挙動を確認してください。
- run_daily_etl 等は内部で例外を捕捉して処理を継続するため、戻り値の ETLResult の errors / quality_issues を確認して運用判断を行ってください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル構成（src 以下）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（fetch / save / retry / rate limit）
    - news_collector.py                — RSS ニュース収集・保存・銘柄抽出
    - schema.py                        — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py                      — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py           — カレンダー管理、営業日判定、更新ジョブ
    - audit.py                         — 監査ログ用テーブル定義と初期化
    - quality.py                       — データ品質チェック
  - strategy/
    - __init__.py                      — 戦略レイヤ（骨組み）
  - execution/
    - __init__.py                      — 発注・ブローカー連携（骨組み）
  - monitoring/
    - __init__.py                      — 監視・メトリクス（骨組み）

---

## 運用上の注意点 / 補足

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化できます。
- J-Quants の API レート制限（120 req/min）に合わせた制御がありますが、運用時は API 利用状況に注意してください。
- ニュース収集では外部 URL の検証（スキーム制限、プライベートアドレス拒否）、XML パース時の安全化、レスポンスサイズ制限などを実装していますが、追加の運用ルール（接続タイムアウト、プロキシ等）は環境に合わせて設定してください。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作成されます。バックアップや運用ポリシーを考慮してください。
- 監査ログ（audit）は UTC タイムゾーンでの保存を前提にしています（init_audit_schema は SET TimeZone='UTC' を実行します）。

---

## 貢献 / テスト

- 新しい機能追加や修正の際は既存の DuckDB スキーマやデータ整合性を壊さないようにしてください。
- 単体テストでは .env 自動読み込みをオフにするか、テスト用の環境変数を設定してください。

---

README は以上です。さらに具体的な利用例（戦略実装や発注フロー、Slack 通知の実装例等）が必要であればサンプルやテンプレートを追加で作成します。必要なものを教えてください。