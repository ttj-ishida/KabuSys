# KabuSys

日本株自動売買プラットフォームのコアライブラリ（ライブラリ層 / バッチ処理向けユーティリティ群）。

このリポジトリはデータ収集（J-Quants, RSS）、DuckDB スキーマ定義、ETL パイプライン、データ品質チェック、マーケットカレンダー管理、ニュース収集、監査ログ（発注 → 約定 のトレーサビリティ）など、システムの基盤機能を提供します。

---

## 主な特徴（機能一覧）

- 環境変数ベースの設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可）
  - 必須設定は明確に例外を投げる（Settings クラス）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レートリミット（120 req/min）遵守、指数バックオフ付きリトライ、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理・URL 正規化（utm 等削除）・SHA-256 ベースの記事 ID による冪等保存
  - SSRF 対策、gzip/サイズ上限（10MB）制御、XML セキュリティ（defusedxml）
  - 記事と銘柄コードの紐付け（news_symbols）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層を含む完全な DDL 定義
  - テーブルとインデックスの初期化関数（init_schema / get_connection）

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新とバックフィル対応、品質チェックの結果をまとめて返却
  - run_daily_etl により一括実行可能

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後の営業日検索、期間内営業日取得、夜間カレンダー更新ジョブ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions など監査用テーブル群
  - order_request_id を冪等キーとして二重発注防止、すべて UTC で保存

- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合などを検出して QualityIssue を返す

---

## 動作環境 / 依存関係

- Python 3.10 以上（型注釈に | 記法を使用）
- 主な Python パッケージ:
  - duckdb
  - defusedxml
- （プロジェクトの packaging/requirements.txt があればそちらを使用してください）

例（仮想環境作成とパッケージインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはプロジェクトの requirements.txt があれば:
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo-directory>
   ```

2. Python 仮想環境を作成し依存関係をインストール（上記参照）

3. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を作成すると、自動的に読み込まれます（優先順位: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用など）。
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack ボットトークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
   - オプション:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite モニタリング DB（デフォルト: data/monitoring.db）

   例 `.env` の一部:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから次を実行して DB とテーブルを作成します:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成してテーブル初期化
   ```

5. 監査テーブル初期化（任意）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.audit import init_audit_schema

   conn = init_schema("data/kabusys.duckdb")
   init_audit_schema(conn)  # 監査ログテーブルを追加
   ```

---

## 使い方（主要なAPIと例）

- settings（設定取得）
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- DuckDB スキーマ初期化 / 接続取得
  ```python
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")  # 初期化して接続を返す
  # 既存 DB に接続するだけなら:
  conn2 = get_connection("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集（RSS）を実行して保存
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "8306"}  # 有効な銘柄コードセット（例）
  results = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  ```

- マーケットカレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved: {saved}")
  ```

- J-Quants トークン取得（必要に応じて）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使う
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=None, reference_date=date.today(), spike_threshold=0.5)
  for i in issues:
      print(i)
  ```

---

## 実行上の注意点 / 設計上のポイント

- J-Quants API はレート制限（120 req/min）があります。本クライアントは内部で RateLimiter を使い自動スロットリングしますが、大量の並列リクエストは避けてください。
- API へのリクエストはリトライ（指数バックオフ）を行います。401 エラー時は自動でリフレッシュを試行します（1回）。
- ニュース収集では SSRF、XML bomb、gzip bomb を軽減するためにさまざまな保護（スキーム検証、プライベートIP拒否、受信上限、defusedxml）を実装しています。
- DuckDB への保存は冪等性を意識しています（ON CONFLICT DO UPDATE / DO NOTHING を多用）。
- 日次 ETL は可能な限り失敗を局所化します（あるステップが失敗しても他のステップは継続し、結果にエラー情報を格納します）。
- 環境変数はプロジェクトルートの .env / .env.local から自動で読み込まれます。OS 環境変数は上書きされません（.env.local は上書き可能）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（取得・保存）
      - news_collector.py            — RSS ニュース収集・保存・銘柄抽出
      - schema.py                    — DuckDB スキーマ定義 & init_schema / get_connection
      - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py       — マーケットカレンダー管理
      - audit.py                     — 監査ログ（signal/order/execution）スキーマ初期化
      - quality.py                   — データ品質チェック
    - strategy/
      - __init__.py                  — 戦略層 placeholder（実装は別途）
    - execution/
      - __init__.py                  — 発注 / 約定関連 placeholder
    - monitoring/
      - __init__.py                  — モニタリング関連 placeholder

各モジュールの詳細はソースコード内の docstring に設計方針や利用法が書かれています。まずは data.schema.init_schema で DB を用意し、data.pipeline.run_daily_etl / data.news_collector.run_news_collection などを順に試してください。

---

## 典型的なワークフロー（例）

1. .env を作成して必要なシークレットを設定
2. init_schema で DuckDB を初期化
3. calendar_update_job でカレンダーを先読み
4. run_daily_etl で株価・財務を差分取得して保存
5. run_news_collection でニュースを収集し銘柄紐付け
6. run_all_checks で品質チェックを実施し、問題があればアラート/手動調査

---

## サポート / 開発メモ

- テスト時に自動 .env の読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB を ":memory:" に指定することでインメモリ DB を使った単体テストが可能です。
- ロギングは標準ライブラリ logging を使用しています。LOG_LEVEL 環境変数で調整してください。

---

ご質問や利用上の具体的なユースケース（例：どのように戦略層と結びつけるか、リアルタイム発注フローの実装方法など）があれば、その用途に合わせたサンプルや追加のドキュメントを作成します。