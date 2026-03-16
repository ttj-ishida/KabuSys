# KabuSys

日本株向けの自動売買プラットフォーム基盤ライブラリ（プロトタイプ）

KabuSys は日本株の市場データ取得、データベーススキーマ管理、ETL パイプライン、データ品質チェック、監査ログ基盤を提供するライブラリ群です。J-Quants API を中心にデータ収集を行い、DuckDB に保存して再現性のある自動売買ワークフローを構築するための基盤機能を備えています。

---

## 主な機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - API レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - ページネーション対応、取得時刻（fetched_at）の記録（Look-ahead Bias 対策）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層の包括的なテーブル群定義
  - インデックス定義、外部キー依存を考慮した作成順
  - 監査ログ（signal_events / order_requests / executions 等）の初期化支援

- ETL パイプライン
  - 差分更新（最終取得日からの差分 + バックフィル）で効率的にデータを取得
  - 市場カレンダーの先読み（デフォルト 90 日）で営業日補正
  - 品質チェック（欠損・スパイク・重複・日付不整合）の実行
  - 各ステップは独立してエラーハンドリング（1ステップ失敗でも残りは実行）

- データ品質チェック
  - 欠損（OHLC 欄）、前日比スパイク検出、主キー重複、将来日付・非営業日データ検出
  - QualityIssue データ構造で詳細（サンプル行）を返却

- 環境管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数の検証（例: JQUANTS_REFRESH_TOKEN 等）

---

## 要件（推奨）

- Python 3.10+
- pip により duckdb をインストール（その他の依存は標準ライブラリ中心）
  - 例: pip install duckdb

（本リポジトリは最低限のサンプルモジュールで構成されており、実際の運用では追加パッケージや broker 用クライアント等が必要になる可能性があります。）

---

## セットアップ手順

1. リポジトリをクローンまたはパッケージを展開します。

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate

3. 必要なパッケージをインストール
   - pip install duckdb

4. 環境変数を設定（.env または OS 環境変数）
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化できます）。

.env 例:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
# (省略可) KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（省略時は data/kabusys.duckdb / data/monitoring.db）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 動作環境
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

必須の環境変数:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

（設定が欠けると Settings によって例外が投げられます）

---

## 使い方（簡易ガイド）

以下は主要な利用フローの例です。Python スクリプトや CLI から呼び出せます。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリを自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# 以降 conn を ETL 等に渡して使用
```

2) 監査ログスキーマの追加
```python
from kabusys.data import audit
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# 監査ログテーブルを追加（UTC タイムゾーン設定を適用）
audit.init_audit_schema(conn)
```

3) 日次 ETL の実行
```python
from datetime import date
from kabusys.data import pipeline
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4) 個別ジョブ（例: 株価のみ）
```python
from datetime import date
from kabusys.data import pipeline
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

5) J-Quants の低レベル API を直接呼ぶ（トークン自動管理・リトライあり）
```python
from kabusys.data import jquants_client as jq

# トークンを渡さず呼べばキャッシュと自動リフレッシュを利用
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
```

Notes:
- run_daily_etl は以下順序で処理します: カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック
- ETL の差分戦略は最終取得日に基づく自動算出（backfill_days により後出し修正を吸収）
- 品質チェックは問題を検出しても ETL を中止せずに結果（QualityIssue）を返します

---

## 設定と動作の注意点

- 環境変数の自動読み込み
  - パッケージ内の config.py は .git や pyproject.toml を起点にプロジェクトルートを探索し、`.env` と `.env.local` を読み込みます。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用途など）。

- DB のデフォルトパス
  - DuckDB: data/kabusys.duckdb
  - SQLite（監視用データベースに利用する想定）: data/monitoring.db
  - これらは Settings.duckdb_path / sqlite_path から取得できます。

- ロギングと環境
  - KABUSYS_ENV は development / paper_trading / live のいずれかを指定（大文字小文字は問わない）。
  - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか。

- J-Quants に関する重要な設計点
  - API レート制限（120 req/min）を厳守するため固定間隔のスロットリングを導入
  - 408/429/5xx 系は指数バックオフで最大 3 回リトライ
  - 401 はトークン期限切れを想定し自動でリフレッシュして 1 回だけリトライ
  - 取得したデータには fetched_at を UTC で付与していつデータが得られたかをトレース

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要モジュールとファイル構成は以下のとおりです（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py         # J-Quants API クライアント（取得・保存ロジック）
      - schema.py                 # DuckDB スキーマ定義と初期化
      - pipeline.py               # ETL パイプライン（差分更新・品質チェック）
      - audit.py                  # 監査ログ（トレーサビリティ）スキーマ
      - quality.py                # データ品質チェック

（上記は本パッケージのコア部分の一覧であり、戦略層・実行層・監視などの拡張モジュールは別途実装して接続します）

---

## 開発・運用上のヒント

- テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して環境読み込みを抑制すると、テストごとに意図した環境変数を注入しやすくなります。
- DuckDB の初期化は一度実行しておけば冪等的にテーブルが作成されます（init_schema）。
- ETL を定期実行する場合は run_daily_etl を呼び出すラッパー（例: cron / Airflow / Prefect）を用意し、結果を監視・アラートする仕組みを組み合わせてください。
- 監査ログ（order_requests / executions）は削除しない前提で設計されています。運用時のディスク使用量やパージ方針は別途検討してください。

---

## 今後の拡張案（参考）

- broker（kabuステーション）との実際の注文送信ロジック（execution 層）の実装
- Slack 通知やメトリクス収集（Prometheus など）を統合する監視モジュールの追加
- 戦略層の実装と特徴量生成（Feature Layer）の自動化
- 権限・シークレット管理の強化（Vault 等の利用）

---

ご不明点や README の追加要望（例えば運用手順の自動化スクリプト例、より詳しい .env.example ファイル、CI/CD 向けの設定など）があれば教えてください。必要に応じてサンプルスクリプトやテンプレートを作成します。