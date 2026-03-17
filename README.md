# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants など外部データソースから市場データや財務データを取得し、DuckDB に保存・管理するための ETL、ニュース収集、品質チェック、監査ログ（発注〜約定のトレーサビリティ）機能を提供します。

この README ではプロジェクト概要、主な機能、セットアップ手順、使い方（簡単なコード例）およびディレクトリ構成を解説します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含みます。

- J-Quants API を介した市場データ（株価日足、四半期財務、マーケットカレンダー）の取得と保存
- RSS ベースのニュース収集と記事→銘柄の紐付け
- DuckDB を用いたデータスキーマ定義・初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 環境変数ベースの設定読み込み（.env の自動読み込み対応）

設計では「冪等性」「Look-ahead バイアス回避（fetched_at の記録）」「API レート制御とリトライ」「SSRF 等のネットワークセキュリティ対策」を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（レートリミット、リトライ、401 自動リフレッシュ、ページネーション対応）
  - fetch/save（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_*）
- data/news_collector.py
  - RSS フィード収集、URL 正規化、記事ID（SHA-256 先頭 32 文字）生成、SSRF 対策、gzip 上限チェック、DuckDB への冪等保存
  - 銘柄コード抽出（4桁コード）と news_symbols テーブルへの紐付け
- data/schema.py
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）と初期化 API（init_schema, get_connection）
- data/pipeline.py
  - 日次 ETL 実装（差分更新、バックフィル、カレンダー先読み、品質チェック）
  - run_daily_etl により一括で ETL を実行し ETLResult を返す
- data/quality.py
  - 欠損、スパイク、重複、日付不整合チェック
  - run_all_checks でまとめて実行可能
- data/audit.py
  - 監査ログ（signal_events, order_requests, executions）スキーマ初期化（init_audit_schema / init_audit_db）
- config.py
  - .env 自動読み込み（プロジェクトルート検出）と Settings クラス経由の環境変数アクセサ
  - 必須環境変数の検査（JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能

---

## 動作環境 / 依存

- 要件
  - Python 3.10 以上（`|` 型や代数的型注記を利用）
- 主な依存パッケージ
  - duckdb
  - defusedxml

（ネットワーク操作は標準ライブラリ urllib を使用しています。必要に応じて slack 等の外部ライブラリを追加してください）

例（pip）:
```
pip install duckdb defusedxml
```

プロジェクトをパッケージとしてインストールする場合（repo 内に setup/pyproject がある前提）:
```
pip install -e .
```

---

## 環境変数（.env）

プロジェクトは .env（および .env.local）から自動で設定を読み込みます（プロジェクトルートに .git または pyproject.toml がある場合）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な設定項目（最低限必要なもの）:

- JQUANTS_REFRESH_TOKEN ・・・ J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD       ・・・ kabuステーション API パスワード（必須）
- KABU_API_BASE_URL       ・・・ kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN         ・・・ Slack Bot Token（必須）
- SLACK_CHANNEL_ID        ・・・ Slack Channel ID（必須）
- DUCKDB_PATH             ・・・ DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH             ・・・ 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV             ・・・ 環境: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL               ・・・ ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

例 (.env):
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

## セットアップ手順（簡易）

1. Python 3.10+ を用意
2. 依存ライブラリをインストール:
   ```
   pip install duckdb defusedxml
   ```
3. .env を作成（上記を参照）
4. データベース初期化（DuckDB スキーマ作成）

   例: Python REPL またはスクリプトで:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```
   監査ログテーブルを追加する場合:
   ```python
   from kabusys.data import audit
   audit.init_audit_schema(conn)
   ```

---

## 使い方（主要 API の例）

以下は基本的な操作例です。実際はログ設定やエラーハンドリングを組み込んでください。

- DuckDB スキーマ初期化（上記参照）

- 日次 ETL の実行
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を省略すると今日が対象
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758"}  # 例: 有効な銘柄コードセット（抽出時に利用）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)  # {source_name: saved_count}
  ```

- J-Quants の個別フェッチ（テストや一括取得に）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  token = get_id_token()  # settings.jquants_refresh_token を使って取得
  records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  ```

- 品質チェックを個別に実行
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

- 設定参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  print(settings.env)  # development | paper_trading | live
  ```

---

## 注意点 / 運用上のヒント

- J-Quants API のレート制限（120 req/min）を厳守するよう、クライアント側でスロットリングとリトライを行っています。大量データ取得の際は考慮してください。
- ETL は差分更新（最終取得日ベース）とバックフィル（デフォルト 3 日）を行い、API の後出し修正を吸収する設計です。
- news_collector は RSS のサイズ制限（デフォルト 10MB）や SSRF 対策を備えています。外部 URL の扱いには注意してください。
- DuckDB は単一ファイル DB です。データ量や同時接続数に応じた運用を検討してください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）をベースに行います。テスト時などに自動ロードを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- KABUSYS_ENV の有効値は `development`, `paper_trading`, `live` です。live 実行では特に発注・監査系の取り扱いに注意してください。

---

## ディレクトリ構成

主要ファイル/モジュール（コードベースより抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save）
    - news_collector.py            — RSS ニュース収集と DB 保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - pipeline.py                  — ETL パイプライン（差分更新・品質チェック）
    - quality.py                   — データ品質チェック
    - audit.py                     — 監査ログスキーマ（signal/order/execution）
    - audit.py                     — 監査スキーマ初期化
  - strategy/
    - __init__.py                  — 戦略関連パッケージ（拡張ポイント）
  - execution/
    - __init__.py                  — 発注/ブローカ連携パッケージ（拡張ポイント）
  - monitoring/
    - __init__.py                  — 監視関連（拡張ポイント）

各モジュールは拡張しやすいように API を分離して実装されています。戦略や実行、監視はこの基盤上にプラグイン的に実装していく想定です。

---

## ライセンス / 貢献

（ここにはプロジェクトのライセンス情報や貢献方法を記載してください。リポジトリに LICENSE があればその内容を参照してください。）

---

README は以上です。必要ならセットアップ手順に CI / systemd / crontab を使った運用例や、より詳細な .env.example を追加したり、実際の SQL スキーマやサンプルデータを使ったデモ手順を追記できます。どの情報を追加したいか教えてください。