# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）です。データ取得、永続化（DuckDB）、監査ログ、発注/戦略のためのスキーマを備え、J-Quants／kabuステーション等と連携することを想定しています。

注意: 本リポジトリはライブラリ本体の一部（データ取得・スキーマ定義・設定管理など）を含んでいます。実際の運用での発注機能や運用コードは別途実装する想定です。

---

## 主な特徴

- 環境変数ベースの設定管理（.env の自動読み込み機能付き）
  - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動ロード
  - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得機能
  - レート制限（120 req/min）を厳守する組み込み RateLimiter
  - リトライ（指数バックオフ、最大3回）、401 時の自動トークンリフレッシュ対応
  - 取得日時（fetched_at）を UTC で記録して Look-ahead Bias に対応
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層を想定したテーブル群（冪等な作成）
  - よく使うクエリ向けのインデックス定義
- 監査（Audit）テーブル
  - シグナル → 発注要求 → 約定というトレースチェーンを保持
  - 冪等キー（order_request_id / broker_execution_id 等）やステータス管理を備える

---

## 機能一覧（抜粋）

- kabusys.config
  - Settings クラス: 環境変数から各種設定を取得（必須キーが未設定だと例外）
  - 自動 .env ロード（優先順位: OS 環境 > .env > .env.local）
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- kabusys.data.schema
  - init_schema(db_path)  — DuckDB のスキーマ初期化と接続取得
  - get_connection(db_path) — 既存 DB への接続
- kabusys.data.audit
  - init_audit_schema(conn) — 監査ログテーブルの追加初期化
  - init_audit_db(db_path) — 監査専用 DB の初期化

---

## セットアップ手順

前提: Python 3.9+（タイプヒントに | を使用しているため。必要に応じて読み替えてください）

1. リポジトリをクローンして仮想環境を作る（例: venv）
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要なパッケージをインストール
   - 本コードで利用されている主要パッケージは duckdb です。その他は標準ライブラリ中心です。
   ```bash
   pip install duckdb
   # 開発時はエディタ補完などのためにパッケージをまとめて入れることがあるかもしれません
   # pip install -e .
   ```

3. 環境変数を準備
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を置くと自動で読み込まれます。
   - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（ライブラリ内で必須としているもの）
- JQUANTS_REFRESH_TOKEN（J-Quants のリフレッシュトークン）
- KABU_API_PASSWORD（kabuステーション API 用パスワード）
- SLACK_BOT_TOKEN（Slack 通知用トークン）
- SLACK_CHANNEL_ID（通知先チャンネル ID）

その他（任意/デフォルトあり）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（有効値: development / paper_trading / live、デフォルト: development）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

.env ファイルの例（.env.example を参考に作成してください）
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=xxxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

- DuckDB スキーマ初期化と接続取得
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリがなければ自動作成）
conn = init_schema("data/kabusys.duckdb")
```

- J-Quants から日足を取得して保存する例
```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# 例: 銘柄コード 7203（トヨタ）の 2022 年の日足を取得・保存
records = fetch_daily_quotes(code="7203", date_from=date(2022, 1, 1), date_to=date(2022, 12, 31))
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

- ID トークンを直接取得する（通常は fetch 系が自動でトークン管理します）
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使用
print(id_token)
```

- 監査ログ（Audit）テーブルの初期化
```python
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)  # 監査テーブル群を追加
```

注意点:
- J-Quants クライアントは内部でレート制限（120 req/min）を守るように実装されています。
- ネットワークエラーや 5xx／429 等は最大3回までリトライされます。401 はトークンをリフレッシュして 1 回リトライします。
- DuckDB 側への保存は冪等（ON CONFLICT DO UPDATE）になっています。重複挿入によるデータ上書きが安全に行われます。

---

## ディレクトリ構成（主なファイル）

以下はこのリポジトリ内の主要ファイルとモジュール構成です（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py       — J-Quants API クライアント（取得 + DuckDB 保存）
      - schema.py               — DuckDB スキーマ定義・初期化
      - audit.py                — 監査ログ（signal / order_request / executions）
      - audit.py
      - monitoring/ (モジュール用の空 __init__ 等)
    - strategy/                  — 戦略モジュールのエントリポイント（空の __init__）
    - execution/                 — 発注/実行モジュールのエントリポイント（空の __init__）
    - monitoring/                — 監視用エントリポイント（空の __init__）

（上記はコードベースの現状ファイルに基づく一覧です）

---

## 設計上の注意・ポリシー

- すべてのタイムスタンプは UTC を基本に扱う設計思想（audit.init_audit_schema は TimeZone='UTC' をセットします）。
- 監査ログは削除しない前提（FK は ON DELETE RESTRICT）。操作履歴を保持してトレーサビリティを確保します。
- データ取得時に fetched_at を保存して「いつデータを取得したか」を記録し、将来的な解析やデバッグでの Look-ahead Bias を防止します。
- 発注や監査に関わる ID（signal_id, order_request_id, broker_order_id, broker_execution_id 等）は冪等設計に配慮しています。

---

## 参考 / トラブルシュート

- .env の自動読み込みが期待通りに動作しない場合:
  - プロジェクトルートが .git または pyproject.toml を起点として検出されます。適切なファイルがあるか確認してください。
  - 自動読み込みを確認したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を空または未設定にしてください。逆に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の初期化でディレクトリがない場合は init_schema が自動で作成します。
- J-Quants の API レスポンスが JSON でない場合はデコードエラー（RuntimeError）が発生します。レスポンスの先頭 200 文字をログ/例外メッセージに含めて通知します。

---

この README は現在のコードベース（config, data.jquants_client, data.schema, data.audit を中心）に基づいて作成しています。運用や追加モジュール（strategy / execution / monitoring）の実装に応じて使い方やセットアップ手順は拡張してください。