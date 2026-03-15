# KabuSys

日本株の自動売買プラットフォーム向けユーティリティ群（ライブラリ）。  
データ取得・永続化（DuckDB スキーマ含む）、環境設定管理、監査ログの初期化などの共通処理を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムで利用するための共通ライブラリです。主に以下を提供します。

- 外部データ取得クライアント（J-Quants API）
- データ永続化用 DuckDB スキーマと初期化ユーティリティ
- 監査ログ（signal → order → execution のトレース）スキーマ初期化
- 環境変数管理（.env ファイル自動読み込み、必須設定のラップ）

設計ポリシーとしては、API レート制御、リトライ、トークン自動リフレッシュ、Look‑ahead バイアス防止（fetched_at の記録）、および冪等性（ON CONFLICT / UPDATE）を重視しています。

---

## 機能一覧

- 環境設定（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得ラッパー（例: JQUANTS_REFRESH_TOKEN）
  - KABUSYS_ENV / LOG_LEVEL 等の検証

- J-Quants API クライアント（kabusys.data.jquants_client）
  - ID トークン取得（refresh token → id token）
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レートリミッタ（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 の自動トークンリフレッシュ
  - DuckDB への保存関数（冪等 INSERT ... ON CONFLICT DO UPDATE）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス作成
  - init_schema(), get_connection() を提供

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions の DDL とインデックス
  - init_audit_schema(), init_audit_db() を提供
  - UTC タイムゾーン固定、冪等性／トレーサビリティ重視

- パッケージ骨組み
  - strategy/, execution/, monitoring/ のパッケージ（将来的な拡張用）

---

## セットアップ手順

前提: Python 3.10+ を想定（typing の Union | 記法を使用）

1. リポジトリをクローンして、ソースを配置（src-layout を想定）:
   ```
   git clone <repo>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）:
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例: duckdb）。プロジェクトに requirements.txt がある場合はそれを使用してください。最低限必要な依存は duckdb です。
   ```
   pip install duckdb
   ```

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くことで自動読み込みされます（起動時に自動で読み込まれます）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
   KABU_API_PASSWORD="your_kabu_api_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   DUCKDB_PATH="data/kabusys.duckdb"
   SQLITE_PATH="data/monitoring.db"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下は主要な処理の利用例です。

- DuckDB スキーマを初期化する
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ作成
  ```

- 監査ログテーブルを既存接続に追加する
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)  # conn は init_schema が返した接続など
  ```

- J-Quants API から日足を取得して保存する
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")

  # 特定銘柄・期間を指定して取得
  from datetime import date
  records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))

  # DuckDB に保存（raw_prices テーブルに ON CONFLICT 更新で保存）
  n = save_daily_quotes(conn, records)
  print(f"保存件数: {n}")
  ```

- ID トークンを直接取得する
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- 設定値（ラッパー）を取得
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意点:
- J-Quants API はレート制限（120 req/min）を組み込んでいます。クライアントは _RateLimiter による固定間隔スロットリングを行います。
- _request は 408 / 429 / 5xx に対して指数バックオフでリトライします。401 を受けた場合はトークンを自動でリフレッシュし 1 回だけ再試行します。
- DuckDB へは冪等的に挿入されるように ON CONFLICT DO UPDATE を利用しています。

---

## ディレクトリ構成

主要ファイル構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存ロジック）
    - schema.py             — DuckDB スキーマ定義 & init_schema()
    - audit.py              — 監査ログスキーマ & init_audit_schema()
    - audit.py              — （監査関連ユーティリティ）
    - (その他のデータユーティリティ)
  - strategy/
    - __init__.py           — 戦略関連パッケージ（拡張ポイント）
  - execution/
    - __init__.py           — 発注実行関連パッケージ（拡張ポイント）
  - monitoring/
    - __init__.py           — モニタリング関連パッケージ（拡張ポイント）

補足:
- schema.py には Raw / Processed / Feature / Execution 各層の DDL が含まれており、init_schema() で一括作成されます。
- audit.py には監査用テーブル群（signal_events, order_requests, executions）とインデックス作成ロジックがあります。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — 通知用 Slack ボットトークン
- SLACK_CHANNEL_ID — 通知用 Slack チャネル ID

任意（デフォルト値あり）:
- KABUSYS_ENV — execution 環境（development / paper_trading / live）※デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）※デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（値を設定すると無効）

.env の書式は一般的なシェル形式を想定しており、' または " で囲った値、export を付けた行、コメント等に対応しています。

---

## トラブルシューティング

- .env が読み込まれない
  - プロジェクトルートの検出は __file__ を起点に `.git` または `pyproject.toml` を探索します。ルートが見つからない場合は自動読み込みをスキップします。
  - 自動読み込みを無効化した場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` がセットされています。これを解除してください。
  - 明示的に環境変数をエクスポートして起動することも可能です。

- J-Quants API の 401 が頻発する
  - refresh token が無効または期限切れの可能性があります。`JQUANTS_REFRESH_TOKEN` を確認してください。
  - get_id_token() は allow_refresh=False の内部呼び出し回避ロジックを持っていますが、上手くいかない場合はトークンの確認が必要です。

- DuckDB に書き込めない / ディレクトリがない
  - DUCKDB_PATH の親ディレクトリが自動作成されますが、アクセス権限等が問題になる場合があります。適切なパーミッションを確認してください。

---

## 拡張・実装メモ（開発者向け）

- strategy/, execution/, monitoring/ 配下は将来的に実装を追加する想定のプレースホルダです。
- jquants_client のページネーションは pagination_key を使用しており、ID トークンはモジュールキャッシュで共有されています（ページネーション間の再認証を防止）。
- DuckDB のテーブル DDL は現場の要件に基づいて厳密な CHECK や FK、インデックスを設定しており、スキーマ変更は慎重に行ってください。
- 監査スキーマは削除されない運用（ON DELETE RESTRICT）を前提にしており、updated_at はアプリ側で制御します。

---

必要であれば、この README を英語版に翻訳したり、具体的なサンプルスクリプト（データ収集バッチ、スケジュール例、監査ログの参照クエリ等）を追加できます。どの部分を詳細化したいか教えてください。