# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリ群です。データ取得、スキーマ定義、監査ログ、戦略・実行・モニタリングの骨組みを提供します。本リポジトリはライブラリ層であり、上位でワークフローやバッチ/常駐プロセスを組むことで自動売買システムを構築できます。

主な特徴
- J-Quants API クライアント（日足・財務・マーケットカレンダー取得）
  - レートリミット（120 req/min）遵守
  - 再試行（指数バックオフ、最大 3 回、408/429/5xx 対象）
  - 401 受信時の自動トークンリフレッシュ（1 回）
  - 取得時刻（fetched_at）を UTC に記録して Look-ahead Bias を抑制
  - DuckDB への冪等的保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ定義（Raw / Processed / Feature / Execution レイヤー）
  - prices, features, ai_scores, orders, trades, positions など
  - インデックスを想定した DDL を含む
- 監査ログ（audit）
  - signal → order_request → execution のトレースを UUID 連鎖で保証
  - order_request_id を冪等キーとして二重発注防止
  - すべての TIMESTAMP は UTC を想定
- 環境変数管理（.env 自動ロード、Settings クラス）

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡単なコード例）
- 環境変数（.env）と自動ロード動作
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株自動売買のコア機能をライブラリとして提供します。データ取り込み（J-Quants）、ローカル DB（DuckDB）での保存・スキーマ管理、監査ログ、戦略／実行／モニタリングのための土台を含みます。各コンポーネントは独立して利用でき、既存システムへの組み込みやプロトタイプ実装に適しています。

---

## 機能一覧

- 環境設定読み込み（.env / OS 環境変数、Settings クラス）
- J-Quants API クライアント
  - get_id_token（リフレッシュトークンから idToken を取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - rate limiting、リトライ、トークン自動リフレッシュ
  - fetch の結果を DuckDB に保存する save_* 関数
- DuckDB スキーマ管理
  - init_schema(db_path) による DB 初期化（テーブル / インデックス作成）
  - get_connection(db_path) で既存 DB へ接続
- 監査ログ（audit）
  - init_audit_schema(conn) で既存 DuckDB 接続へ監査テーブル追加
  - init_audit_db(db_path) 単体で監査専用 DB を初期化
- 基礎的なパッケージ構成（strategy, execution, monitoring のプレースホルダ）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の union 演算子 `|` を使用）
- pip

1. リポジトリをクローン（またはソースを取得）
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (UNIX) / .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - 主要依存: duckdb（その他は標準ライブラリで実装）
   - pip install duckdb
   - （開発用）pip install -e .
     - setup.py / pyproject.toml が用意されている場合は上記でローカルインストール可能
4. 環境変数を準備（下記「環境変数」参照）。プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効にすることも可能）。

---

## 使い方（簡単なコード例）

以下は J-Quants から日足を取得して DuckDB に保存する例です。

例: データ取得→保存
```python
from pathlib import Path
import duckdb
from kabusys.data.jquants_client import (
    fetch_daily_quotes,
    save_daily_quotes,
)
from kabusys.data.schema import init_schema

# DuckDB の初期化（ファイルを指定）
db_path = Path("data/kabusys.duckdb")
conn = init_schema(db_path)  # テーブルが存在しない場合は作成する

# 銘柄コード指定や日付範囲指定も可能
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# 保存（冪等）
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

例: ID トークンを直接取得する
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
print(token)
```

監査ログの初期化（既存接続へ追加）
```python
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)  # 監査テーブルを追加
```

監査専用 DB を作る場合:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
```

ログ出力や例外は標準の logging を使っているため、アプリ側で logging.basicConfig() 等を設定して運用してください。

---

## 環境変数（.env）と自動ロード動作

設定は環境変数から読み取られ、Settings クラス経由で利用します。プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に `.env` → `.env.local` の順で自動ロードします（.env.local は上書き、OS の環境変数は保護されます）。

自動ロードを無効化するには環境変数を設定:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主に利用される環境変数
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite 等（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

サンプル .env
```
# .env (例)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパースはシェル風のクォート・コメント処理をある程度サポートしています（export プレフィックス対応、クォート内のエスケープ、コメント扱いなど）。

---

## ディレクトリ構成

本コードベースの主なファイル・フォルダ構成（抜粋）:
- src/kabusys/
  - __init__.py (パッケージ定義、バージョンなど)
  - config.py (Settings、.env 自動ロード、環境変数検証)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント + DuckDB 保存機能)
    - schema.py (DuckDB スキーマ定義および init_schema / get_connection)
    - audit.py (監査ログ用スキーマ定義と初期化)
    - その他: audit / schema に関連する DDL
  - strategy/
    - __init__.py (戦略モジュールのプレースホルダ)
  - execution/
    - __init__.py (発注/執行モジュールのプレースホルダ)
  - monitoring/
    - __init__.py (モニタリング周りのプレースホルダ)

重要な公開 API（主な関数/オブジェクト）
- kabusys.settings — 設定オブジェクト（Settings インスタンス）
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.schema.get_connection(db_path)
- kabusys.data.jquants_client.get_id_token()
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.data.audit.init_audit_schema(conn)
- kabusys.data.audit.init_audit_db(db_path)

---

## 運用上の注意 / ベストプラクティス

- J-Quants のレート上限（120 req/min）を守るため、クライアントは内部でスロットリング・リトライを実装していますが、システム全体でのリクエスト頻度にも注意してください。
- DuckDB のファイルは排他制御に注意（複数プロセスからの書き込み等）。運用形態に応じて DB の扱いを設計してください。
- 監査ログは削除しない前提です。トレーサビリティを担保するため、更新は行っても削除を避けてください。
- 環境切り替え（paper_trading / live）を間違えると実際の発注につながる恐れがあります。KABUSYS_ENV の設定を厳密に管理してください。

---

必要に応じて README をプロジェクト固有の導入フロー（CI/CD、コンテナ化、実運用のジョブスケジュールなど）に合わせて拡張してください。追加でサンプルスクリプトや CLI、ユニットテストのテンプレートが欲しい場合はお知らせください。