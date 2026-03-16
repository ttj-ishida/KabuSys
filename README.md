# KabuSys

日本株向け自動売買基盤のコアライブラリ（実験的実装）

このリポジトリは、J-Quants API と kabuステーション API を利用して
データ取得（ETL）→ 特徴量生成 → シグナル生成 → 発注／監査までを想定した
モジュール群のコア部分を実装したものです。データ基盤（DuckDB）を中心に、
品質チェック・差分取得・監査ログなどの仕組みを含みます。

主な用途
- J-Quants からの株価・財務・市場カレンダー取得
- DuckDB に対するスキーマ定義・初期化
- 日次 ETL パイプライン（差分取得／バックフィル／品質チェック）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）初期化

要件
- Python 3.10+
- duckdb
- （運用時）J-Quants のリフレッシュトークン等の環境変数

機能一覧
- data/jquants_client.py
  - J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
  - 株価日足 / 財務（四半期）/ 市場カレンダー取得
  - DuckDB へ冪等（ON CONFLICT DO UPDATE）で保存するユーティリティ
- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - DB 初期化用関数 init_schema(), get_connection()
- data/pipeline.py
  - 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
  - run_daily_etl() により市場カレンダー→株価→財務→品質チェックを実行
- data/quality.py
  - 欠損、スパイク、重複、日付不整合等の品質チェック
  - QualityIssue オブジェクトで検出結果を返す
- data/audit.py
  - 監査ログ（signal_events / order_requests / executions）の DDL と初期化
- config.py
  - .env 自動読み込み（プロジェクトルート自動検出）
  - 必須環境変数の取り扱い・簡易設定ラッパー（settings）

セットアップ手順

1. Python 環境を作成（推奨: venv）
   - Python 3.10 以上を使用してください。

   例:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 依存パッケージをインストール
   - 最低限 duckdb が必要です。その他の運用依存（例: slack-sdk 等）はプロジェクト拡張時に追加してください。

   例:
   ```
   pip install duckdb
   ```

   もしパッケージ化されている場合:
   ```
   pip install -e .
   ```

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に配置した .env または .env.local が自動で読み込まれます。
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須（実行に必要な値）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API のパスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   任意:
   - KABUSYS_ENV (development | paper_trading | live) 既定: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) 既定: INFO
   - KABU_API_BASE_URL 既定: http://localhost:18080/kabusapi
   - DUCKDB_PATH 既定: data/kabusys.duckdb
   - SQLITE_PATH 既定: data/monitoring.db

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

使い方（代表的な操作例）

- DuckDB スキーマ初期化（最初に一度だけ実行）
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  # 以降 conn を使って ETL やクエリを実行
  ```

- 監査ログテーブルの初期化（既存接続に追加）
  ```python
  from kabusys.data import audit
  audit.init_audit_schema(conn)
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
  ```python
  from datetime import date
  from kabusys.data import pipeline, schema

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

  run_daily_etl は内部で:
  - 市場カレンダーを lookahead で取得
  - 取得したカレンダーで対象日を営業日に調整
  - 差分更新（最後に取得していない日を自動検出）＋ backfill（デフォルト: 3 日）
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- J-Quants の低レベル API 呼び出し（例: 日足取得）
  ```python
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
  # 保存
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  jq.save_daily_quotes(conn, records)
  ```

設計上のポイント（運用時に重要な点）
- API レート制御: J-Quants の制限（120 req/min）に合わせてモジュール内でスロットリングを行います。
- リトライ: ネットワークエラーや 408/429/5xx に対する指数バックオフ付きリトライを実装しています。401 は自動でリフレッシュして 1 回だけリトライします。
- 冪等性: DuckDB への保存は ON CONFLICT DO UPDATE を利用して重複を排除する実装です。
- 監査: シグナル→発注→約定のトレーサビリティを UUID ベースで保つ監査ログを用意しています。
- 品質チェックは Fail-Fast とせず、すべてのチェックを実行して問題の一覧を返し、呼び出し側で判断できるようにしています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py               : 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py     : J-Quants API クライアント（取得 + 保存）
    - schema.py             : DuckDB スキーマ定義・初期化
    - pipeline.py           : ETL パイプライン（差分更新・品質チェック）
    - quality.py            : データ品質チェック
    - audit.py              : 監査ログテーブル定義・初期化
  - strategy/
    - __init__.py           : 戦略関連モジュールを置く場所（未実装）
  - execution/
    - __init__.py           : 発注/約定関連モジュールを置く場所（未実装）
  - monitoring/
    - __init__.py           : モニタリング関連（未実装）

テストとデバッグ
- データベースに対するテストは DuckDB の ":memory:" を用いて行えます。
- 自動 .env 読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテスト等で便利です）。

拡張・運用のヒント
- Slack 通知や実際の発注ロジック（kabu API 呼び出し）は execution/ 配下や monitoring/ に実装してください。
- デプロイ環境では KABUSYS_ENV を正しく設定して（paper_trading / live）安全な運用を行ってください。
- DuckDB のファイルは定期バックアップやローテーション（アーカイブ）を検討してください。監査ログは削除しない前提で設計されています。

ライセンス / 貢献
- 本 README 内では明示していません。プロジェクトに LICENSE ファイルを追加して運用してください。
- バグレポートや機能追加は Pull Request を歓迎します。まず issue を立ててください。

以上が本コードベースの概要と基本的な使い方です。追加で README に入れたい内容（例: 実行スクリプト、CI 設定、依存リストなど）があれば教えてください。