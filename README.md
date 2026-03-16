# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
J-Quants API などから市場データを取得して DuckDB に保存、品質チェックを実施し、戦略→発注→監査に至るデータ基盤とパイプラインの基礎を提供します。

バージョン: 0.1.0

## 主な特徴
- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）に合わせたスロットリング
  - リトライ（指数バックオフ、最大 3 回）・401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）の保存で Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ定義・初期化モジュール
  - Raw / Processed / Feature / Execution 層を想定したテーブル群
  - インデックスと外部キーの設計を含む DDL を提供
- ETL パイプライン
  - 差分更新（最終取得日を元に未取得分のみ取得）
  - backfill による後出し修正吸収
  - 市場カレンダーの先読み
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- 監査（Audit）スキーマ
  - シグナル→発注→約定のトレーサビリティを UUID 連鎖で管理
  - 発注の冪等キー（order_request_id）などを取り扱う
- 設定/環境変数管理
  - .env/.env.local から自動読み込み（プロジェクトルート検出）
  - 必須値は Settings クラスから取得（未設定時は例外）

## 機能一覧（概要）
- kabusys.config
  - 環境変数の自動読み込み（.env / .env.local）と Settings API
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...) を含む差分 ETL 実装
- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(db_path)

（strategy / execution / monitoring パッケージは骨格モジュールとして用意されています）

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型記法（|）と __future__ 注釈を使用）
- pip が使用可能

1. リポジトリをクローン／取得
   - 任意の方法でソースを取得してください（例: git clone）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリのインストール
   - このコードベースで外部に依存する主要パッケージは DuckDB です（pip install duckdb）
   - 例:
     - pip install duckdb

   ※ 実運用で Slack 連携や kabu API を使う場合は、それらの SDK や追加パッケージを別途追加してください。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を配置すると自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 必要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
   - KABUSYS_ENV (任意, 値: development | paper_trading | live, デフォルト: development)
   - LOG_LEVEL (任意, DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## 基本的な使い方（サンプル）

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を作成・初期化
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

2) 監査ログスキーマの初期化（別途）
```python
from kabusys.data import audit

# 既存の conn に監査テーブルを追加
audit.init_audit_schema(conn)

# 監査専用 DB を初期化する場合
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema を実行済みの前提
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4) 個別ジョブの実行（例: 株価だけ）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
conn = schema.get_connection("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

5) J-Quants のトークン取得（テストや直接呼び出し）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

6) 品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

## 環境変数の自動読み込みについて
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に `.env` と `.env.local` を探します。
- 読み込み順と優先度:
  - OS 環境変数（既存） > .env.local（override=True） > .env（override=False）
- `.env.local` は .env 上の値を上書きする用途（ローカル開発設定）に使います。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

パーサーの挙動（簡単な補足）
- export KEY=val 形式に対応
- 値のクォートやエスケープを処理
- # は行頭コメントおよびスペース直前の # をコメントとみなす等

## ログ・実行モード
- 環境変数 KABUSYS_ENV により実行モードを切替:
  - development, paper_trading, live
- LOG_LEVEL 環境変数でログレベルを設定（DEBUG/INFO/...）

## ディレクトリ構成

リポジトリ内の主要ファイル（この README 作成時点）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定管理
  - execution/                      — 発注/執行関連（骨格）
    - __init__.py
  - strategy/                       — 戦略ロジック（骨格）
    - __init__.py
  - monitoring/                     — 監視・メトリクス（骨格）
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント・保存ロジック
    - schema.py                     — DuckDB スキーマ定義・初期化
    - pipeline.py                   — ETL パイプライン（差分更新・品質チェック）
    - audit.py                      — 監査ログ（signal / order_request / executions）
    - quality.py                    — データ品質チェック

（上記以外に strategy / execution / monitoring の具体実装を追加していく想定です）

## 開発メモ / 注意点
- DuckDB を利用しており、ON CONFLICT を使った冪等性を重視しています。既存 DB に対しては init_schema を一度だけ実行してください（冪等であるため何度実行しても安全です）。
- J-Quants API レート制限を守るため内部で固定間隔レートリミッタを実装しています。
- ETL は Fail-Fast ではなく、各ステップでエラーを記録しつつ可能な処理は継続します（結果オブジェクトでエラー／品質問題を確認可能）。
- 本ライブラリはインフラ（証券会社 API、実行エンジン、Slack 通知等）と組み合わせて使う想定です。実際の発注・資金管理ロジックは execution/ 下の実装に依存します。

---

追加で README に記載したい内容（例: ライセンス、貢献方法、CI 設定、依存バージョン固定ファイル等）があれば教えてください。必要に応じて README を拡張します。