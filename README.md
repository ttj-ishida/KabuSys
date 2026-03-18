# KabuSys

日本株向け自動売買データ基盤／ETL／監査ライブラリ

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。主に以下を目的とします。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する ETL パイプライン
- RSS からニュースを収集して正規化・保存するニュースコレクタ
- データ品質チェック、マーケットカレンダー管理、監査ログ（シグナル→発注→約定のトレーサビリティ）用テーブル定義
- 発注・戦略・モニタリング等のための基盤モジュール（スケルトン）

設計上の特徴：
- API レート制限（J-Quants: 120 req/min）遵守（固定間隔スロットリング）
- リトライ／トークン自動リフレッシュ（401 の場合1回リトライ）
- Look-ahead bias に配慮した fetched_at / UTC 時刻保存
- DuckDB への保存は冪等（ON CONFLICT）で安全

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - レートリミット制御、リトライ、ID トークン取得
  - DuckDB へ冪等保存する save_* 関数

- data/pipeline.py
  - 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
  - 個別ジョブ（prices / financials / calendar）の実行補助

- data/schema.py
  - DuckDB スキーマ（Raw / Processed / Feature / Execution 層）定義
  - スキーマ初期化関数 init_schema(), get_connection()

- data/news_collector.py
  - RSS フィード取得、前処理、記事ID正規化（SHA-256）、DuckDB への冪等保存
  - SSRF / XML Bomb / レスポンスサイズ対策を実装

- data/calendar_management.py
  - market_calendar を用いた営業日判定・次/前営業日取得・カレンダー更新ジョブ

- data/quality.py
  - 欠損・スパイク・重複・日付不整合などのデータ品質チェック

- data/audit.py
  - 監査ログ（signal_events / order_requests / executions）テーブルと初期化を提供

- config.py
  - 環境変数読み込み（.env / .env.local 自動ロード）
  - 必須設定チェック（例: JQUANTS_REFRESH_TOKEN 等）

---

## 動作要件 / 依存（目安）

- Python 3.10+
- 必要な外部パッケージ（主なもの）:
  - duckdb
  - defusedxml

（プロジェクトに pyproject.toml 等があればそちらに依存が記載されます。最低限 duckdb と defusedxml をインストールしてください。）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## 環境変数 / 設定

自動でプロジェクトルート（.git または pyproject.toml を探索）を探し `.env` と `.env.local` を読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（Settings クラスで参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）

任意 / デフォルト:
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 で無効）

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_pass
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env`（上記サンプル参照）を作成するか、OS の環境変数を設定します。
   - 自動 .env 読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. DuckDB スキーマ初期化
   - ライブラリから直接初期化できます（例は次節）。

---

## 使い方（サンプル）

以下は主な利用例（Python スクリプトや REPL）です。

- DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema

# ファイルパス例
conn = init_schema("data/kabusys.duckdb")
```

- 監査ログ専用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- 日次 ETL 実行:
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

- ニュース収集（RSS）ジョブ:
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758"}  # 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # ソースごとの新規保存数
```

- J-Quants から直接データ取得（低レベル関数）:
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

token = get_id_token()  # settings.jquants_refresh_token を使用してトークン取得
quotes = fetch_daily_quotes(id_token=token, date_from=None, date_to=None)
```

- 品質チェックを手動実行:
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点:
- ETL は差分更新を行います（DBの最終取得日を参照）。初回ロードは過去データを取得します。
- run_daily_etl は市場カレンダーを先に取得し、営業日に調整して株価・財務を取得します。
- ログや例外は標準 logging で出力されます。実運用ではロギング設定を行ってください。

---

## ディレクトリ構成（主要ファイル）

（ソースは `src/kabusys` 配下を想定）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント、保存ロジック
    - news_collector.py                — RSS ニュース収集・前処理・保存
    - pipeline.py                      — ETL パイプライン（日次 / 個別ジョブ）
    - schema.py                        — DuckDB スキーマ定義・初期化
    - calendar_management.py           — マーケットカレンダー管理
    - audit.py                         — 監査ログスキーマと初期化
    - quality.py                       — データ品質チェック
  - strategy/
    - __init__.py                      — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                      — 発注実行関連（拡張ポイント）
  - monitoring/
    - __init__.py                      — 監視関連（拡張ポイント）

---

## 実装上の注意 / 補足

- API 制限やネットワーク不安定性を考慮して、jquants_client は RateLimiter と指数バックオフを実装しています。
- fetch_* 関数はページネーション対応、save_* 関数は ON CONFLICT による冪等保存です。
- news_collector は SSRF、XML Bomb、gzip 膨張攻撃などに対して防御策を組み込んでいます（スキーム検証、プライベートIPチェック、受信サイズ制限、defusedxml）。
- DuckDB のスキーマは Raw / Processed / Feature / Execution / Audit をカバーしており、監査用テーブル群は UTC タイムゾーンで保存する設計です。
- KABUSYS_ENV によって挙動（例: 実際の発注を行うかどうかなど）を切り替える想定です（development / paper_trading / live）。

---

## さらに進めるために

- strategies や execution ブロックを実装して実運用フロー（シグナル生成→発注→監査）を構築してください。
- 運用環境ではモニタリング、アラート（例: Slack 通知）、および安全な鍵管理（シークレットストア）を併用してください。
- パッケージ化（pyproject.toml / setup.cfg）や CI（テスト、静的解析）、コンテナ化も検討してください。

---

ご要望があれば、README にさらに以下を追加できます:
- サンプル .env.example ファイル
- 具体的な運用手順（cron / Airflow / GitHub Actions でのスケジュール実行）
- よくあるエラーとトラブルシューティングガイド

必要であれば希望内容を教えてください。