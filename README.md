# KabuSys — 日本株自動売買システム

軽量なデータプラットフォームと ETL / 監査基盤を備えた、日本株向け自動売買システムのコアライブラリ群です。  
主に J-Quants API からのデータ取得、DuckDB スキーマ定義・初期化、差分 ETL パイプライン、データ品質チェック、監査ログ用テーブルなどを提供します。

---

## 主な機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回、408/429/5xx 対応）
  - 401 発生時にリフレッシュトークンで自動トークン更新（1 回のみ）
  - 取得時刻（fetched_at）を UTC で記録（Look-ahead バイアス対策）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution（監査含む）層のテーブル定義
  - インデックス定義、外部キーを考慮した作成順
  - 冪等な初期化（既存テーブルはスキップ）

- ETL パイプライン
  - 差分取得（最終取得日をもとに自動算出）とバックフィル（デフォルト 3 日）
  - カレンダーの先読み（デフォルト 90 日）
  - 保存は冪等（ON CONFLICT DO UPDATE）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - ETL 結果を集約する ETLResult 型

- データ品質チェック
  - 欠損データ、スパイク（前日比閾値）、主キー重複、日付不整合の検出
  - 問題は QualityIssue 列挙で返却（エラー／ワーニングを区別）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル
  - order_request_id による冪等化、UTC タイムスタンプ保持

- 設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - 環境変数アクセス用 settings オブジェクト（必須チェック・検証含む）
  - 自動ロード無効化オプション（KABUSYS_DISABLE_AUTO_ENV_LOAD）

---

## 必要要件（推奨）

- Python 3.9+
- 依存パッケージ（最低限）:
  - duckdb
- ネットワーク接続（J-Quants API へアクセスする場合）
- J-Quants のリフレッシュトークン等の環境変数

（実際のプロジェクトでは requirements.txt / pyproject.toml に依存を記載してください）

---

## セットアップ手順（開発環境）

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate もしくは Windows の場合 .venv\Scripts\activate

2. 依存パッケージをインストール
   - pip install duckdb

   （プロジェクトに packaging があれば pip install -e . を実行）

3. プロジェクトルートに `.env`（および任意で `.env.local`）を作成する。  
   package の config モジュールはプロジェクトルート（.git または pyproject.toml を探索）を基準に自動で読み込みます。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: `.env` の最低限の必須変数（サンプル）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_station_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
# 任意:
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は代表的なユースケースの Python スニペットです。

1) DuckDB スキーマを初期化して接続を取得する
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Path オブジェクトを返します（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())

# ETL 結果確認
print(result.to_dict())
if result.has_errors:
    print("ETL 中にエラーがあります:", result.errors)
if result.has_quality_errors:
    print("品質チェックでエラーが検出されました")
```

3) 監査ログ用スキーマを既存の接続に追加する
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
init_audit_schema(conn)
```

4) J-Quants の ID トークン取得・直接データ取得（テスト等）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を利用して取得
rows = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,12,31))
```

5) ETL 内での品質チェック（個別呼び出し）
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## 主要 API（抜粋）

- 設定
  - kabusys.config.settings — 環境変数をラップしたプロパティ集

- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int

- DuckDB スキーマ（kabusys.data.schema）
  - init_schema(db_path) -> duckdb connection
  - get_connection(db_path) -> duckdb connection

- ETL（kabusys.data.pipeline）
  - run_daily_etl(conn, target_date=None, ...) -> ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl

- 品質チェック（kabusys.data.quality）
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5) -> list[QualityIssue]
  - check_missing_data / check_spike / check_duplicates / check_date_consistency

- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn)
  - init_audit_db(db_path) -> duckdb connection

---

## 環境変数一覧（主なもの）

必須（ETL / 実行に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意 / デフォルトあり:
- KABUSYS_ENV — 環境（development / paper_trading / live）、デフォルト development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）、デフォルト INFO
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）

制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化

注意: settings の必須プロパティは _require() によって未設定時に ValueError を投げます。

---

## ディレクトリ構成

（リポジトリの src/kabusys 配下の主要ファイルを抜粋）

```
src/
└─ kabusys/
   ├─ __init__.py            # パッケージメタデータ
   ├─ config.py              # 環境変数 / 設定管理
   ├─ execution/             # 発注・約定関連（未実装の初期モジュール）
   │  └─ __init__.py
   ├─ strategy/              # 戦略実装用モジュール（未実装の初期モジュール）
   │  └─ __init__.py
   ├─ monitoring/            # 監視用モジュール（未実装の初期モジュール）
   │  └─ __init__.py
   └─ data/
      ├─ __init__.py
      ├─ jquants_client.py   # J-Quants API クライアント（取得・保存・リトライ・レート制御）
      ├─ schema.py          # DuckDB スキーマ定義・初期化
      ├─ pipeline.py        # ETL パイプライン（差分取得・保存・品質チェック）
      ├─ audit.py           # 監査ログ（signal / order_requests / executions）
      └─ quality.py         # データ品質チェック
```

---

## 運用上の注意 / 設計におけるポイント

- API レート制限を厳守（120 req/min）。jquants_client は固定間隔スロットリングで制御します。
- J-Quants から 401 が返った場合は自動で id_token をリフレッシュして 1 回再試行します。
- 保存は冪等設計（ON CONFLICT DO UPDATE）なので、何度実行しても重複データは上書きされます。
- ETL は各ステップを個別にハンドリングし、1 ステップ失敗でも他の処理を継続して問題の全件収集を行います（Fail-Fast ではない）。
- 監査テーブルはトレーサビリティを重視し、削除を前提としない設計です（FK は ON DELETE RESTRICT 等）。

---

## 例外・エラー処理

- settings の必須環境変数が未設定の場合は ValueError が発生します。
- jquants_client の _request は最大リトライ後に RuntimeError を送出します。呼び出し側で適切に例外処理してください。
- quality.run_all_checks は検出された問題を一覧で返し、致命的な問題は呼び出し側が判断する設計です。

---

必要に応じて README に以下を追加してください:
- テストの実行方法
- CI / デプロイ手順
- 具体的な戦略実装のサンプル
- 依存パッケージの固定（requirements.txt / pyproject.toml）

他に記載したい情報（例: .env.example のテンプレート、実際のコマンドラインツール例、Slack 通知の使い方等）があれば教えてください。README を用途に合わせて拡張します。