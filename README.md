# KabuSys

日本株向けの自動売買プラットフォーム基盤ライブラリ（KabuSys）。  
データ取得・ストレージ（DuckDB）・監査ログ等の共通基盤を提供し、戦略層／実行層の実装を支援します。

現在のバージョン: 0.1.0

---

## 概要

KabuSys は以下の要件を満たすことを目指した内部ライブラリです。

- J-Quants API から市場データ（株価日足・財務指標・マーケットカレンダー等）を取得
- 取得データを DuckDB に保存（Raw / Processed / Feature / Execution 層のスキーマ定義）
- 監査ログ（シグナル → 発注 → 約定のトレース）を専用テーブルに保存
- 環境変数（.env）管理とアプリ設定の集中管理
- API レート制限・リトライ・トークン自動更新などの堅牢な HTTP クライアント設計

設計上の主なポイント：
- J-Quants API のレート制限（120 req/min）を順守する RateLimiter を実装
- 408/429/5xx 等に対する指数バックオフ・最大リトライ（3 回）
- 401 を検出した場合はリフレッシュトークンで id_token を自動更新して一回のみリトライ
- データ取得時点（fetched_at）を UTC で保存し Look-ahead Bias を抑止
- DuckDB への保存は ON CONFLICT DO UPDATE により冪等化

---

## 機能一覧

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルートから自動読み込み（.git または pyproject.toml を基準）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_ENV（development / paper_trading / live） / LOG_LEVEL の検証
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - ページネーション対応
  - レート制限、リトライ、トークンキャッシュを備えた堅牢な実装
  - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を用意
  - init_schema(db_path) により DB を初期化（テーブル／インデックス作成、親ディレクトリ自動作成）
  - get_connection(db_path) で既存 DB へ接続

- 監査ログ（src/kabusys/data/audit.py）
  - signal_events, order_requests, executions テーブルを生成
  - init_audit_schema(conn) / init_audit_db(db_path) を提供（すべての TIMESTAMP は UTC）

- パッケージ構成（strategy / execution / monitoring は拡張用のパッケージとして用意）

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部構文を利用）
- pip

推奨: 仮想環境を利用すること。

1. リポジトリをクローン / 作業ディレクトリへ移動
   - プロジェクトルートには .git または pyproject.toml があることを想定（自動 .env 読み込み用）
2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリのインストール
   - 本リポジトリに requirements.txt が無い場合、必要最低限は duckdb
   - pip install duckdb
   - （パッケージ配布がある場合）pip install -e . など
4. 環境変数設定
   - プロジェクトルートに .env または .env.local を作成（下記の .env.example 参照）
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. データベース初期化（例は後述）

.env 例（.env.example）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabu API（kabuステーション）※必要であれば
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack（通知用）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（省略時はデフォルト）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development  # or paper_trading or live
LOG_LEVEL=INFO
```

必須環境変数（Settings が require するもの）：
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

（テストやローカル実行の際は .env に最低限これらを設定してください）

---

## 使い方（基本的な例）

以下は Python 上での代表的な操作例です。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path はデフォルトで "data/kabusys.duckdb"
conn = schema.init_schema(settings.duckdb_path)
```

- J-Quants から日足データを取得して保存
```python
from datetime import date
from kabusys.data import jquants_client
from kabusys.data import schema
from kabusys.config import settings

# DB 接続（初回は init_schema、以降は get_connection でも可）
conn = schema.get_connection(settings.duckdb_path)

# 例: 銘柄コード 7203（トヨタ）を 2023 年のデータで取得
records = jquants_client.fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))

# DuckDB の raw_prices に保存（冪等）
saved = jquants_client.save_daily_quotes(conn, records)
print(f"保存件数: {saved}")
```

- id_token の取得（必要時）
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使って POST で idToken を取得
```

- 監査ログテーブルの初期化
```python
from kabusys.data import audit
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
audit.init_audit_schema(conn)
```

注意点（実装上のふるまい）:
- fetch_* 系関数はページネーションに対応し、内部で id_token キャッシュを共有します。
- API 呼び出しは 120 req/min 制限に従いスロットリングされます。
- HTTP エラー（408/429/5xx）は最大 3 回の再試行（指数バックオフ）を行います。
- 401 Unauthorized を受けた場合は一度 id_token をリフレッシュして再試行します（無限再帰防止のため 1 回のみ）。
- save_* 系関数は ON CONFLICT DO UPDATE を使い冪等に動作します。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py               -- 環境・設定管理（.env 読み込み、Settings）
    - data/
      - __init__.py
      - jquants_client.py     -- J-Quants API クライアント + DuckDB 保存ユーティリティ
      - schema.py             -- DuckDB スキーマ定義・初期化
      - audit.py              -- 監査ログ（signal_events / order_requests / executions）
      - (others: raw/processed helpers)
    - strategy/
      - __init__.py           -- 戦略関連の拡張ポイント（現時点は空）
    - execution/
      - __init__.py           -- 発注・ブローカー連携の拡張ポイント（現時点は空）
    - monitoring/
      - __init__.py           -- 監視用モジュール（現時点は空）

その他:
- pyproject.toml (プロジェクトルートにある想定。存在すると .env 自動読み込みの基準になります)
- .git も同様にプロジェクトルート検出に使われます

---

## 開発メモ / 注意事項

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テストなどで自動読み込みをオフにしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のデフォルトパスは data/kabusys.duckdb。必要に応じて Settings.duckdb_path を上書きしてください。
- 監査ログは削除されないことを前提に設計されています（ON DELETE RESTRICT などを使用）。データの保全に注意してください。
- 複数プロセスで DB にアクセスする等の運用を行う場合は、DuckDB の使用制約やロック動作を確認してください。

---

## 貢献 / 拡張

- strategy/、execution/、monitoring/ パッケージに機能を追加して、戦略ロジック、注文送信ロジック、監視ロジックを実装してください。
- J-Quants 以外のデータ取得元やブローカー API を統合する場合は、既存の保存ユーティリティとスキーマに従って実装してください。
- バグ報告や PR は歓迎します。README に記載の環境・動作仕様に沿ってください。

---

必要であれば README を英語版やインストール用の手順（pyproject.toml / setup.cfg に合わせた pip install の例）、CI 用の初期化スクリプト例などに拡張できます。どの部分を詳細化したいか教えてください。