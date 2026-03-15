# KabuSys

日本株自動売買システムのコアライブラリ（ライブラリ部分の骨組み）。  
本リポジトリはデータ取得・永続化・スキーマ定義・監査ログなど、アルゴリズム取引システムの基盤を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から市場データ（株価日足、財務データ、JPX カレンダー）を安全に取得するクライアント
- DuckDB を用いた三層（Raw / Processed / Feature）データスキーマの定義と初期化
- 発注〜約定の監査ログ（トレーサビリティ）テーブルの初期化
- 環境変数による設定管理と自動 .env ロード（プロジェクトルート基準）
- （プレースホルダ）戦略・発注・監視用のパッケージ構成

設計上の要点：
- API レート制限・リトライ・トークン自動リフレッシュ（J-Quants クライアント）
- DuckDB への冪等的保存（ON CONFLICT DO UPDATE を活用）
- 監査ログは削除せず、UUID 連鎖でシグナル→発注→約定を完全にトレース可能

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）
  - 実行環境フラグ（development / paper_trading / live）とログレベル検証

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期）、マーケットカレンダーの取得
  - 固定間隔のレートリミッタ（120 req/min）
  - 指数バックオフによるリトライ（408/429/5xx 等）、401 受信時の自動トークンリフレッシュ
  - fetched_at による取得時刻の UTC 記録（Look-ahead Bias 対策）
  - DuckDB に対する冪等保存関数（raw_prices / raw_financials / market_calendar）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema() による DB 初期化（テーブル・インデックス作成）
  - get_connection() で既存 DB に接続

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL と初期化関数
  - init_audit_schema() / init_audit_db() による監査テーブルの追加・初期化
  - UTC 保存、冪等キー（order_request_id）による二重発注防止

- パッケージ構成（プレースホルダ）：strategy / execution / monitoring パッケージ

---

## セットアップ手順

前提:
- Python 3.9+（コード中で typing のオプション型注釈を利用）
- duckdb 等の依存パッケージ（必要に応じて pyproject.toml / requirements.txt を参照）

1. リポジトリをクローンして作業ディレクトリへ移動

   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成して有効化（任意）

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール

   - 最低限必要: duckdb
   - 例:
       pip install duckdb

   もしプロジェクトがパッケージ化されている場合:
       pip install -e .

4. 環境変数の設定（.env 作成）

   プロジェクトルートに .env（および任意で .env.local）を置くと、kabusys.config が自動で読み込みます（CWD ではなくパッケージファイル位置からプロジェクトルートを探索）。

   必須の環境変数（主要なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   任意:
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite モニタリング DB（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する場合は `1` をセット

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN="your_refresh_token_here"
   KABU_API_PASSWORD="your_kabu_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   DUCKDB_PATH="data/kabusys.duckdb"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DB 初期化

   Python REPL またはスクリプトで DuckDB スキーマを作成します。

   例:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

   監査ログのみ別 DB で管理する場合:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/kabusys_audit.duckdb")
   conn.close()
   ```

---

## 使い方（基本例）

以下はライブラリ機能の代表的な利用例です。

- 設定値の参照

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.env)
print(settings.is_live)
```

- J-Quants から日足を取得して DuckDB に保存

```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# 指定銘柄・期間の取得
records = fetch_daily_quotes(code="7203", date_from=date(2024, 1, 1), date_to=date(2024, 1, 31))

# raw_prices テーブルへ保存（冪等）
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
conn.close()
```

- 財務データやマーケットカレンダーも同様の API / 保存関数が用意されています:
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar

- ID トークン取得（必要に応じて直接呼ぶ）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

- 監査ログの初期化（既存の DuckDB 接続へ追加）

```python
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
conn.close()
```

---

## ディレクトリ構成

主要ファイル・モジュールの構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理（.env 自動ロード等）
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（取得・保存ロジック）
      - schema.py              # DuckDB スキーマ定義と初期化
      - audit.py               # 監査ログ（signal_events, order_requests, executions）
      - audit...               # （監査用ユーティリティ）
    - strategy/
      - __init__.py            # 戦略モジュール（実装はここに置く）
    - execution/
      - __init__.py            # 発注/約定処理（証券会社接続等）
    - monitoring/
      - __init__.py            # 監視 / アラート（Slack 連携など）

ドキュメント的に重要なモジュール:
- kabusys.config: .env 自動ロード、必須チェック、環境フラグ
- kabusys.data.jquants_client: API 呼び出し、レート制限、保存関数
- kabusys.data.schema: DuckDB の DDL / インデックス、init_schema
- kabusys.data.audit: 監査ログの DDL / init_audit_schema

---

## 注意事項・トラブルシューティング

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に行われます。テストなどで自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants の API 制限（120 req/min）を超えないよう内部でスロットリングしています。大量取得時は実行時間に注意してください。
- DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）は親ディレクトリが存在しなければ自動作成されますが、ファイルシステムの権限に注意してください。
- ネットワークエラーや一時的な HTTP 429/5xx は内部でリトライしますが、最終的に失敗すると例外が発生します。ログを参照してリトライ戦略を調整してください。

---

## 今後の拡張ポイント（参考）

- strategy パッケージに戦略の実装（シグナル生成、リスク管理）
- execution パッケージに broker アダプタ（kabu ステーション等）の実装
- monitoring に Slack 通知やメトリクス収集の組み込み
- CI テスト、型チェック、パッケージ配布設定（pyproject.toml の整備）

---

問題報告・貢献についてはリポジトリの Issue / PR をご利用ください。