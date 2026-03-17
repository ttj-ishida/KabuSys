# KabuSys

日本株の自動売買プラットフォーム向けユーティリティ群（データ収集 / ETL / スキーマ / 品質チェック / ニュース収集 / 監査ログ）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買システムのデータ基盤と補助モジュールを提供するパッケージです。本リポジトリは主に以下を目的とします。

- J-Quants API からの市場データ（OHLCV、財務情報、マーケットカレンダー）取得
- DuckDB ベースのスキーマ定義・初期化
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と銘柄抽出
- マーケットカレンダー管理（営業日判定等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 設定管理（.env / 環境変数）およびログレベル制御

設計上のポイント:
- API レート制限やリトライ、トークン自動更新を考慮
- DuckDB への保存は冪等（ON CONFLICT）で安全
- ニュース収集では SSRF / XML Bomb / トラッキングパラメータ除去等のセキュリティ対策を実装
- 品質チェックは Fail-Fast ではなく問題を収集して報告

---

## 機能一覧

- 環境設定読み込み（.env / .env.local / OS 環境変数）
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - トークン自動リフレッシュ、レート制御、指数バックオフ
- DuckDB スキーマ定義と初期化（data.schema.init_schema）
  - Raw / Processed / Feature / Execution 層のテーブル群
- ETL パイプライン（data.pipeline）
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - 差分更新・バックフィル・品質チェック
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、記事 ID 生成、raw_news 保存、銘柄抽出・紐付け
- カレンダー管理（data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job （夜間バッチでカレンダー差分更新）
- データ品質チェック（data.quality）
  - 欠損・スパイク・重複・日付不整合チェック
  - run_all_checks でまとめて実行
- 監査ログスキーマ（data.audit）
  - signal_events, order_requests, executions テーブル等の初期化（init_audit_schema / init_audit_db）

---

## 要求環境・依存パッケージ

- Python 3.10+
- 必要な外部パッケージ（例）:
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install duckdb defusedxml
# 開発パッケージがあればここに追加
```

（プロジェクトをパッケージとして配布する場合は requirements.txt / pyproject.toml を用意してください）

---

## 環境変数（必須／任意）

自動で .env / .env.local をプロジェクトルートから読み込みます（無効化可）。主に以下を設定してください。

必須:
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
- KABU_API_PASSWORD：kabuステーション API のパスワード
- SLACK_BOT_TOKEN：Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID：Slack チャネル ID

任意（デフォルト値あり）:
- KABUSYS_ENV：development / paper_trading / live（デフォルト: development）
- LOG_LEVEL：DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD：1 をセットすると自動 .env ロードを無効化

簡単な .env 例（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

テスト時に自動ロードを抑制する場合:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
4. 必要な環境変数を .env に設定（上記参照）
5. DuckDB スキーマ初期化（Python REPL やスクリプトで実行）
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ディレクトリが無ければ自動作成
   conn.close()
   ```
6. 監査ログ用 DB 初期化（必要に応じて）
   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   audit_conn.close()
   ```

---

## 使い方（主要な API と例）

以下はプログラムから利用する基本例です。アプリケーション内でスケジューラ（cron / systemd timer / Airflow 等）から定期実行してください。

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data import schema, pipeline

# DB 接続（既存 DB に接続）
conn = schema.get_connection("data/kabusys.duckdb")

# 日次ETL（省略時は今日を対象）
result = pipeline.run_daily_etl(conn, target_date=date.today())

print(result.to_dict())
conn.close()
```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は有効な銘柄コードセット（例: 上場銘柄リスト）
known_codes = {"7203", "6758", ...}
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)
conn.close()
```

- マーケットカレンダー夜間更新ジョブ
```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
conn.close()
```

- J-Quants の ID トークンを手動で取得（テスト等）
```python
from kabusys.data import jquants_client as jq
token = jq.get_id_token()  # settings.jquants_refresh_token を使用
print(token)
```

- 品質チェック単体実行
```python
from datetime import date
from kabusys.data import quality, schema

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date(2024, 1, 1))
for i in issues:
    print(i)
conn.close()
```

---

## 運用上の注意

- レート制限: J-Quants は 120 req/min。クライアントは内部で RateLimiter を用いて制御しますが、大量並列リクエストは避けてください。
- トークン更新: 401 を受けると自動でリフレッシュを試みます。refresh token は安全に保管してください。
- DuckDB ファイルはローカルに保存されます。バックアップ・ロック・同時アクセスポリシーは運用で検討してください（DuckDB の動作に依存）。
- news_collector は外部フィードから HTML/XML を取得します。SSRF・XML Bomb・大容量レスポンス等の防御を行っていますが、運用環境のセキュリティポリシーに従ってください。
- ETL は各ステップを独立してエラーハンドリングします。エラー一覧は ETLResult.errors / quality_issues で参照できます。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 定義（J-Quants / kabu / Slack / DB パス / 環境判定）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得 / 保存 / リトライ / レート制御）
    - news_collector.py
      - RSS 取得、記事正規化、raw_news 保存、銘柄抽出
    - schema.py
      - DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution）
    - pipeline.py
      - ETL パイプライン（差分更新・バックフィル・品質チェック）
    - calendar_management.py
      - マーケットカレンダー管理、営業日判定、calendar_update_job
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）初期化
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - execution/
    - __init__.py
    - （発注実装はこの層に配置）
  - strategy/
    - __init__.py
    - （戦略実装はこの層に配置）
  - monitoring/
    - __init__.py
    - （監視・メトリクス用モジュール）

---

## よくある質問 / トラブルシュート

- .env が読み込まれない
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に自動で .env/.env.local を読み込みます。テストや明示的制御が必要な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化で権限エラー
  - 指定した DUCKDB_PATH の親ディレクトリが存在しないと自動作成しますが、ファイルシステム側の書き込み権限を確認してください。
- J-Quants から 401 が返る
  - get_id_token() が refresh token を用いて id token を取得します。refresh token が正しいか、有効期限を確認してください。コードは 401 受信時に自動リフレッシュを 1 回行います。

---

## 今後の拡張案（例）

- 発注／バックテストモジュールの実装（execution 層の充実）
- 戦略テンプレートとパラメータ管理（strategy 層）
- メトリクス・監視ダッシュボード（monitoring 層）
- テストインフラ（モック J-Quants / DuckDB の CI 用セットアップ）

---

必要であれば README にサンプル .env.example ファイル、Docker / systemd / cron のサンプル、より詳細な API リファレンス（関数の引数・戻り値）を追加します。どの追加情報が必要か教えてください。