# KabuSys

日本株自動売買システムのライブラリ（モジュール群）。  
データ収集（J-Quants）、DuckDB スキーマ定義、ETL パイプライン、品質チェック、監査ログなど、戦略や発注層の基盤となる機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリです。主に次を目的とします。

- J-Quants API からの市場データ（株価日足、財務データ、マーケットカレンダー）取得
- DuckDB による段階的なデータ保管（Raw / Processed / Feature / Execution / Audit）
- ETL（差分取得・バックフィル）パイプラインと品質チェック
- 発注系の監査ログ（トレーサビリティ）用スキーマの初期化

設計上のポイント:
- API のレートリミット（120 req/min）を守る固定間隔スロットリング
- リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- 品質チェックは全件検出し呼び出し元で判断できる設計

---

## 機能一覧

- 環境変数管理（.env 自動ロード、Settings クラス）
- J-Quants クライアント
  - 株価日足（OHLCV）のページネーション取得
  - 財務データ（四半期 BS/PL）取得
  - マーケットカレンダー取得
  - トークン取得／自動リフレッシュ、レート制御、リトライ
- DuckDB スキーマ定義 / 初期化（data.schema.init_schema）
  - Raw / Processed / Feature / Execution テーブル群
  - インデックス定義
- 監査ログスキーマ（data.audit.init_audit_schema / init_audit_db）
- ETL パイプライン（data.pipeline.run_daily_etl など）
  - 差分更新、バックフィル、カレンダー先読み
  - 品質チェックの統合（data.quality）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 演算子を使用）
- DuckDB を使用（duckdb パッケージ）

1. リポジトリをクローン / パッケージを配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install duckdb
   - （必要に応じて urllib 関連は標準ライブラリです）
   - プロジェクトで requirements.txt がある場合はそれを使ってください
4. 環境変数の設定
   - プロジェクトルートに `.env`（および `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必要な環境変数（主要なもの）は以下参照。
5. DuckDB スキーマ初期化
   - Python からスキーマを初期化します（例を下に記載）。

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知用 Slack 設定（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)、デフォルト development
- LOG_LEVEL: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)、デフォルト INFO

注意: `.env.example` をプロジェクトルートに用意しておき、そこから `.env` を作成してください（コード内に .env.example の明確なファイルは無い想定ですが、Settings._require の説明にその文言が出ます）。

---

## 使い方（代表的な API と実行例）

以下は Python REPL またはスクリプトでの利用例です。

1) スキーマ初期化（DuckDB）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ディレクトリが無ければ自動作成
```

2) 監査ログスキーマ初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema
# 既に init_schema で得た conn を渡す
init_audit_schema(conn)
```

3) J-Quants トークン取得（明示的に）
```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を利用
```

4) データ取得と保存（株価日足）
```python
from kabusys.data import jquants_client as jq
# conn は DuckDB の接続
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

5) 日次 ETL の実行（カレンダー・株価・財務・品質チェックをまとめて実行）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を省略すると今日を基準に実行
print(result.to_dict())
```
run_daily_etl は ETLResult を返します。フィールドには取得数／保存数／品質問題／エラー情報が含まれます。

6) 品質チェックのみを実行したい場合
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=date(2024,1,31))
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

設定値の参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 必須
print(settings.duckdb_path)            # Path オブジェクト
print(settings.env, settings.is_live, settings.log_level)
```

ログ設定や通知連携（Slack 等）はプロジェクト側で行ってください。KabuSys はトークン／チャネル ID 等の設定を提供します。

---

## 実装上のポイント（短い技術メモ）

- jquants_client
  - レート制御: _RateLimiter により 120 req/min を固定間隔で守る
  - リトライ: 408/429/5xx に対して最大 3 回の指数バックオフ
  - 401 受信時: トークンを自動でリフレッシュして一度リトライ
  - ページネーション: pagination_key による取得ループ
  - 保存: DuckDB へは ON CONFLICT DO UPDATE による冪等操作

- data.schema
  - Raw / Processed / Feature / Execution / Audit をカバーするテーブル群定義
  - 必要なインデックスを作成（頻出クエリに対する最適化）

- data.pipeline
  - 差分更新を基本とし、バックフィルにより後出し修正を吸収
  - カレンダーは先に取得して営業日判定に利用
  - 品質チェックは Fail-Fast せず、検出結果を集約して返す

- data.quality
  - 欠損、重複、スパイク、日付不整合（未来日・非営業日）を検出
  - 各チェックは QualityIssue のリストを返す（severity: error/warning）

---

## ディレクトリ構成

プロジェクト内の主要なファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  -- 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント（取得・保存）
    - schema.py                -- DuckDB スキーマ定義・初期化
    - pipeline.py              -- ETL パイプライン実装
    - quality.py               -- データ品質チェック
    - audit.py                 -- 監査ログスキーマ（トレーサビリティ）
    - pipeline.py
  - execution/
    - __init__.py              -- 発注・約定連携のためのパッケージ入口（未実装箇所あり）
  - strategy/
    - __init__.py              -- 戦略層のパッケージ入口（未実装箇所あり）
  - monitoring/
    - __init__.py              -- モニタリング用パッケージ（未実装箇所あり）

※ 実装の一部（execution、strategy、monitoring） はパッケージの骨組みのみが定義されています。実際の戦略ロジックや発注ドライバは別途実装が必要です。

---

## 注意点・ヒント

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。テストや CI で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB ファイルの親ディレクトリが存在しない場合は自動で作成されます。
- run_daily_etl は各ステップでエラーをキャッチして続行するため、戻り値の ETLResult.errors を確認して部分失敗を検知してください。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかを設定してください（未設定時は development）。

---

この README はコードベースの主要機能と利用手順を簡潔にまとめたものです。詳細な運用（運用スケジュール、ログ管理、発注フローの実装、安全性チェックなど）は運用ドキュメントとして別途整備してください。