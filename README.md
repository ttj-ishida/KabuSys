# KabuSys

日本株自動売買システムのコアライブラリ（データ取得・スキーマ・監査ログ・設定管理など）

このリポジトリは、J-Quants API や kabuステーション 等からデータを取得し、DuckDB に永続化して戦略／実行レイヤで利用できる基盤モジュール群を提供します。設計上、レート制限・リトライ・トレーサビリティ（監査ログ）・冪等性を重視しています。

## 主な機能

- 環境変数/設定管理
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得（未設定時は例外）
  - KABUSYS_ENV / LOG_LEVEL の検証
- J-Quants API クライアント（data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - API レート制限遵守（120 req/min 固定間隔スロットリング）
  - ページネーション対応
  - リトライ（指数バックオフ、最大 3 回）、HTTP 429 の Retry-After 尊重
  - 401 受信時はリフレッシュトークンで自動的にトークン更新して1回リトライ
  - 取得時刻（fetched_at）を UTC で記録（Look-ahead bias 対策）
  - DuckDB への保存は ON CONFLICT DO UPDATE により冪等
- DuckDB スキーマ定義 / 初期化（data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス、外部キー、制約を含む DDL を提供
  - init_schema() により DB を初期化
- 監査ログ（data/audit.py）
  - signal_events / order_requests / executions を含む監査テーブル
  - order_request_id による冪等（再送時に重複防止）
  - すべての TIMESTAMP を UTC で保存（init で TimeZone を設定）
  - init_audit_schema() / init_audit_db() を提供
- パッケージ構成上、strategy / execution / monitoring のプレースホルダモジュールを用意

## 必要条件

- Python 3.9+
- 主要依存（例）
  - duckdb
- ネットワークアクセス（J-Quants API など）

（実際の requirements はプロジェクトの packaging 側で管理してください）

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb

   （プロジェクトの requirements.txt / pyproject.toml があればそれを使ってインストールしてください）

4. 環境変数の準備
   - プロジェクトルートに `.env`（もしくは `.env.local`）を作成します。自動読み込みはデフォルトで有効です。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

.env の例:
```
# 必須
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# 任意
KABUSYS_ENV=development          # development | paper_trading | live
LOG_LEVEL=INFO                   # DEBUG | INFO | WARNING | ERROR | CRITICAL
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABU_API_BASE_URL=http://localhost:18080/kabusapi
```

## 使い方（簡単な例）

- 設定の参照
```python
from kabusys.config import settings

print(settings.env)
print(settings.duckdb_path)
# 必須値はプロパティアクセス時に検証され、未設定なら ValueError が発生します
```

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイル DB を初期化して接続を返す
```

- J-Quants から日足を取得して保存する
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

# 全銘柄の過去日足を取得（ページネーション対応）
records = fetch_daily_quotes(date_from=None, date_to=None)

# raw_prices テーブルに保存（ON CONFLICT DO UPDATE で冪等）
n = save_daily_quotes(conn, records)
print("saved rows:", n)
```

- 監査テーブルを既存接続に追加
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
init_audit_schema(conn)  # audit テーブルを追加
```

- 監査専用 DB を作る
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意点:
- J-Quants API 呼び出しは内部でレート制御・リトライ・トークンリフレッシュを行うため、基本的に単純に呼び出して問題ありません。
- fetch_* 関数はページネーションを内部で扱い、結果を全件返します。大量データを扱う場合は注意してください（メモリ消費）。

## 環境変数（主要なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意／デフォルトあり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化

## 主要な設計上のポイント

- データの取得時刻（fetched_at）は UTC で記録し、Look-ahead bias のトレーサビリティを確保しています。
- DuckDB への挿入は冪等（ON CONFLICT DO UPDATE）なので、再取得やジョブの再実行でデータの二重挿入を防げます。
- 監査ログは消さない想定で、外部キーは ON DELETE RESTRICT を使うなどトレーサビリティを厳格にしています。
- J-Quants API クライアントはレート制限（120 req/min）を固定間隔で守る実装になっています。429/5xx/408 やネットワークエラーは指数バックオフでリトライします。

## ディレクトリ構成

（主なファイル/モジュール）
```
src/kabusys/
├─ __init__.py                 # パッケージ初期化、バージョン等
├─ config.py                   # 環境変数 / 設定管理（.env 自動読み込み等）
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py        # J-Quants API クライアント（取得/保存ロジック）
│  ├─ schema.py                # DuckDB スキーマ定義・初期化
│  └─ audit.py                 # 監査ログ（signal/order_request/execution）定義・初期化
├─ strategy/
│  └─ __init__.py              # 戦略関連（プレースホルダ）
├─ execution/
│  └─ __init__.py              # 実行関連（プレースホルダ）
└─ monitoring/
   └─ __init__.py              # 監視用モジュール（プレースホルダ）
```

## 開発・運用上のヒント

- 自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml から探索して行います。テスト環境などで読み込みを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のファイルパスの親ディレクトリが存在しない場合は init_schema()/init_audit_db() が自動的に作成します。
- 監査ログでは UTC タイムゾーンを前提に保存しています。ローカルタイムでの表示が必要な場合はアプリ側で変換してください。
- ログレベルや実行環境（paper_trading / live）によって挙動を切り替えるプロパティが settings に用意されています。

---

この README はコードベースの概要説明と基本的な使い方を示すことを目的としています。戦略実装やブローカ接続（kabu API を使った注文送信等）は別モジュール／アプリケーション側で実装してください。必要であれば README の補足（ブローカー連携、CI 設定、例外ハンドリング方針など）を追加します。