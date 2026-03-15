# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。  
データ取得、データベーススキーマ管理、監査ログ、環境設定ユーティリティなど、自動売買システムの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、J-Quants API や kabu ステーション等からのデータ取得と、DuckDB を用いたローカルデータ保存・スキーマ管理、発注フローを追跡する監査ログ機能などを備えた日本株自動売買プラットフォームの基盤ライブラリです。  
主に以下を提供します。

- J-Quants API クライアント（株価・財務・マーケットカレンダー等の取得、ページネーション対応）
- DuckDB ベースのスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ（signal → order_request → execution の追跡用テーブル群）
- 環境変数/.env 読み込みユーティリティ（自動ロード、必須チェック）
- 発注・実行モジュールの雛形（パッケージ構成上のプレースホルダ）

設計上のポイント:
- J-Quants API のレート制限（120 req/min）を尊重するレートリミッタ
- リトライ（指数バックオフ、最大 3 回。401 は自動トークンリフレッシュで再試行）
- データの fetched_at を UTC で記録し Look-ahead Bias を防止
- DuckDB への INSERT は冪等（ON CONFLICT ... DO UPDATE）で重複を排除

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを探索）
  - 必須環境変数の取り扱い（未設定時はエラー）
- データ取得（J-Quants）
  - 日次株価（OHLCV）
  - 財務（四半期 BS/PL）
  - JPX マーケットカレンダー
  - ページネーション、認証トークン管理、レート制御、リトライ実装
- データベース（DuckDB）
  - Raw、Processed、Feature、Execution 層のテーブル定義
  - インデックス定義
  - スキーマ初期化（init_schema）
- 監査ログ（Audit）
  - signal_events / order_requests / executions を含む監査スキーマ
  - 監査用 DB 初期化（init_audit_db / init_audit_schema）
  - UTC タイムスタンプの保存方針
- ユーティリティ
  - 型安全の数値変換、冪等保存関数（save_*）

---

## 要件

- Python 3.10 以上（型注釈で | 演算子を使用）
- pip パッケージ: duckdb

（標準ライブラリのみで動く部分もありますが、DuckDB を利用する機能は duckdb が必要です）

---

## セットアップ手順

1. リポジトリをクローン（またはプロジェクトを取得）
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存ライブラリをインストール
   ```
   pip install duckdb
   # （ローカル editable インストールが必要なら）
   pip install -e .
   ```

4. 環境変数を準備
   - プロジェクトルートに `.env` と（機密情報用に）`.env.local` を置くと、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数の例は後述します。

---

## 環境変数（主なキー）

以下はコード内で参照される環境変数の一覧と説明です。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token() により ID トークンを取得します。

- KABU_API_PASSWORD (必須)
  - kabu ステーション API 用パスワード。

- KABU_API_BASE_URL (任意)
  - kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン。

- SLACK_CHANNEL_ID (必須)
  - Slack のチャンネル ID。

- DUCKDB_PATH (任意)
  - DuckDB ファイルパスのデフォルト。デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)
  - 監視・モニタリング用 SQLite のパス。デフォルト: data/monitoring.db

- KABUSYS_ENV (任意)
  - 実行環境。development / paper_trading / live のいずれか。デフォルト: development

- LOG_LEVEL (任意)
  - ログレベル。DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO

- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 何か値が設定されていると .env 自動読み込みを無効化します（テスト用など）。

.env の例（.env.example を参考に作成してください）:
```
JQUANTS_REFRESH_TOKEN="your-refresh-token"
KABU_API_PASSWORD="your-password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## クイックスタート（サンプル使い方）

以下は J-Quants から日次株価を取得して DuckDB に保存する簡単な例です。

```python
from datetime import date
import kabusys.data.jquants_client as jqc
from kabusys.data import schema
from kabusys.config import settings

# 1) DuckDB を初期化して接続を取得（ファイルを指定）
conn = schema.init_schema(settings.duckdb_path)

# 2) J-Quants から日次株価を取得（コード・期間を指定）
records = jqc.fetch_daily_quotes(code="7203", date_from=date(2023, 1, 1), date_to=date(2023, 12, 31))

# 3) 取得データを raw_prices テーブルに保存（冪等）
n = jqc.save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

監査ログ用の DB を別途作る場合（監査専用 DB）:

```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/audit.duckdb")
# audit_conn は executions / order_requests 等のテーブルを含む
```

トークン取得（手動）:

```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を使って ID トークンを取得
```

注意点:
- fetch_* 関数はページネーション対応で全件を取得します。
- 内部でレートリミッタ・リトライ・トークン自動更新を行います。
- save_* 関数は ON CONFLICT ... DO UPDATE で冪等に保存します。

---

## ディレクトリ構成

リポジトリの主要ファイル/ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数管理・Settings クラス（自動 .env ロード含む）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得／保存ロジック）
    - schema.py              — DuckDB スキーマ定義 & init_schema / get_connection
    - audit.py               — 監査ログ（signal_events, order_requests, executions）
    - audit のテーブル初期化ヘルパー（init_audit_db / init_audit_schema）
    - その他: audit 用ユーティリティ等
  - strategy/
    - __init__.py            — 戦略関連（プレースホルダ）
  - execution/
    - __init__.py            — 発注実行関連（プレースホルダ）
  - monitoring/
    - __init__.py            — モニタリング関連（プレースホルダ）

主要なモジュール機能:
- kabusys.config.settings — 環境設定プロパティ群
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化
- kabusys.data.jquants_client.fetch_* / save_* — データ取得・保存
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログ初期化

---

## 実運用上の注意

- KABUSYS_ENV を `live` にする前に十分な検証を行ってください（paper_trading / development を活用）。
- 発注・約定周りは監査ログで必ず追跡されるようにしてください（order_request_id を冪等キーとして扱うこと）。
- DuckDB ファイルのバックアップ・排他制御（複数プロセスからのアクセス）については運用側で検討してください。
- J-Quants のレート制限・エラーコードポリシーに注意してください。内部でレート制御やリトライを実装していますが、運用時の同時実行数や別クライアントからのアクセスも考慮してください。

---

## 貢献・拡張

- strategy/、execution/、monitoring/ フォルダは拡張ポイントです。戦略ロジック、発注ハンドラ、モニタリングパイプラインを実装して連携してください。
- 新しいデータソースを追加する場合は data/ 以下にクライアント実装を追加し、schema.py に必要なテーブルを追加してください。

---

必要であれば、README に含める具体的な .env.example や、DuckDB のテーブル定義の要約、コード例の追加なども対応します。どの部分を詳しく書きたいか教えてください。