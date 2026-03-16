# KabuSys

日本株自動売買プラットフォーム（ライブラリ部品）
このリポジトリは、J-Quants / kabuステーション 等を利用した日本株向けのデータプラットフォームと自動売買に必要な基盤モジュール群を含みます。  
主にデータ取得（ETL）、DuckDB スキーマ定義、品質チェック、監査ログ用スキーマ、J-Quants API クライアントなどを提供します。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数管理
  - プロジェクトルートの `.env` / `.env.local` を自動読込（必要に応じて無効化可能）
  - 必須変数の取得とバリデーション（Settings クラス）

- J-Quants API クライアント（`kabusys.data.jquants_client`）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レートリミット制御（120 req/min）、リトライ、トークン自動リフレッシュ
  - データを DuckDB に冪等に保存するユーティリティ（ON CONFLICT DO UPDATE）

- DuckDB スキーマ（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution 層を含むスキーマ定義
  - テーブル作成・インデックス作成・DB 初期化ヘルパー

- ETL パイプライン（`kabusys.data.pipeline`）
  - 差分更新（最終取得日を基に差分取得）、バックフィル、カレンダー先読み対応
  - 品質チェック実行フロー（欠損、重複、スパイク、日付不整合）
  - 結果を集約した `ETLResult` を返却

- データ品質チェック（`kabusys.data.quality`）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合（未来日・非営業日）検出
  - 問題は `QualityIssue` リストで返す（エラー/警告を区別）

- 監査ログ（`kabusys.data.audit`）
  - シグナル → 発注 → 約定 のトレースを行う監査用テーブル群
  - 冪等キー・ステータス管理・UTC タイムスタンプ運用を前提

---

## 必要環境 / 依存

- Python 3.10+（typing の一部記法を利用）
- 必須ライブラリ
  - duckdb
- 標準ライブラリ: logging, urllib, json, datetime, pathlib, os 等

（実行環境に合わせて pyproject.toml 等に依存を記載してください）

---

## 環境変数（主な設定）

このライブラリは環境変数から設定を読み込みます。プロジェクトルート（.git または pyproject.toml があるディレクトリ）に置いた `.env` / `.env.local` を自動読み込みします（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

例（`.env`）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   - (例) git clone ...

2. Python 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存インストール
   - pip install duckdb
   - （プロジェクトに pyproject.toml がある場合は `pip install -e .`）

4. 環境変数設定
   - プロジェクトルートに `.env` を作成して必要な値を設定するか、
   - シェル環境で直接エクスポートする。

5. DuckDB スキーマ初期化
   - 下記「使い方」を参照して DB を初期化してください。

---

## 使い方（例）

以下は最小限のコード例です。実運用ではロギング設定やエラー処理、スケジューラ（cron/Airflow 等）などを組み合わせてください。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema

# デフォルトのファイルパスを使う場合:
conn = schema.init_schema("data/kabusys.duckdb")

# インメモリ DB を試す場合:
# conn = schema.init_schema(":memory:")
```

- 日次 ETL を実行する
```python
from kabusys.data import pipeline, schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn)  # target_date を指定しなければ今日
print(result.to_dict())
```

- J-Quants の生データを直接取得して保存する
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# トークンを明示的に渡すことも可能
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
jq.save_daily_quotes(conn, records)
```

- 監査テーブルの初期化（既存の DuckDB 接続へ追加）
```python
from kabusys.data import audit, schema

conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

注意:
- ETL は差分更新を行います。初回は J-Quants が提供する最古日（2017-01-01）からロードします。
- pipeline.run_daily_etl は品質チェックを行い、`ETLResult.quality_issues` に検出結果を返します。重大な問題は呼び出し元で対処してください。

---

## ディレクトリ構成

リポジトリ内の主なファイル/パッケージ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得 & DuckDB 保存）
    - schema.py                      — DuckDB スキーマ定義 / init_schema
    - pipeline.py                    — ETL パイプライン（差分取得・品質チェック）
    - quality.py                     — データ品質チェック
    - audit.py                       — 監査ログ用テーブル初期化
    - pipeline.py                    — ETL フロー（重複記載あり）
  - strategy/
    - __init__.py                    — 戦略関連のエントリ（将来拡張想定）
  - execution/
    - __init__.py                    — 発注/実行関連（将来拡張想定）
  - monitoring/
    - __init__.py                    — 監視関連（将来拡張想定）

（上記は現状実装済みモジュールに基づく構成です。今後 strategy / execution / monitoring に機能が追加される想定です）

---

## 設計上の注意 / 実運用向けポイント

- レート制御:
  - J-Quants API は 120 req/min を想定。クライアントで固定間隔のスロットリングを実装しています。
- リトライ/エラーハンドリング:
  - HTTP 408/429/5xx は指数バックオフで最大 3 回リトライ。401 は refresh token を使って自動リフレッシュして 1 回リトライします。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE を使い冪等に実行されます（重複挿入リスクを低減）。
- 時刻管理:
  - 監査ログや fetched_at などの時刻は UTC を前提としています（audit.init_audit_schema は `SET TimeZone='UTC'` を実行）。
- テスト:
  - 自動 `.env` ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストで環境を明示的に切り替える場合など）。

---

## 貢献 / ライセンス

この README では明示していませんが、実プロジェクトとして公開する際は CONTRIBUTING.md や LICENSE を追加してください。

---

README はここまでです。必要であれば、以下の補足を作成できます:
- .env.example の完全テンプレート
- よくあるエラー（トークンエラー、DuckDB ファイルパーミッション等）と対処法
- CI / デプロイ手順（Airflow / cron / systemd など）