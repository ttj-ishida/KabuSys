# KabuSys

日本株自動売買システムの基盤ライブラリ（パッケージ: `kabusys`）  
バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコアコンポーネント群です。  
主に以下を提供します。

- J-Quants API からの市場データ取得クライアント（株価日足、四半期財務、JPXカレンダー）
- DuckDB を用いたスキーマ定義／初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定までのトレース用スキーマ）

設計上のポイント：
- API レート制限（120 req/min）を守るためのスロットリング
- 再試行（指数バックオフ、401 時はトークンリフレッシュ）
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- すべてのタイムスタンプは UTC を前提に扱う

---

## 機能一覧

- jquants_client
  - ID トークン取得（リフレッシュ）
  - 日足（OHLCV）、財務データ、マーケットカレンダー取得（ページネーション対応）
  - レートリミッタ、リトライ、401 時の自動トークン更新
  - DuckDB へ冪等保存（raw_prices / raw_financials / market_calendar）

- data.schema
  - Raw / Processed / Feature / Execution 層を含む DuckDB スキーマ定義
  - インデックス定義、初期化関数（init_schema / get_connection）

- data.pipeline
  - 差分 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 日次 ETL エントリ（run_daily_etl）: カレンダー取得 → 株価 → 財務 → 品質チェック
  - backfill / lookahead による後出し修正吸収

- data.quality
  - 欠損、スパイク（前日比閾値）、重複、日付不整合チェック
  - QualityIssue 型で結果を返す。重大度に基づく判断を呼び出し元に委譲

- data.audit
  - シグナル / 発注要求 / 約定 の監査ログテーブル定義と初期化
  - 発注の冪等キー（order_request_id）や各種制約を備える

- 設定管理（kabusys.config）
  - `.env` または OS 環境変数から設定を読み込み
  - プロジェクトルートを .git または pyproject.toml から自動検出して `.env` / `.env.local` を読み込む（自動ロードは無効化可能）

---

## 要件

- Python 3.10 以上（型ヒントで `|` を使用しているため）
- 依存パッケージ（例）:
  - duckdb

（必要に応じて `requirements.txt` / `pyproject.toml` を用意してください）

---

## インストール

開発中の環境であればリポジトリルートで:

```bash
# pip editable install（プロジェクトのセットアップ方法例）
pip install -e ".[dev]"   # もし extras を用意している場合
# 最低限
pip install duckdb
```

パッケージ配布があれば通常の `pip install .` を使用してください。

---

## 環境変数 / 設定

kabusys は環境変数（または `.env` / `.env.local`）から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化する場合:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API 用パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視 DB（SQLite）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — one of: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

例（.env）:

```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（概要）

1. Python 3.10+ を準備
2. 依存パッケージをインストール（少なくとも `duckdb`）
3. プロジェクトルートに `.env`（または環境変数）を配置（上記参照）
4. DuckDB スキーマ初期化

Python REPL / スクリプト例:

```python
from kabusys.data import schema

# ディスク DB を初期化（親ディレクトリが無ければ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
```

監査ログ（audit）スキーマを追加する場合:

```python
from kabusys.data import audit, schema
conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)  # 既存接続に監査テーブルを追加
```

---

## 使い方（主要な例）

- 日次ETL を実行する（フルフロー: カレンダー → 株価 → 財務 → 品質チェック）

```python
from datetime import date
from kabusys.data import pipeline, schema
from kabusys.config import settings

# DB 初期化（初回）
conn = schema.init_schema(settings.duckdb_path)

# ETL 実行（通常は日次バッチで実行）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- 特定日に対して ETL を実行

```python
result = pipeline.run_daily_etl(conn, target_date=date(2026, 1, 15))
```

- J-Quants の ID トークンを明示的に取得（テストや手動呼び出し時）

```python
from kabusys.data import jquants_client as jq

id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
```

- 個別の ETL ジョブを実行（差分取得ロジックを利用）

```python
from datetime import date
from kabusys.data import pipeline

fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
```

- 品質チェックのみを実行

```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

---

## 注意点 / 運用上のヒント

- J-Quants API のレート上限は 120 req/min に合わせてクライアント側でスロットリングしています。短時間に大量リクエストを投げないでください。
- API の 401 は自動でリフレッシュして 1 回再試行します。無限再帰を防ぐため get_id_token 呼び出し時はその再試行を抑止しています。
- DuckDB の初期化は冪等です。既存テーブルがあればスキップします。
- ETL の差分処理では「最終取得日から backfill_days 日分を再取得」して後出し修正を吸収する設計です（デフォルト backfill_days=3）。
- 品質チェックは Fail-Fast ではなく全件収集します。呼び出し側で重大度（error/warning）に応じた処理を行ってください。
- 自動で `.env` を読み込む挙動はプロジェクトルートの検出に依存します（.git または pyproject.toml）。CI やテストで制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（取得・保存）
      - schema.py                    — DuckDB スキーマ定義・初期化
      - pipeline.py                  — ETL パイプライン（差分・日次 ETL）
      - audit.py                     — 監査ログ（signal / order_request / execution）
      - quality.py                   — データ品質チェック
    - strategy/
      - __init__.py                   — 戦略層（実装はここに追加）
    - execution/
      - __init__.py                   — 発注／ブローカー連携（実装はここに追加）
    - monitoring/
      - __init__.py                   — 監視・メトリクス（実装はここに追加）

---

## 貢献 / 拡張案

- strategy, execution, monitoring サブパッケージに戦略実装やブローカー接続アダプタを追加してください。
- 品質チェックや監査ログの出力先（外部監視 / Slack 通知）を追加するプラグイン設計が有用です。
- CI 上での DB 初期化／ETL テスト用のヘルパー（in-memory DuckDB を使ったテスト）を整備してください。

---

必要であれば、README に含める追加の CLI コマンド例、より詳細な .env.example、サンプルデータを使ったハンズオン手順等も作成します。どの情報を追加したいか教えてください。