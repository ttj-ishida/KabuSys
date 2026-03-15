# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。  
データ取得・永続化（DuckDB）・監査ログ・戦略層・発注層の基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリ／フレームワークです。

- J-Quants API からの市場データ（株価日足、財務データ、JPX カレンダー等）の取得
- DuckDB を用いたスキーマ定義とデータ永続化（Raw / Processed / Feature / Execution 層）
- シグナル → 発注 → 約定 の監査（トレーサビリティ）用テーブル
- 環境変数管理、設定読み込みのユーティリティ
- 将来的に戦略・発注・モニタリングの実装を組み込むためのパッケージ構造

設計上の特徴：
- J-Quants クライアントはレート制限（120 req/min）を順守し、リトライ・トークン自動リフレッシュ等の耐障害性を備えます。
- 取得時刻（fetched_at）や UTC タイムスタンプを明示的に扱い、Look‑ahead bias 防止・トレーサビリティを確保します。
- DuckDB への書き込みは冪等になるよう ON CONFLICT による更新を行います。

---

## 主な機能一覧

- 環境変数ロード・管理（.env / .env.local の自動読み込み、必須キーチェック）
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
- J-Quants API クライアント
  - レートリミット管理（120 req/min、固定間隔スロットリング）
  - リトライ（最大 3 回、指数バックオフ）、401 の自動トークンリフレッシュ
  - ページネーション対応
  - fetch_* 系関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - DuckDB へ保存する save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）
- DuckDB スキーマ定義（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル群、インデックス定義
  - init_schema(db_path) により初期化（冪等）
  - get_connection(db_path) で接続取得
- 監査ログスキーマ（data.audit）
  - signal_events, order_requests, executions を定義
  - init_audit_schema(conn) / init_audit_db(db_path)
  - 監査用のインデックスを含む
- パッケージ構成により strategy / execution / monitoring の拡張ポイントを提供

---

## 前提・依存

- Python 3.10+
  - 型注釈に union 演算子（A | B）を使用しているため 3.10 以上を推奨します
- 必要パッケージ（最低限）
  - duckdb
- 標準ライブラリのみで動作する箇所も多いですが、実運用では追加の HTTP クライアントやログ周り、発注 API クライアント等が必要になります。

推奨インストール例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# パッケージを editable インストールできる packaging が整っていれば:
# pip install -e .
```

---

## 環境変数（必須・推奨）

必須（アプリ起動時に settings.* を参照する機能が使えます）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）

任意（デフォルト値あり）:
- KABUSYS_ENV — 環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）デフォルト: INFO
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（デフォルト: data/monitoring.db）

.env ファイルはプロジェクトルートの .git または pyproject.toml を起点に探索され、優先順位は:
OS 環境変数 > .env.local > .env
です。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

注意: シークレットはリポジトリ / 公開場所に保存しないでください。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <リポジトリ URL>
   cd <repo>
   ```

2. 仮想環境の作成と依存のインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb
   # 追加の依存が発生したら適宜インストール
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成して必要な値を設定します。例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```
   - もしくは OS 環境変数で設定してください。

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトから初期化します:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
     # 監査ログを別 DB で使いたい場合:
     # from kabusys.data.audit import init_audit_db
     # audit_conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（簡単な例）

J-Quants から日足を取得して DuckDB に保存する例:

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

# DB 初期化（既存ならスキップして接続を返す）
conn = init_schema(settings.duckdb_path)

# 日足取得（例: 銘柄コード 7203、期間指定）
records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))

# DuckDB に保存（冪等）
count = save_daily_quotes(conn, records)
print(f"保存件数: {count}")
```

トークンの取得（手動）:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使う
```

監査ログの初期化（既存の conn に追加）:
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # conn は init_schema() の返り値など
```

注意点:
- fetch_* 系関数は内部でレート制御とリトライを行います。大量取得時は 120 req/min を意識してください。
- save_* 系は PK に基づいて ON CONFLICT DO UPDATE を行うので冪等です。
- すべてのタイムスタンプは UTC で扱われることを想定しています。

---

## ディレクトリ構成

リポジトリ内のおおまかな構成（提供コードに基づく）:

- src/kabusys/
  - __init__.py               — パッケージ定義（__version__ 等）
  - config.py                 — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得 + 保存）
    - schema.py               — DuckDB スキーマ定義 / init_schema / get_connection
    - audit.py                — 監査ログ（signal_events / order_requests / executions）
    - audit.py
  - strategy/
    - __init__.py             — 戦略層用パッケージ（拡張ポイント）
  - execution/
    - __init__.py             — 発注層用パッケージ（拡張ポイント）
  - monitoring/
    - __init__.py             — 監視・メトリクス用（拡張ポイント）

その他:
- .env / .env.local           — 環境変数（プロジェクトルートに配置）
- data/...                   — デフォルトで DuckDB ファイルなどを出力する場所

---

## 開発上のメモ / 設計意図

- データ取得時に fetched_at を UTC で保存することで、システムがデータを「いつ知り得たか」を後から遡れるようにしています（Look‑ahead bias 対策）。
- J-Quants クライアントはページネーション中も同一の id_token を共有するため、内部キャッシュを保持しています。401 を受けた場合は 1 回だけ自動リフレッシュして再試行します。
- DuckDB のテーブル設計は Raw → Processed → Feature → Execution の層を想定しており、トレーサビリティ（監査ログ）も別途用意しています。
- 監査ログは削除しない前提（ON DELETE RESTRICT 等）で、order_request_id を冪等キーとして二重発注防止を助ける設計です。

---

## 連絡・貢献

バグ報告や機能提案、ドキュメント修正のプルリクエストは welcome です。  
実運用やブローカー API との連携実装については別モジュール（execution 層）を拡張して行ってください。

---

README に記載のない点や、サンプルスクリプトの追加・運用上の注意（例: 発注フローの安全化）などが必要であればお知らせください。