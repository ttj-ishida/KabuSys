# KabuSys

日本株自動売買システムの基盤ライブラリ（KabuSys）。  
データ取得・ETL・データ品質チェック・DuckDB スキーマ定義・監査ログなど、戦略層・実行層の共通基盤を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けの内部ライブラリです。主な役割は以下の通りです。

- J-Quants API からの市場データ取得（OHLCV・財務・マーケットカレンダー）
- 取得データの DuckDB への格納（冪等性を保証する INSERT ... ON CONFLICT ロジック）
- ETL パイプライン（差分取得、バックフィル、先読みカレンダー）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）スキーマ
- 環境変数 / .env の自動読み込みと集中設定管理

設計上の注目点:
- J-Quants API のレート制限（120 req/min）に対応する固定間隔スロットリング
- リトライ（指数バックオフ、最大 3 回）および 401 時の自動トークンリフレッシュ
- Look-ahead バイアス対策のため fetched_at を UTC で記録
- ETL と品質チェックはフェールセーフ（1 ステップの失敗が他を止めない）

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート基準）
  - 必須設定チェック（_require）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化

- データ取得（kabusys.data.jquants_client）
  - fetch_daily_quotes（株価日足）
  - fetch_financial_statements（財務）
  - fetch_market_calendar（JPX カレンダー）
  - save_* 系関数で DuckDB へ冪等保存

- スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL
  - init_schema(db_path) による初期化と接続取得

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の流れ
  - 差分取得とバックフィル対応
  - ETLResult による実行結果収集

- 品質チェック（kabusys.data.quality）
  - 欠損データ検出（OHLC 欠損）
  - スパイク検出（前日比閾値）
  - 重複チェック（主キー重複）
  - 日付不整合（未来日付 / 非営業日データ）
  - run_all_checks で一括実行

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の監査スキーマ
  - init_audit_schema / init_audit_db を提供

---

## 必要環境・依存

- Python 3.10 以上（型ヒント: `Path | None` 等を使用）
- duckdb（DuckDB Python パッケージ）
  - インストール例: pip install duckdb

（その他は標準ライブラリのみ使用）

推奨インストール方法（プロジェクトルートで）:
```
pip install -e .    # packaging が用意されている場合
pip install duckdb
```

---

## 環境変数（必須・任意）

必須（アプリケーションで利用する際に設定してください）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意 / デフォルト値あり:
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）。デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite パス。デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

.env の読み込み順序（優先度低 → 高）:
- .env （プロジェクトルート）
- .env.local（.env を上書き）
- OS 環境変数が最優先（上書き防止）

.env の書式は一般的な KEY=VALUE 形式に対応します。クォートや export プレフィックスもハンドリングします。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python と pip を準備（Python >= 3.10）
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb
   - （プロジェクトに packaging があれば）pip install -e .
4. プロジェクトルートに .env を作成し、必要な環境変数を設定
5. DuckDB スキーマ初期化（下記「使い方」を参照）

---

## 使い方（簡易ガイド）

以下は Python REPL やスクリプト内での基本的な使い方例です。

- スキーマ初期化（DuckDB ファイルを作成してテーブルを作る）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH の値を反映
conn = init_schema(settings.duckdb_path)
```

- 監査ログスキーマ初期化（既存接続へ追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

- 日次 ETL 実行（市場カレンダー、株価、財務、品質チェックを実行）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 個別ジョブを呼ぶ（差分 ETL の直接呼び出し）
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

# 例: ある日付までの株価を差分更新
fetched, saved = run_prices_etl(conn, target_date=date(2025, 1, 15))
```

- 品質チェックを単独実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点:
- J-Quants API へのリクエストはレート制限があり、内部でスロットリング・リトライを行います。
- API 認証は JQUANTS_REFRESH_TOKEN を使用して id_token を取得する仕組みです。
- run_daily_etl は各ステップごとに例外を捕捉し、ETLResult.errors にエラー概要を蓄積します。

---

## ディレクトリ構成

プロジェクトの主要ファイル・モジュールは以下の構成です（抜粋）。

- src/
  - kabusys/
    - __init__.py               # パッケージ定義（__version__=0.1.0）
    - config.py                 # 環境変数・設定管理
    - execution/
      - __init__.py             # 実行（発注）層のプレースホルダ
    - strategy/
      - __init__.py             # 戦略層のプレースホルダ
    - monitoring/
      - __init__.py             # 監視モジュール（プレースホルダ）
    - data/
      - __init__.py
      - jquants_client.py       # J-Quants API クライアント（取得・保存ロジック）
      - schema.py               # DuckDB スキーマ定義と初期化
      - pipeline.py             # ETL パイプライン（差分・バックフィル・品質チェック）
      - audit.py                # 監査ログスキーマ初期化
      - quality.py              # データ品質チェック

---

## 実運用上の注意

- 環境変数は機密情報を含むため、.env をリポジトリにコミットしないでください（.gitignore に追加推奨）。
- 本ライブラリは発注・実行ロジックの基盤を提供しますが、実際の発注を行うブローカー接続部分（kabu API 呼び出しや資金管理など）は別実装が必要です。
- run_daily_etl の backfill 設定や spike_threshold を運用に合わせて調整してください。
- DuckDB のファイルバックアップや VACUUM、パフォーマンス監視は運用側で行ってください。

---

必要に応じて README に追記できます。例えば:
- サンプル .env.example
- CI / デプロイ手順
- 詳細な API 使用例（ページネーションや大規模バックフィルのベストプラクティス）
- 戦略層 / 実行層の実装テンプレート

追加したい項目があれば教えてください。