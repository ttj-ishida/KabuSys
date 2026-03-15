# KabuSys

日本株向け自動売買システムのコアライブラリ（プロトタイプ）。  
データ取得、データベーススキーマ、監査ログ、および環境設定を含む基盤機能を提供します。

## 目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 使い方（簡単な例）
- 環境変数
- ディレクトリ構成（ファイル一覧）
- 補足（設計上の注意点）

---

## プロジェクト概要
KabuSys は、日本株自動売買システムの基盤コンポーネント群です。  
主に以下を提供します。

- J-Quants API クライアント（株価・財務・マーケットカレンダーの取得）
- DuckDB を使った三層データスキーマ（Raw / Processed / Feature）および Execution 層
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 環境変数／.env の自動読み込みと設定管理

設計上は、レート制限遵守、リトライ、トークン自動リフレッシュ、UTC タイムスタンプ保存、冪等性（ON CONFLICT）を重視しています。

---

## 主な機能
- data.jquants_client
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - API レート制御（120 req/min の固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への保存関数（冪等な INSERT ... ON CONFLICT）
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）
  - 初期化関数 init_schema(db_path)
- data.audit
  - 監査ログ用 DDL と初期化（init_audit_schema / init_audit_db）
  - シグナルから約定までの完全トレーサビリティを確保するテーブル群
- config.Settings
  - .env（.env.local 含む）や OS 環境変数から設定を読み込み
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行う
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能

---

## 前提条件
- Python 3.10+
  - 型ヒントで PEP 604（X | None）を利用しているため 3.10 以上を想定
- 推奨パッケージ
  - duckdb
- ネットワーク接続（J-Quants API へアクセスする場合）
- （任意）kabuステーション等の実運用 API

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージのインストール（例）
   - パッケージ配布用の setup がある場合:
     ```
     pip install -e .
     ```
   - 最低限 duckdb は必要:
     ```
     pip install duckdb
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を作成することで自動読み込みされます。
   - サンプル（必要なキーの一覧は下記「環境変数」参照）。

5. データベース初期化（DuckDB）
   - python REPL やスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     # settings.duckdb_path は .env またはデフォルトを参照
     conn = init_schema(settings.duckdb_path)
     ```
   - 監査ログ用テーブルを追加するには:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```
   - 監査専用 DB を作る場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn_audit = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（簡単な例）
以下は J-Quants から株価日足を取得して DuckDB に保存する最小例です。

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings

# DB 初期化 / 接続
conn = init_schema(settings.duckdb_path)

# 銘柄コードを指定して取得（例: '7203'）
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# 保存（冪等）
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

財務データやマーケットカレンダーも同様の関数が用意されています：
- fetch_financial_statements / save_financial_statements
- fetch_market_calendar / save_market_calendar

トークン取得（明示的に行いたい場合）:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

注意:
- fetch_* 関数は内部でトークンキャッシュ、レート制御、リトライを行います。
- save_* 関数はレコードの PK 欠損をスキップし、ON CONFLICT DO UPDATE による上書きを行います。

---

## 環境変数（主なもの）
プロジェクトは .env（.env.local）や OS 環境変数から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行われます。自動ロードを止めるには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要なキー:
- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, allowed: development / paper_trading / live, デフォルト: development)
- LOG_LEVEL (任意, DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト: INFO)

.env の解釈ルールやコメント処理は config モジュールに実装されています（クォートや export プレフィックス対応、行内コメントの扱いなど）。

---

## ディレクトリ構成（主要ファイル）
（この README に含まれるコードベースに基づく抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得 / 保存 / レート制御 / リトライ）
    - schema.py             — DuckDB スキーマ定義と初期化
    - audit.py              — 監査ログ（signal / order_request / executions）
    - audit (他ファイル)
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

各ファイルの用途の一言:
- config.py: .env の自動読み込みロジック、Settings クラス（プロパティで必須変数の検証）
- jquants_client.py: API 呼び出し、レート制御、トークン管理、DuckDB への保存ユーティリティ
- schema.py: Raw / Processed / Feature / Execution 層の DDL と初期化関数
- audit.py: 監査ログ用の DDL とインデックス、初期化関数

---

## 補足（設計上の注意点）
- 型や文法から Python 3.10 以上を想定しています。
- J-Quants のレート制限（120 req/min）に合わせてクライアント側で固定間隔のスロットリングを実装しています。並列で多数のスレッド／プロセスから同時に呼ぶと制限に抵触する可能性があるため、実運用ではプロセス設計を注意してください。
- DuckDB の INSERT は ON CONFLICT を使って冪等に保存しますが、上位設計（処理フロー）でも重複処理やトランザクションを考慮してください。
- 監査ログは削除しない前提（FK は ON DELETE RESTRICT）です。updated_at はアプリ側で current_timestamp をセットする運用となります。
- すべてのタイムスタンプは UTC が推奨されています（audit.init_audit_schema は接続に対して SET TimeZone='UTC' を実行します）。

---

必要に応じて README を拡張して、セットアップスクリプト、CI 設定、例外ハンドリングや運用手順（ログの出力先、バックアップ、マイグレーション）を追加してください。質問や追加したいセクションがあれば教えてください。