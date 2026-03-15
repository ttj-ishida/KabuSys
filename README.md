# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants）、DuckDB によるデータ永続化、スキーマ定義、監査ログ（オーダーから約定までのトレーサビリティ）など、自動売買システムの基盤機能を提供します。

バージョン: 0.1.0

---

## 主な特徴

- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - ページネーション対応
  - レート制限（120 req/min）遵守（内部 RateLimiter）
  - リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias に配慮
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution の多層スキーマを定義・初期化
  - 冪等なテーブル作成（IF NOT EXISTS）およびインデックス定義
  - init_schema() / get_connection() による簡単な初期化・接続
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 を UUID 連鎖でトレース可能にするテーブル群
  - 冪等キー（order_request_id）やステータス遷移を明示
  - init_audit_schema() / init_audit_db() を提供
- 環境設定管理
  - .env / .env.local / OS 環境変数から設定を読み込み
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）から行う
  - テスト等のために自動ロードを無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）

---

## 要求環境

- Python 3.10+
- 主要依存:
  - duckdb
- ネットワークアクセス（J-Quants API など）

（実際のプロジェクトでは requirements.txt や pyproject.toml を参照して依存関係をインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトします。

2. Python 仮想環境を作成して有効化します（推奨）。
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # macOS/Linux
     .venv\Scripts\activate     # Windows
     ```

3. 依存関係をインストールします（例: pip）。
   ```
   pip install duckdb
   # or
   pip install -e .
   ```

4. 環境変数を設定します。
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を作成してください。
   - 自動読み込みは既定で有効です。無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 必要な環境変数（Settings）

Settings クラスが参照する主な環境変数は以下です。必須のものは未設定時に例外が発生します。

- J-Quants / 認証
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- Slack（通知等）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス（任意）
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- システム設定（任意）
  - KABUSYS_ENV (development / paper_trading / live、デフォルト: development)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)
- 自動 .env ロード制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化

.env の書き方は一般的な KEY=VALUE、コメント行（#）や export プレフィックスにも対応しています。クォートやエスケープも処理します。

---

## 使い方（基本例）

以下はライブラリの主要な用途例です。

1. DuckDB スキーマの初期化（永続 DB ファイルを使用）

```python
from kabusys.data import schema
from kabusys.config import settings

# DUCKDB_PATH は settings.duckdb_path により取得（Path 型）
conn = schema.init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

2. J-Quants から日足を取得して保存する

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
n = save_daily_quotes(conn, records)
print(f"{n} 件を保存しました")
```

- fetch_* 関数はページネーションを自動処理します。
- save_* 関数は DuckDB 側で ON CONFLICT DO UPDATE を使い冪等に保存します。
- get_id_token() は内部で settings.jquants_refresh_token を使ってトークンを発行します。401 が返った場合、1 回リフレッシュして再試行します。

3. 監査ログ（Order/Execution）の初期化

- 既存接続に監査テーブルを追加する場合:

```python
from kabusys.data.audit import init_audit_schema
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
init_audit_schema(conn)
```

- 監査専用 DB を作る場合:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

---

## ディレクトリ構成（主なファイル）

以下はパッケージ内の主なモジュールと役割の一覧です（省略記載あり）。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 定義
    - 自動 .env ロード（.env → .env.local、OS 環境変数保護）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
    - schema.py
      - DuckDB スキーマ定義（Raw / Processed / Feature / Execution）
      - init_schema(db_path) / get_connection(db_path)
    - audit.py
      - 監査ログ用スキーマ（signal_events / order_requests / executions）
      - init_audit_schema(conn) / init_audit_db(db_path)
    - (その他) audit/schema など
  - strategy/
    - __init__.py
    - （戦略ロジックを配置する想定）
  - execution/
    - __init__.py
    - （発注・ブローカー連携を配置する想定）
  - monitoring/
    - __init__.py
    - （監視・メトリクス保存等を配置する想定）

---

## 設計上のポイント / 注意事項

- 全てのタイムスタンプは UTC を想定しています。監査テーブル初期化時に `SET TimeZone='UTC'` を実行します。
- J-Quants API のレート制限を厳守するため、モジュール内で固定間隔スロットリングを実装しています（120 req/min）。
- 保存処理は冪等を意識しており、重複レコードは更新で上書きされます（ON CONFLICT）。
- .env の自動読み込みはプロジェクトルート検出に .git または pyproject.toml を利用します。配布後やテスト環境で動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。

---

## 貢献 / 拡張ポイント

- strategy パッケージにアルゴリズムや特徴量生成ロジック（features テーブルへの投入）を実装
- execution パッケージにブローカーラッパ（kabuステーション API など）を実装して orders/trades テーブルへの反映
- monitoring パッケージで Slack 通知や監視ダッシュボードの連携

---

必要であれば README を拡張して、実際のインストールコマンド（pyproject.toml に基づく）や例の .env テンプレート、より詳細な API 使用例（ページネーションやエラーハンドリングの挙動）を追加します。どの情報を優先して追加しますか？