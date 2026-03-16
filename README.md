# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ (プロトタイプ)。  
このリポジトリはデータ取得、スキーマ管理、データ品質チェック、監査ログの初期化等の基盤機能を提供します。

## 概要
KabuSys は以下を目的としたモジュール群を含みます。

- J-Quants API からの時系列（OHLCV）・財務・マーケットカレンダーの取得
- DuckDB によるデータ永続化（Raw / Processed / Feature / Execution 層）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）スキーマ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 環境変数による設定管理（.env 自動ロード機能）

設計上のポイント：
- API レート制限・リトライ・トークン自動リフレッシュを考慮した J-Quants クライアント
- DuckDB スキーマは冪等（既存テーブルがあればスキップ）
- 監査ログは削除しない前提で設計（ON DELETE RESTRICT 等）

## 機能一覧
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得ラッパー（未設定時に明確なエラー）
  - KABUSYS_ENV によるモード区分（development / paper_trading / live）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）・財務データ・マーケットカレンダー取得（ページネーション対応）
  - レートリミット（120 req/min）管理、指数バックオフによるリトライ、401 時トークン自動更新
  - DuckDB 用の保存関数（raw_prices, raw_financials, market_calendar）— ON CONFLICT DO UPDATE による冪等性
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - init_schema / get_connection API
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの初期化
  - すべての TIMESTAMP は UTC 保存（初期化時に SET TimeZone='UTC'）
- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合の検出
  - run_all_checks による一括実行、QualityIssue のリストを返す

## セットアップ手順

前提
- Python 3.10 以上を推奨（PEP 604 などの型記法を使用）
- DuckDB を使用するためネイティブライブラリが必要（pip で導入可能）

1. 仮想環境作成（推奨）
   - Linux / macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. 依存パッケージのインストール
   - 最小例（duckdb が必須）:
     ```
     pip install duckdb
     ```
   - 他に必要なパッケージがあればプロジェクトの requirements.txt / pyproject.toml を参照してインストールしてください。

3. 環境変数の用意
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を置くと、自動的に読み込まれます（CWD ではなくファイル位置からプロジェクトルートを探索）。
   - 自動ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 代表的な環境変数（README 例）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     # KABU_API_BASE_URL は省略可（デフォルト: http://localhost:18080/kabusapi）
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development    # or paper_trading / live
     LOG_LEVEL=INFO
     ```

## 使い方（基本例）

以下はよく使われるワークフローの例です。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイル DB の場合は親ディレクトリを自動作成
```

2) J-Quants から日足データを取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# 取得（id_token を省略すると内部でキャッシュ／自動リフレッシュされる）
records = fetch_daily_quotes(code="7203")  # 銘柄コードを指定（省略で全銘柄）

# 保存（冪等）
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

3) 財務データやマーケットカレンダーも同様に fetch_*/save_* を使用してください。
- fetch_financial_statements / save_financial_statements
- fetch_market_calendar / save_market_calendar

4) データ品質チェック
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)  # target_date を指定するとその日のみチェック
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
    for row in issue.rows:
        print(row)
```

5) 監査ログテーブルの初期化（既存 conn に追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

その他の補足:
- トークン取得（明示的に行いたい場合）:
  ```python
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を利用
  ```
- J-Quants クライアントは内部で:
  - 120 req/min のレート制限をスロットリングで守る
  - HTTP 408/429/5xx に対して指数バックオフで最大 3 回リトライ
  - 401 を受けた場合トークンを自動リフレッシュして 1 回リトライ

## 環境変数一覧（主なもの）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動ロードを無効化

## ディレクトリ構成
（リポジトリ内の主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                        -- 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py              -- J-Quants API クライアント + DuckDB 保存
      - schema.py                      -- DuckDB スキーマ定義・初期化
      - audit.py                       -- 監査ログ（signal/order/execution）スキーマ
      - quality.py                     -- データ品質チェック
      - (raw modules: news, executions 定義等)
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

上記以外にも将来的に strategy（戦略実装）や execution（発注実装）、monitoring（監視・通知）用のコードを追加する想定です。

## 注意事項 / ベストプラクティス
- 本コードはデータ基盤・ユーティリティを提供するものであり、実際の売買ロジック・マネジメントは別途慎重に実装してください。特に live 運用時はリスク管理・二重発注防止・監査ログの利用を徹底してください。
- DuckDB のファイルはプロジェクトのバックアップ or 運用バックアップ戦略を用意してください。監査テーブルは削除しない前提のため、永続化設計を検討してください。
- API トークンや機密情報は .env/.env.local で管理し、リポジトリにコミットしないでください。
- テスト環境で .env 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD をセットしてください。

---

その他、README に追加したい操作例や CI / デプロイ手順、単体テストの実行方法などがあれば教えてください。必要に応じてサンプルスクリプトや .env.example を作成します。