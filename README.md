# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。  
J-Quants / DuckDB を使ったデータプラットフォーム、ETL、品質チェック、監査ログ、戦略・実行・監視の骨組みを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買システムの基盤モジュール群です。主な目的は次のとおりです。

- J-Quants API からの市場データ・財務データ・マーケットカレンダー取得
- DuckDB を用いた永続化（スキーマ、インデックス、監査テーブル）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- 品質チェック（欠損・スパイク・重複・日付不整合）の自動化
- 発注／約定の監査ログ（トレーサビリティ）構造

設計上のポイント:
- API レート制限（120 req/min）を守るレートリミッタ
- リトライ（指数バックオフ、401時のトークン自動リフレッシュ含む）
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- すべての TIMESTAMP は UTC を意識

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー）
  - レート制御、リトライ、トークン自動リフレッシュ
  - DuckDB への保存関数（save_daily_quotesなど）
- data/schema.py
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - テーブル群・インデックスの作成・接続取得ユーティリティ
- data/pipeline.py
  - 日次 ETL（差分取得、バックフィル、品質チェック）
  - run_daily_etl により一括実行
- data/quality.py
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue を返す）
- data/audit.py
  - 発注〜約定までの監査ログテーブル定義・初期化（冪等キー、ステータス管理）
- config.py
  - 環境変数読み込み（.env / .env.local の自動ロード）
  - 必須設定の抽象化（settings オブジェクト経由）
- その他
  - strategy/, execution/, monitoring/ のパッケージプレースホルダ（拡張ポイント）

---

## 必要条件

- Python 3.10 以上（PEP 604 の型注釈などを使用）
- 依存ライブラリ（例）
  - duckdb
- ネットワークから J-Quants API へ接続可能な環境

（実際の requirements.txt / pyproject.toml を用意して pip インストールしてください）

---

## セットアップ手順

1. リポジトリをクローン／取得
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存ライブラリをインストール
   - pip install duckdb
   - （プロジェクトの pyproject.toml / requirements.txt があればそれを使う）

4. 環境変数を設定
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルト値あり）:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live）デフォルト: development
     - LOG_LEVEL（DEBUG/INFO/...）デフォルト: INFO
   - .env/.env.local をプロジェクトルートに置くと自動で読み込まれます（自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

5. データベーススキーマの初期化
   - DuckDB をファイルで使用する場合、親ディレクトリは自動作成されます。
   - 例（Python スクリプト内）:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

   - 監査ログのみ別 DB に分けたい場合:
     from kabusys.data import audit
     conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（サンプル）

基本的な日次 ETL を実行する流れ（最小例）:

- スクリプト例 run_etl.py:

```python
from datetime import date
from kabusys.data import schema, pipeline

# DB 初期化（初回のみ）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると今日）
result = pipeline.run_daily_etl(conn, target_date=date.today())

# 結果確認
print(result.to_dict())
```

- 取得／保存の個別実行例:

```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
import duckdb

conn = schema.get_connection("data/kabusys.duckdb")
# id_token を明示的に取得することも可能
id_token = jq.get_id_token()
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

- 品質チェックを手動で実行する例:

```python
from kabusys.data import quality, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

---

## 設定（環境変数）

主要な環境変数一覧:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)、デフォルトは development
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）、デフォルト INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動読み込みを無効化

.env の構文は一般的な形式に対応（export プレフィックス、クォート、コメント処理など）。

---

## 注意・設計上の備考

- J-Quants API のレート制限（120 req/min）を内部で守るため、長時間の大量フェッチでは制限に注意する必要があります。
- HTTP 408/429/5xx に対しては指数バックオフで再試行します。401 受信時はリフレッシュして再試行を試みます（ただし無限ループは回避）。
- DuckDB への挿入は ON CONFLICT DO UPDATE で冪等性を確保しています。
- ETL の品質チェックは「Fail-Fast」ではなくすべての問題を収集し呼び出し元が判断できるようにしています。
- 監査ログ（order_requests / executions / signal_events）は削除しない前提、UTC タイムスタンプを使用します。

---

## ディレクトリ構成

リポジトリの主要ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント、保存関数
    - schema.py          — DuckDB スキーマ / init_schema / get_connection
    - pipeline.py        — ETL パイプライン（差分更新・品質チェック）
    - quality.py         — 品質チェック
    - audit.py           — 監査ログ（トレーサビリティ）初期化
  - strategy/
    - __init__.py        — 戦略関連モジュール（拡張ポイント）
  - execution/
    - __init__.py        — 発注/実行関連（拡張ポイント）
  - monitoring/
    - __init__.py        — 監視関連（拡張ポイント）

- pyproject.toml / setup.cfg 等（プロジェクトルートに配置）
- .env.example（プロジェクトルートに想定されるサンプル）

---

## 開発・拡張ポイント

- strategy、execution、monitoring パッケージは拡張用のプレースホルダです。戦略の導入、ポートフォリオ管理、発注シーケンス、Slack 通知などを実装して接続してください。
- DuckDB スキーマは DataPlatform.md に基づく階層構造（Raw / Processed / Feature / Execution）で設計済みです。必要に応じて拡張・マイグレーションを行ってください。
- テストを容易にするため、pipeline の関数は id_token の注入や :memory: DuckDB を利用できます。

---

## ライセンス / 貢献

- ライセンス情報や貢献ガイドはリポジトリルートの LICENSE / CONTRIBUTING.md を参照してください（存在しない場合はプロジェクト管理者に確認してください）。

---

何か追記してほしい項目や、サンプルスクリプトの具体化（cron設定、Dockerfile など）が必要であれば教えてください。