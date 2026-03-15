# KabuSys

日本株自動売買のための共通ライブラリ群（データ取得・スキーマ定義・監査ログ等）

このリポジトリは、自動売買プラットフォームの基盤コンポーネントを提供します。主に以下を実装しています。

- J-Quants API クライアント（株価・財務・マーケットカレンダーの取得、レート制御・リトライ・トークンリフレッシュ対応）
- DuckDB スキーマ定義 / 初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 環境変数 / .env 読み込みユーティリティ

現時点では strategy / execution / monitoring パッケージは骨組みのみを提供しています。

## 主な機能 (Features)

- 環境変数・.env ファイルの自動読み込み（プロジェクトルート検出）
  - 読み込み優先度: OS 環境 > .env.local > .env
  - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- J-Quants API クライアント
  - OHLCV（日足）、四半期財務データ、JPX マーケットカレンダー取得
  - API レート制限（120 req/min）遵守のための固定間隔レートリミッタ
  - リトライ（指数バックオフ、最大 3 回）、HTTP 408/429/5xx 対応
  - 401 受信時はリフレッシュトークンで自動的に ID トークンを更新して 1 回リトライ
  - ページネーション対応、取得時刻 (fetched_at) を UTC で記録（Look-ahead Bias 防止）
  - DuckDB への保存関数は冪等（ON CONFLICT DO UPDATE）
- DuckDB スキーマ（Data Layer）
  - Raw / Processed / Feature / Execution 各層のテーブル定義
  - 頻出クエリ向けインデックス群
  - init_schema / get_connection API
- 監査ログ（Audit）
  - signal_events, order_requests, executions のテーブル定義
  - order_request_id を冪等キーとして二重発注防止
  - UTC タイムゾーン強制、インデックス設定
  - init_audit_schema / init_audit_db API

## 必要条件

- Python 3.10+
- duckdb（データベース）
- （実運用時）J-Quants のリフレッシュトークン、kabuステーション API、Slack トークン等

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
```

※パッケージ化・依存関係管理はお好みの方法で行ってください（pip/poetry 等）。

## 環境変数（主要）

必須（コード内で _require によって要求されるもの）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

オプション / 既定値あり:

- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（既定: development）
- LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")（既定: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB）パス（既定: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 を設定）

.sample .env（README 用例）:

```
# .env 例（実運用では値は安全に管理してください）
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_api_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

## セットアップ手順

1. Python 3.10+ を準備し、仮想環境を作成・有効化する
2. 依存ライブラリをインストール（最小: duckdb）
   - pip install duckdb
3. プロジェクトルートに .env を用意する（上記の必須環境変数を設定）
   - OS 環境変数で上書き可能
4. DuckDB スキーマを初期化する（例は次節の使い方参照）

## 使い方（簡単なコード例）

- DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path で .env の DUCKDB_PATH を利用可能
conn = init_schema(settings.duckdb_path)  # ファイル DB を作成・初期化
# あるいはメモリ DB を使う:
# conn = init_schema(":memory:")
```

- J-Quants から日足データを取得して保存する

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

# 単一銘柄・日付範囲で取得
from datetime import date
records = fetch_daily_quotes(code="6758", date_from=date(2023,1,1), date_to=date(2023,12,31))

# DuckDB に冪等的に保存
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

- 財務データ / マーケットカレンダーの取得・保存

```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

fin_records = fetch_financial_statements(code="6758")
save_financial_statements(conn, fin_records)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

- ID トークンを明示的に取得する（テストや直接呼び出し時に便利）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って POST 実行
```

- 監査ログを初期化（既存の DuckDB 接続に監査テーブルを追加）

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

注意点:
- J-Quants API にはレート制限があるため、fetch 系は内部でレート制御・リトライを行います。
- 401 が返ってきた場合は自動的にリフレッシュして 1 回リトライします（ただし無限再帰は防止）。
- 保存関数は ON CONFLICT DO UPDATE により冪等です。

## 自動 .env 読み込みの挙動

- パッケージが import されると、プロジェクトルート（.git または pyproject.toml の存在する親ディレクトリ）を探索し、.env を自動で読み込みます。
- 読み込み順: OS 環境変数（最優先） → .env → .env.local（.env.local は上書き）
- 自動読み込みを無効化したい場合は、Python プロセスの前に環境変数をセットします:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "import kabusys; ..."
```

## ディレクトリ構成

リポジトリ（src/kabusys）内の主要ファイルは以下の通りです:

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py                      # 環境変数・.env 読み込み設定
   ├─ data/
   │  ├─ __init__.py
   │  ├─ schema.py                   # DuckDB スキーマ定義・init_schema
   │  ├─ jquants_client.py           # J-Quants API クライアント（fetch/save）
   │  └─ audit.py                    # 監査ログ（signal / order_request / executions）
   ├─ strategy/
   │  └─ __init__.py                 # 戦略モジュール（骨組み）
   ├─ execution/
   │  └─ __init__.py                 # 発注・ブローカー接続（骨組み）
   └─ monitoring/
      └─ __init__.py                 # 監視・メトリクス（骨組み）
```

## 設計のハイライト / 注意点

- Look-ahead Bias 防止のため、外部データの取得時刻（fetched_at）を UTC で保存しています。これにより「いつシステムがそのデータを知り得たか」を追跡可能です。
- データ保存は冪等に設計されており、同じデータを二重に保存しても上書きが行われます（ON CONFLICT DO UPDATE）。
- 監査ログは削除しない前提で設計されており、トレースを重視します（FK は ON DELETE RESTRICT）。
- DuckDB の SQL 型定義や制約（CHECK 等）を積極的に採用し、不正データ挿入の検出を助けます。

## 今後の拡張案（非 exhaustive）

- strategy / execution / monitoring の具象実装（ポートフォリオ最適化・発注エグゼキューション・アラート）
- CI 用のテストケース、型チェック、静的解析
- packaging (pyproject.toml) / pip 配布

---

問題や実装上の質問があれば教えてください。README の改善（例: .env.example の追加、より詳細な使用例、CLI ヘルパーの説明 等）も対応できます。