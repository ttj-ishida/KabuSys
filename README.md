# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買プラットフォーム向けに設計された軽量ライブラリです。J-Quants API からの市場データ取得、DuckDB によるデータ格納（スキーマ定義含む）、ETL パイプライン、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）を備えています。

主な用途:
- 市場データの差分取得・永続化（株価日足、財務データ、JPX カレンダー）
- ETL 実行（差分更新・バックフィル）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ用スキーマの初期化

---

## 機能一覧

- J-Quants API クライアント（jquants_client）
  - 株価日足（OHLCV）、財務四半期データ、JPX マーケットカレンダーをページネーション対応で取得
  - レート制限（120 req/min）対応、リトライ（指数バックオフ、401 時のトークン自動リフレッシュ）
  - データ取得時の fetched_at（UTC）記録
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義と冪等な初期化関数（init_schema / get_connection）

- ETL パイプライン（data.pipeline）
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 差分取得（最終取得日からの差分 + backfill）
  - 品質チェック（quality モジュール）との統合

- データ品質チェック（data.quality）
  - 欠損（OHLC 欄）、スパイク（前日比閾値）、主キー重複、日付不整合（未来日／非営業日）

- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等の監査用テーブル
  - 発注フローの UUID 連鎖による完全トレーサビリティ
  - init_audit_schema / init_audit_db を提供

- 環境設定管理（config）
  - .env / .env.local をプロジェクトルートから自動ロード（必要に応じて無効化可）
  - 必須環境変数のラッパー（settings）

---

## セットアップ手順

1. Python 環境（推奨: venv）を用意
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate   # Unix/macOS
     .\.venv\Scripts\activate    # Windows
     ```

2. 依存パッケージをインストール
   - 必要な外部依存は duckdb のみです:
     ```
     pip install duckdb
     ```
   - パッケージをローカル開発用にインストールする場合:
     ```
     pip install -e .
     ```
     （pyproject/setup.py がある前提です。無ければ上の duckdb のみで実行できます）

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 最低限設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
     - SLACK_BOT_TOKEN: 通知用 Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
   - その他（任意/デフォルトあり）:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（簡単な例）

以下は最小限のサンプルコードです。DuckDB スキーマを初期化して日次 ETL を実行します。

- スキーマ初期化と日次 ETL 実行（Python スクリプト例）:
  ```python
  from datetime import date
  from pathlib import Path
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  db_path = Path("data/kabusys.duckdb")
  conn = init_schema(db_path)  # テーブルを作成して接続を返す

  # 今日の ETL を実行
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 監査ログスキーマを追加したい場合:
  ```python
  from kabusys.data.audit import init_audit_schema
  # conn は init_schema() で取得した接続
  init_audit_schema(conn)
  ```

- J-Quants から生データを直接取得したい場合:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  # トークンは settings から自動取得されますが、明示的に渡すことも可能
  token = get_id_token()
  rows = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))
  ```

- 品質チェックを個別に実行:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  ```

注記:
- J-Quants API は 120 req/min の制限があるため、jquants_client は内部でスロットリングとリトライを行います。
- 取得データの fetched_at は UTC タイムスタンプで保存され、Look-ahead Bias 防止のため「いつそのデータが得られたか」を追跡できます。

---

## 環境変数一覧（重要）

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（取得に必要）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化する際に `1` を設定

settings オブジェクト経由でアクセスできます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## ディレクトリ構成

主要ファイル・モジュール一覧（src/kabusys 以下）:

- kabusys/
  - __init__.py  （パッケージ定義、バージョン: 0.1.0）
  - config.py    （環境変数・設定管理、自動 .env 読み込み）
  - data/
    - __init__.py
    - jquants_client.py   （J-Quants API クライアント、取得/保存ロジック）
    - schema.py          （DuckDB スキーマ定義・初期化）
    - pipeline.py        （ETL パイプライン / run_daily_etl 等）
    - audit.py           （監査ログ用スキーマ / init_audit_schema）
    - quality.py         （データ品質チェック）
  - strategy/
    - __init__.py        （戦略関連のエントリポイント（拡張箇所））
  - execution/
    - __init__.py        （発注・実行関連（拡張箇所））
  - monitoring/
    - __init__.py        （監視・メトリクス用（拡張箇所））

補足:
- データ層は Raw / Processed / Feature / Execution の 3 層（+監査）構造を想定して設計されています。
- strategy、execution、monitoring は拡張ポイントとして空の __init__.py が置かれています（将来的に戦略やブローカー連携を実装）。

---

## 実運用上の注意・設計ポイント

- レート制限厳守: jquants_client は固定間隔スロットリング（120 req/min）を実装しています。大量データ取得時は待ち時間が発生します。
- リトライとトークン自動更新: HTTP 408/429/5xx は最大 3 回の指数バックオフリトライ、401 受信時はリフレッシュトークンを使って ID トークンを再取得して再試行します。
- 冪等性: DuckDB に対する INSERT は ON CONFLICT DO UPDATE を使用して重複・上書きに対応します。
- 品質チェックは Fail-Fast ではなく全問題を収集する方針です。ETL 自体は個別ステップが失敗しても可能な限り継続し、呼び出し元が結果を見て判断します。
- 監査ログは削除しない前提で設計されており、すべての TIMESTAMP は UTC で保存します。

---

もし README に追加したい「動作確認手順」「CI 設定」「外部ブローカー連携の実装例」などがあれば、あなたの利用シナリオに合わせて追記します。