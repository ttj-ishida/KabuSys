# KabuSys

日本株自動売買システムのライブラリ (KabuSys)。  
市場データ取得、DuckDB スキーマ管理、監査ログ、戦略・実行・モニタリング向けの基盤モジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の役割を持つモジュール群を含むプロジェクトです。

- J-Quants API から株価・財務・マーケットカレンダー等のデータを取得
- DuckDB によるデータスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）スキーマ
- 環境変数による設定管理（.env / .env.local の自動読み込み）
- 低レベルの実行／戦略／モニタリング用パッケージ構造（雛形）

設計上のポイント:
- J-Quants API はレート制限（120 req/min）を尊重する RateLimiter を適用
- リトライ（指数バックオフ）、401 時は自動トークンリフレッシュ
- データ保存は冪等（ON CONFLICT DO UPDATE）で重複を取り除く
- 監査ログは UUID 連鎖で完全トレース可能に設計

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルート基準）
  - 必須設定の取得ヘルパー（settings）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得（ページネーション対応）
  - JPX マーケットカレンダー取得
  - トークン取得・キャッシュ・自動リフレッシュ
  - レート制御・リトライ機構
  - DuckDB への保存ヘルパー（save_* 関数）で冪等保存
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL 定義
  - インデックス作成
  - init_schema / get_connection
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL
  - init_audit_schema / init_audit_db
- パッケージ構造（strategy / execution / monitoring） — 拡張用の雛形

---

## 必要要件（依存）

最低限の依存ライブラリ（代表例）:
- Python 3.9+
- duckdb

実際のプロジェクトでは requests 等の追加依存やパッケージ管理（poetry / pip）を用いる想定です。

---

## セットアップ手順

1. リポジトリをクローン／取得する

2. 仮想環境を作成して依存をインストール
   （例: pip と duckdb のみが必要な場合）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を作成します。
   - 自動読み込みはデフォルト ON（プロジェクトルートの .git または pyproject.toml を検出して読み込み）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. DuckDB スキーマを初期化（次の「使い方」参照）

---

## 環境変数（主なキー）

以下はこのコードベースで参照される主な環境変数です。必須のものは README または .env.example を参考に設定してください。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

省略可（デフォルトあり／任意）:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)

注意:
- .env/.env.local の読み込み順は OS 環境変数 > .env.local > .env。`.env.local` は .env を上書き可能です。
- OS 環境のキーは保護され、上書きされません。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットします（テスト用途）。

---

## 使い方（簡単な例）

以下は DuckDB スキーマ初期化と J-Quants API から株価日足を取得して保存するサンプルです。

1) DuckDB スキーマの初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照します（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2) J-Quants からデータ取得して保存
```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# 例: 銘柄コード 7203（トヨタ）の日足を取得して保存
records = fetch_daily_quotes(code="7203", date_from=date(2020, 1, 1), date_to=date(2020, 12, 31))
n = save_daily_quotes(conn, records)
print(f"保存した件数: {n}")
```

3) 監査ログスキーマを追加する（既存の conn に対して）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

4) 監査用に専用 DB を作る場合
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

注意点:
- J-Quants API 呼び出しは内部でレート制御（120 req/min）とリトライを行います。
- get_id_token() によるトークン取得は自動的に settings.jquants_refresh_token を使用します。トークン未設定時は ValueError が発生します。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（src/kabusys 以下）

- __init__.py
  - パッケージ初期化。公開サブパッケージを定義。
- config.py
  - 環境変数読み込み・Settings クラス（アプリ設定）の定義
  - .env / .env.local の自動読み込みロジック
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント、トークン取得、fetch_* / save_* 関数
  - schema.py
    - DuckDB の DDL 定義と init_schema / get_connection
  - audit.py
    - 監査ログ向け DDL と初期化関数（init_audit_schema / init_audit_db）
  - audit, schema などでさらに index や制約を定義
- strategy/
  - __init__.py（戦略層の雛形）
- execution/
  - __init__.py（発注・約定管理の雛形）
- monitoring/
  - __init__.py（モニタリング関連の雛形）

（ファイル名はコードベースをそのまま反映しています）

---

## 開発・注意事項

- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。配布後は CWD に依存せずに動作することを意図しています。
- J-Quants API のレート制限・HTTP リトライ・401 リフレッシュの挙動は jquants_client.py に実装されています。必要に応じてログ出力レベルやリトライ回数などを調整してください。
- DuckDB に対する DDL は冪等で設計されています。init_schema は既存テーブルを上書きしません（CREATE IF NOT EXISTS）。
- 監査ログは削除しない前提（ON DELETE RESTRICT）で設計されています。監査データを破棄する場合は運用ポリシーを明確にしてください。
- テスト実行時に .env の自動ロードを避けたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

必要であれば README に CI / テスト手順、実際のデプロイ手順（kabuステーション連携、Slack 通知の利用方法など）やサンプルスクリプトを追加します。どの内容を加えるか指示してください。