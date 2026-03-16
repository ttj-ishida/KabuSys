# KabuSys — 日本株自動売買システム

日本株のデータ収集・品質管理・監査ログ・発注基盤の基礎を提供するライブラリ群です。  
J-Quants API や kabuステーション（発注）と連携するためのクライアント、DuckDB ベースのスキーマ定義、データ品質チェック、監査（トレーサビリティ）機能などを含みます。

---

## 主な概要

- データ収集（J-Quants API）から DB 保存までの ETL 基盤
- DuckDB を用いた多層（Raw / Processed / Feature / Execution）スキーマ
- 監査ログ（シグナル→発注→約定の連鎖）を保存する監査テーブル群
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 環境変数管理（.env / .env.local の自動読み込み、必要設定の抽象化）
- 発注・戦略・監視のためのパッケージ構成（strategy / execution / monitoring：拡張ポイント）

---

## 機能一覧

- 環境設定
  - .env / .env.local をプロジェクトルートから自動読み込み（CWDに依存しない）
  - 必須値は Settings クラス経由で取得（未設定時に例外を投げる）
  - 自動読み込みを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - サポートする環境: `development`, `paper_trading`, `live`

- J-Quants クライアント（data.jquants_client）
  - ID トークン自動リフレッシュ
  - ページネーション対応で日足・財務・カレンダーを取得
  - API レート制御（120 req/min）とリトライ（指数バックオフ、401時の1回自動リフレッシュ）
  - データ取得時の fetched_at を UTC で記録
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）

- DuckDB スキーマ（data.schema）
  - Raw / Processed / Feature / Execution のテーブル群
  - インデックス定義、外部キー制約、型チェック、制約付き DDL
  - init_schema() による初期化と get_connection()

- 監査ログ（data.audit）
  - signal_events / order_requests / executions の DDL とインデックス
  - order_request_id を冪等キーとして二重発注防止
  - UTC タイムスタンプ、削除制限（ON DELETE RESTRICT）

- データ品質（data.quality）
  - 欠損データ検出（OHLC 欄）
  - スパイク検出（前日比 ±X%）
  - 重複チェック（主キー重複）
  - 日付不整合チェック（未来日付、非営業日）
  - 各チェックは QualityIssue のリストを返す（ログと判定は呼び出し側で対応）

---

## 要件

- Python 3.10+
- 依存ライブラリ（例）
  - duckdb
- ネットワークアクセス（J-Quants API 等）

※ 実際のセットアップにはプロジェクトの pyproject.toml / requirements を参照してください（本コードには依存定義ファイルは含まれていません）。

---

## セットアップ手順（ローカル開発向けの例）

1. リポジトリをクローンしてワークディレクトリへ移動

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を置くと自動的に読み込まれます。
   - 必須環境変数（アプリケーション動作に必須）：
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト値あり：
     - KABUSYS_ENV (default: development) 値: development, paper_trading, live
     - LOG_LEVEL (default: INFO)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（よく使う API 例）

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  ```

- 監査スキーマを既存接続に追加
  ```python
  from kabusys.data import audit
  audit.init_audit_schema(conn)
  ```

- J-Quants の ID トークン取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使う
  ```

- 日足取得して DuckDB に保存（例）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data import schema

  conn = schema.init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
  saved = save_daily_quotes(conn, records)
  print(f"保存件数: {saved}")
  ```

- 品質チェックの実行
  ```python
  from kabusys.data import quality
  issues = quality.run_all_checks(conn, target_date=None)
  for issue in issues:
      print(issue.check_name, issue.severity, issue.detail)
  ```

- 簡単な注意点
  - fetch_* 関数はページネーション対応で内部的にトークンを共有します。
  - API レート制限とリトライ処理は組み込まれていますが、運用時はさらに外部制御を検討してください。
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）を意図しています。

---

## ディレクトリ構成

プロジェクトの主要ファイル・モジュールは以下の通りです（src/kabusys 配下）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数・設定管理（.env 自動読み込み、Settings）
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（取得・保存ロジック）
      - schema.py                    — DuckDB スキーマ定義 & init_schema / get_connection
      - audit.py                     — 監査ログスキーマ（signal / order_request / executions）
      - quality.py                   — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - strategy/
      - __init__.py                   — 戦略ロジックの拡張ポイント（未実装）
    - execution/
      - __init__.py                   — 発注/ブローカー連携の拡張ポイント（未実装）
    - monitoring/
      - __init__.py                   — モニタリング機能の拡張ポイント（未実装）

---

## 運用上のポイント / ベストプラクティス

- 環境の切り替えは KABUSYS_ENV で行う（development / paper_trading / live）。
  - live を有効にする際は特に環境変数やパスワード管理に注意すること。
- DuckDB ファイルはバックアップ・バージョニングを推奨（データの大破防止）。
- 監査ログは削除しない前提の設計（履歴保存）。更新時は updated_at を明示的にセットすること。
- データ品質チェックは ETL パイプラインに組み込み、重要度に応じて ETL 中断／通知を行うこと。
- 実運用発注系との接続は事前に paper_trading 環境で十分に検証すること。

---

必要に応じて README にさらに以下を追加できます：
- 具体的なインストール用の requirements.txt / pyproject.toml の例
- CI / テスト実行手順
- 実運用向けの運用手順（Slack 通知、エラーハンドリング方針）
- strategy / execution / monitoring の拡張ガイド

追加したい項目があれば教えてください。