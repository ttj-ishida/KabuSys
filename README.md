# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群（プロトタイプ）

このリポジトリは、J-Quants API 等から市場データを取得して DuckDB に保存・検査し、
戦略→発注→監査までのデータフローを支援するモジュール群を提供します。
設計上は「データレイヤー」「特徴量レイヤー」「実行・監査レイヤー」を念頭に置いています。

主な用途例:
- J-Quants から株価・財務・カレンダーを差分取得して DuckDB に保存
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ETL パイプラインの一括実行（run_daily_etl）
- 発注フローの監査ログ（監査用スキーマ）

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（サンプルコード）
- 環境変数（.env）例
- ディレクトリ構成
- 補足 / 注意事項

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォームおよび自動売買補助ライブラリです。
主要な機能は以下の通りです。

- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB 用スキーマ定義と初期化
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェックモジュール（欠損、スパイク、重複、日付整合性）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用テーブル定義
- 環境変数管理（.env 自動読み込み、必須チェック）

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API から株価日足、財務データ、マーケットカレンダーを取得
  - API レート制限（120 req/min）に合わせた固定間隔スロットリング
  - 再試行（指数バックオフ、最大3回）、401 時の自動トークンリフレッシュ
  - データの取得日時（fetched_at）を UTC で記録
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）

- data/schema.py
  - Raw / Processed / Feature / Execution レイヤーのテーブル DDL
  - インデックス定義、init_schema() による初期化処理

- data/pipeline.py
  - 差分 ETL（calendar → prices → financials）の実行
  - backfill（デフォルト 3 日）による後出し修正吸収
  - run_daily_etl() による一括実行と品質チェック呼び出し

- data/quality.py
  - 欠損データ検出、スパイク検出、重複チェック、日付不整合チェック
  - QualityIssue オブジェクトで結果を返却（severity により呼び出し元が判断）

- data/audit.py
  - シグナル / 発注要求 / 約定 の監査用テーブルとインデックスを定義
  - init_audit_schema() / init_audit_db() による初期化

- config.py
  - .env（および .env.local）や OS 環境変数から設定を自動読み込み
  - Settings クラスでアプリ設定に型付きアクセス（必須キーは例外を投げる）
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## セットアップ手順

前提:
- Python 3.10 以上（型シンタックスに | を使用）
- pip が利用可能

推奨手順（ローカル開発）:

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - Linux / macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   - pip install duckdb
   - （他に logging 等標準ライブラリを使用しています。外部依存は最小限です）
   - 実運用・開発で必要なパッケージがある場合は requirements.txt を用意して利用してください。

4. 環境変数設定
   - プロジェクトルートに .env（および任意で .env.local）を配置してください。
   - 必須の環境変数は下記「環境変数例」を参照。

5. DuckDB スキーマ初期化（例）
   - 下記の「使い方」を参照して DB を初期化してください。

---

## 使い方（主要な例）

簡単な ETL 実行の例（Python スクリプト）:

例: etl_run.py
```python
from datetime import date
from kabusys.data import schema, pipeline

# DuckDB ファイルパス（デフォルト: data/kabusys.duckdb が settings で使われる）
db_path = "data/kabusys.duckdb"

# 1) スキーマ初期化（存在すればスキップされる）
conn = schema.init_schema(db_path)

# 2) 日次 ETL を実行（省略時 target_date は今日）
result = pipeline.run_daily_etl(conn, target_date=date.today())

# 結果を確認
print(result.to_dict())
```

監査スキーマを追加で初期化する例:
```python
from kabusys.data import audit, schema

conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)  # 既存接続に監査テーブルを追加
```

DuckDB をインメモリで使いたい場合:
```python
conn = schema.init_schema(":memory:")
```

注意:
- J-Quants の認証トークンは settings.jquants_refresh_token 経由で取得されます（環境変数 JQUANTS_REFRESH_TOKEN）。
- jquants_client は自動的に ID トークンをキャッシュ・リフレッシュします。テスト時は id_token を直接注入可能です。

---

## 環境変数（.env）例

プロジェクトルートに置く .env の最小例:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
#KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意。デフォルトはローカル

# Slack 通知（任意だが Settings では必須扱い）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# DB パス（省略可能）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境とログ
KABUSYS_ENV=development  # development / paper_trading / live
LOG_LEVEL=INFO
```

- 必須項目（Settings が要求するもの）は少なくとも JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID です。足りないと起動時に ValueError が発生します。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を基準に行われます。読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

主要ファイル / モジュール:

- src/kabusys/
  - __init__.py
  - config.py                 - 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py       - J-Quants API クライアント（取得 + 保存）
    - schema.py               - DuckDB スキーマ定義・初期化
    - pipeline.py             - ETL パイプライン（run_daily_etl 等）
    - quality.py              - データ品質チェック
    - audit.py                - 監査ログ（シグナル→発注→約定）の DDL 初期化
    - pipeline.py             - ETL 実行ロジック（差分更新・品質チェック）
  - strategy/                  - 戦略モジュール入口（未実装のプレースホルダ）
  - execution/                 - 発注実行モジュール入口（未実装のプレースホルダ）
  - monitoring/                - 監視モジュール（未実装のプレースホルダ）

README 等のトップレベルファイルはプロジェクトルートに置いてください。

---

## 補足 / 注意事項

- Python バージョン: 3.10 以上を推奨（PEP 604 の型構文 (A | B) を使用）。
- ネットワーク呼び出しは jquants_client が直接 urllib を使って行っています。プロキシやタイムアウト等は必要に応じて設定してください。
- ETL は各ステップが独立して失敗を処理します（1ステップ失敗でも他は継続）。run_daily_etl の戻り値に errors / quality_issues が含まれますので呼び出し側で対応してください。
- DuckDB は組み込み型の軽量 OLAP DB で高速ですが、運用時のファイルロックやバックアップ方針はプロジェクト要件に合わせて検討してください。
- 発注実行・ブローカー連携・Slack 通知等は基盤部分が用意されているだけで、実運用では安全性（冪等性、冗長性、テスト）が重要です。

---

必要があれば、README に CLI 実行例・ユニットテストの書き方・CI 設定例・より詳しい .env の例などを追加します。どの内容を優先して追加しますか？