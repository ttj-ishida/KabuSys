# KabuSys

KabuSys は日本株のデータ収集・品質管理・ETL・監査を支援するライブラリ／フレームワークです。J-Quants API から株価・財務・マーケットカレンダーを取得し、DuckDB に冪等的に保存、品質チェックやニュース収集、監査ログ（発注→約定のトレーサビリティ）を提供します。

主な設計目標は信頼性（レート制限・リトライ・トークン自動更新・SSRF対策）と冪等性（ON CONFLICT / RETURNING を活用した安全な保存）です。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルート基準）。環境変数の必須チェックを提供。
  - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- J-Quants API クライアント（`kabusys.data.jquants_client`）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - API レート制御（120 req/min 固定）および指数バックオフ付きリトライ（最大 3 回）
  - 401 応答時のリフレッシュトークンによる自動トークン更新
  - 取得時刻（UTC）を記録して look-ahead bias をトレース可能に

- ニュース収集（`kabusys.data.news_collector`）
  - RSS フィード取得、URL 正規化（トラッキングパラメータの除去）、記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証、プライベートIP 拒否、リダイレクト検査）
  - 受信サイズ上限、gzip 解凍チェック、defusedxml による XML 攻撃防御
  - DuckDB に冪等保存（INSERT ... ON CONFLICT / RETURNING）

- データスキーマ管理（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス作成、DuckDB の初期化ユーティリティ

- ETL パイプライン（`kabusys.data.pipeline`）
  - 差分更新（最終取得日ベース）・バックフィル（デフォルト 3 日）・カレンダー先読み
  - 品質チェック（欠損・スパイク・重複・日付不整合）を実行可能
  - 日次 ETL エントリポイント `run_daily_etl`

- カレンダー管理（`kabusys.data.calendar_management`）
  - 営業日判定、前後営業日取得、期間内営業日リスト、夜間のカレンダー差分更新ジョブ

- データ品質チェック（`kabusys.data.quality`）
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合を検出して問題を列挙

- 監査ログ（`kabusys.data.audit`）
  - シグナル → 発注要求 → 約定 までの監査テーブル定義（UUIDベースのトレーサビリティ）
  - 発注要求は冪等キー（order_request_id）をサポート

---

## セットアップ手順

前提
- Python 3.10 以上を想定（Union 型として `X | None` を使用）
- DuckDB を利用するためローカルディスクに書き込み可能であること

1. リポジトリをクローン／配置
   - プロジェクトルート（pyproject.toml や .git がある場所）を保持してください。

2. 仮想環境作成・有効化（任意だが推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 依存パッケージのインストール
   - 少なくとも以下をインストールしてください（例）:
     ```
     pip install duckdb defusedxml
     ```
   - パッケージを editable インストールする場合（プロジェクトが pyproject.toml を持つ想定）:
     ```
     pip install -e .
     ```

4. 環境変数（.env）を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
   - 必須の環境変数（少なくとも下記をセットしてください）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーションの API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - オプション:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定すると自動 .env ロードを無効化
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）

   - 簡単な `.env` 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方 (例)

ここでは代表的な利用例を示します。Python スクリプトやバッチジョブから呼ぶことを想定します。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")  # ファイルを作成しスキーマを作る
   ```

2. 日次 ETL を実行する
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # target_date を省略すると本日を基準に実行
   print(result.to_dict())
   ```

3. ニュース収集を実行する（RSS → raw_news / news_symbols）
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   ```

4. J-Quants クライアントの直接利用（トークン取得 / データ取得）
   ```python
   from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   # id_token を直接取得（内部では settings.jquants_refresh_token を参照）
   token = get_id_token()
   # 銘柄 or 日付レンジ指定でデータ取得
   records = fetch_daily_quotes(id_token=token, code="7203", date_from=None, date_to=None)
   ```

5. 監査ログ（order_requests / executions）用スキーマ初期化
   ```python
   from kabusys.data.audit import init_audit_db

   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

6. カレンダー更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print("saved calendar rows:", saved)
   ```

注意:
- ETL 関数は例外を捕捉して内部でログに残す設計ですが、呼び出し元でも適切にログや通知を行ってください。
- `run_daily_etl` の `run_quality_checks` を True にすると品質チェック（missing / spike / duplicates / date consistency）を実行します。検出結果は ETLResult.quality_issues に集約されます。

---

## 環境変数一覧（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

- 任意 / 推奨
  - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化

---

## 実装上のポイント / 注意事項

- レート制限
  - J-Quants API は 120 req/min を想定。クライアントでは固定間隔スロットリング（_RateLimiter）で制御しています。

- リトライ
  - ネットワーク/サーバエラー（408/429/5xx）に対して指数バックオフで最大 3 回リトライします。429 の場合、Retry-After ヘッダを優先します。

- トークン自動リフレッシュ
  - 401 を受け取った場合、内部的にリフレッシュトークンから id_token を再取得し 1 回だけリトライします。

- 冪等性
  - DuckDB への保存は多くの箇所で ON CONFLICT DO UPDATE / DO NOTHING / RETURNING を用い、再実行や重複挿入に対して安全な実装になっています。

- セキュリティ
  - RSS 取得は defusedxml と複数の SSRF 対策（スキーム検証、プライベートIP ブロック、リダイレクト検査）を実施しています。
  - .env 読み込みはプロジェクトルートを基準に行うため、意図しないパスからの読み込みを防ぎます。

---

## ディレクトリ構成

主要なファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント + 保存ロジック
    - news_collector.py              — RSS 収集 / 前処理 / 保存
    - schema.py                      — DuckDB スキーマ定義と初期化
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py         — 市場カレンダー管理（営業日判定・更新ジョブ）
    - audit.py                       — 監査ログ（signal/order/execution）スキーマ
    - quality.py                     — データ品質チェック
  - strategy/
    - __init__.py                    — 戦略層（拡張用）
  - execution/
    - __init__.py                    — 発注実行層（拡張用）
  - monitoring/
    - __init__.py                    — 監視・メトリクス（拡張用）

---

## 追加情報 / 開発者向けメモ

- テスト性を意識して各所で依存注入（例: id_token 引数、_urlopen のモック差し替え）をサポートしています。ユニットテストではこれらをモックして API 呼び出しやネットワークを切り離してテストできます。
- DuckDB の接続は `duckdb.DuckDBPyConnection` を直接利用します。初回は schema.init_schema() を使ってテーブルを作成してください。監査ログ用のスキーマは `init_audit_db` / `init_audit_schema` で追加できます。
- 本リポジトリは戦略（strategy）層や発注実行（execution）層の拡張を想定しており、各層は pluggable に実装可能です。

---

README に含める他のサンプルや CI / デプロイの手順等が必要であれば、どの部分を優先して追加するか教えてください。