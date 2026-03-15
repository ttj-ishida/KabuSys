# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得（J‑Quants）、DuckDBスキーマ管理、監査ログ（トレーサビリティ）など、取引戦略の構築・実行に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリ群です。

- J‑Quants API からの市場データ（OHLCV、財務諸表、JPX カレンダー）の取得
- DuckDB による階層的なデータスキーマ（Raw / Processed / Feature / Execution）の初期化と永続化
- 発注・約定までの監査ログ（UUID 連鎖）によるトレーサビリティ管理
- 環境変数ベースの設定管理（.env 自動読み込み / 保護）
- レート制御・リトライ・トークン自動リフレッシュ等を備えた堅牢な API クライアント

設計上のポイント:
- J‑Quants のレート制限（120 req/min）に準拠するスロットリング
- 401 時の自動トークンリフレッシュ（1回まで）と指数バックオフ付きリトライ（最大3回）
- データ取得時の fetched_at を UTC で記録し、Look‑ahead Bias を防止
- DuckDB への INSERT は ON CONFLICT DO UPDATE により冪等性を確保

---

## 主な機能一覧

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）
  - 必須環境変数の取得ラッパー（settings オブジェクト）
- J‑Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（fetch_daily_quotes）
  - 財務データ（fetch_financial_statements）
  - JPX マーケットカレンダー（fetch_market_calendar）
  - レートリミッタ、リトライ、ID トークン取得（get_id_token）
  - DuckDB へ保存するユーティリティ（save_daily_quotes など）
- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - init_schema(db_path)：全テーブル・インデックスの作成（冪等）
  - get_connection(db_path)：既存DBへの接続
- 監査ログ（src/kabusys/data/audit.py）
  - init_audit_schema(conn)：監査テーブルを既存接続に追加
  - init_audit_db(db_path)：監査用 DB を新規作成して初期化
- パッケージ構成の骨組み（strategy / execution / monitoring パッケージ置き場）

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションに union 型（X | None）等を使用）
- git

推奨手順（例）:

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール
   最小: duckdb（その他は標準ライブラリを利用）
   ```
   pip install duckdb
   ```
   パッケージとして使う場合（プロジェクトルートに setuptools/pyproject がある想定）:
   ```
   pip install -e .
   ```

4. 環境変数を用意
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化されます）。必要な環境変数は下記参照。

---

## 必要な環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — environment: "development"（デフォルト） / "paper_trading" / "live"
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に "1" を設定
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

例 (.env):
```
JQUANTS_REFRESH_TOKEN="xxxx"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
KABUSYS_ENV=development
```

---

## 使い方（簡単なコード例）

- settings を利用する
```python
from kabusys.config import settings

print(settings.env)          # development / paper_trading / live
print(settings.duckdb_path)  # デフォルト path
```

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# 以降 conn を使ってデータ処理を実行
```

- J‑Quants から日足を取得して保存
```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(code="7203", date_from=date(2023, 1, 1), date_to=date(2023, 12, 31))
count = save_daily_quotes(conn, records)
print(f"保存件数: {count}")
```

- 財務データ / マーケットカレンダー取得
```python
from kabusys.data.jquants_client import fetch_financial_statements, fetch_market_calendar

fin = fetch_financial_statements(code="7203")
cal = fetch_market_calendar()
```

- 監査ログ（audit）スキーマ初期化（既存接続へ追加）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

- 監査専用 DB を分けて使う場合
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意点:
- fetch_* 系はページネーションに対応し、取得した各レコードの fetched_at（UTC）情報を保存する設計になっています（save_* が付与）。
- jquants_client は内部でレートリミッタ／リトライ／トークン自動リフレッシュを行います。アプリではこれらの仕様を前提に並列アクセスや呼び出し頻度を調整してください。

---

## ディレクトリ構成

（プロジェクトの src 配下を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                     # 環境変数・設定管理
    - execution/                     # 発注・実行関連（未実装のプレースホルダ）
      - __init__.py
    - strategy/                      # 戦略ロジック（プレースホルダ）
      - __init__.py
    - monitoring/                    # 監視・メトリクス（プレースホルダ）
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py            # J‑Quants API クライアント（取得・保存処理）
      - schema.py                    # DuckDB スキーマ定義・初期化
      - audit.py                     # 監査ログ（注文→約定のトレーサビリティスキーマ）

主要ファイルの役割:
- config.py: .env 自動読み込み（プロジェクトルートを検出）・settings オブジェクト
- data/jquants_client.py: HTTP リトライ・レート制御・ID トークンの管理、DuckDB 保存ユーティリティ
- data/schema.py: 全テーブルの DDL・インデックス定義・init_schema 実装（冪等）
- data/audit.py: 監査用テーブルの DDL・インデックス定義・初期化関数

---

## 実運用上の注意

- レート制限: J‑Quants の上限（120 req/min）に合わせた固定間隔のスロットリングを実装しています。高頻度での並列リクエストは避けてください。
- トークンリフレッシュ: 401 を受けた場合、トークンを自動で再取得し1回だけリトライします。それでも失敗したら例外になります。
- 時刻管理: データの取得時刻・監査ログは UTC で保存します。DB 初期化時や保存時の時刻は UTC に基づきます。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行います。テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB へは ON CONFLICT DO UPDATE を使って冪等に保存します。データの二重投入・差分更新を考慮した設計です。

---

## 今後の拡張案（参考）
- strategy / execution モジュールに戦略エンジン・発注フロー実装
- Slack 通知・監視エンドポイントの実装（monitoring）
- 単体テスト・CI の整備
- 複数データソース（ニュース、代替データ）の統合

---

ご不明点や README に追記してほしい項目があれば教えてください。README をプロジェクトの実態や運用手順に合わせてカスタマイズします。