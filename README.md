# KabuSys

日本株向けの自動売買プラットフォーム基盤ライブラリです。  
データ取得（J-Quants API）、ETLパイプライン、データ品質チェック、DuckDBスキーマ、監査ログなど、取引戦略／実行層の基盤となる機能を提供します。

## 概要
- J-Quants API から価格・財務・マーケットカレンダーを取得して DuckDB に保存する ETL パイプラインを実装。
- データの冪等保存（ON CONFLICT DO UPDATE）、レート制御、リトライ、トークン自動更新をサポート。
- データ品質チェック（欠損・スパイク・重複・日付不整合）を実行可能。
- 監査ログ（シグナル→発注→約定のトレース）用スキーマが用意されている。
- 将来的に戦略・実行・モニタリング層と連携できるモジュール構成。

## 主な機能一覧
- 環境設定管理（.env 自動読込、必須設定の検証）: kabusys.config
- J-Quants API クライアント（取得、認証、ページネーション、レートリミット、リトライ）: kabusys.data.jquants_client
- DuckDB スキーマ定義・初期化: kabusys.data.schema
- ETL パイプライン（差分取得・バックフィル・品質チェック）: kabusys.data.pipeline
- データ品質チェック（欠損・スパイク・重複・日付不整合）: kabusys.data.quality
- 監査ログ（signal / order_request / execution テーブル）初期化: kabusys.data.audit

## セットアップ手順（開発環境）
※実行環境の構成に応じて適宜調整してください。

1. Python 仮想環境を作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell/CMD)
   ```

2. 必要パッケージをインストール  
   （プロジェクト配布方法により変わります。例: pip インストール）
   ```bash
   pip install duckdb
   # pip install -e .    # パッケージ化している場合はプロジェクトルートで実行
   ```
   - 本ライブラリは duckdb と標準ライブラリを利用しています。その他の依存は実行部分（Slack 通知や kabu API 連携等）に応じて追加してください。

3. 環境変数の準備  
   プロジェクトルートに `.env` と（必要なら）`.env.local` を配置できます。ライブラリは自動的にプロジェクトルート（.git または pyproject.toml を起点）を探索して以下の順で環境変数を読み込みます。
   - OS 環境変数（優先）
   - .env.local（存在すれば上書き）
   - .env

   自動ロードを無効にする場合:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

4. 必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - DUCKDB_PATH: デフォルトの DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（省略時: data/monitoring.db）
   - KABUSYS_ENV: 実行環境 (development | paper_trading | live)（省略時: development）
   - LOG_LEVEL: ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL）

   例 `.env`（最小例）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

## 使い方（簡単な例）

- 設定値を参照する
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- DuckDB スキーマの初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # データベースファイル作成 & 全テーブル作成
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務の差分取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # 引数で target_date, id_token などを渡せる
  print(result.to_dict())
  ```

- J-Quants から価格を直接取得
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes

  quotes = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
  ```

- 監査ログテーブルを追加で初期化
  ```python
  from kabusys.data.audit import init_audit_schema
  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn)  # 監査ログ用テーブルを追加作成
  ```

注意点:
- jquants_client は内部でレート制御（120 req/min）・リトライ（指数バックオフ）・401 の場合のトークン自動更新を行います。
- ETL はデフォルトでバックフィル（直近 N 日分の再取得）を行い API の後出し修正を吸収します。
- 品質チェックは問題を検出しても ETL を停止せず、呼び出し元が結果を見て対処する設計です。

## ディレクトリ構成
（主要ファイル・モジュールのみ）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読込・Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・認証・保存ユーティリティ）
    - schema.py
      - DuckDB の DDL 定義と初期化（Raw / Processed / Feature / Execution 層）
    - pipeline.py
      - ETL パイプライン（差分更新・バックフィル・品質チェック）
    - audit.py
      - 監査ログ（signal / order_request / execution）の DDL と初期化
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py
    - （戦略実装用のプレースホルダ）
  - execution/
    - __init__.py
    - （発注実装用のプレースホルダ）
  - monitoring/
    - __init__.py
    - （監視・メトリクス用のプレースホルダ）

その他:
- プロジェクトルートに `.env`, `.env.local`, pyproject.toml, README.md などを置く想定。

## 動作上の留意点
- .env のパースはシェル風のクォートやコメント（export KEY=val 対応）をある程度サポートしています。
- DuckDB スキーマの初期化は冪等（複数回実行しても安全）です。
- 全ての TIMESTAMP は UTC で扱う設計の箇所があります（監査ログ等）。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかでなければエラーになります。
- ライブラリは外部 API の利用や実際の発注を行うため、実運用ではシークレット管理（Vault 等）や安全なネットワーク設定が必要です。

---

この README はコードベースの主要機能と使い方を要約したものです。詳細な仕様や追加のドキュメント（DataPlatform.md, DataSchema.md 等）がプロジェクト内にある想定ですので、そちらも併せて参照してください。必要であれば（例：運用手順、CI/CD、監視フローなど）追記します。