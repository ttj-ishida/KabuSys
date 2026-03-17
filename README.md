# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
J-Quants / kabuステーション 等の外部サービスからデータを取得・永続化し、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログなど自動売買に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- 環境変数 / .env を利用した設定管理（自動ロード機能付き）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レートリミット制御、リトライ、トークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録（Look-ahead Bias 対策）
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）
- ニュース収集（RSS）
  - URL 正規化、トラッキングパラメータ削除、SSRF 対策、gzip 上限チェック
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - raw_news / news_symbols への冪等保存（INSERT ... RETURNING 使用）
  - テキストからの銘柄コード抽出（既知銘柄リストでフィルタ）
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit）
- ETL パイプライン
  - 差分更新（最終取得日からの差分、バックフィル対応）
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- データ品質モジュール（QualityIssue を返す設計で Fail-Fast しない）

---

## 前提条件

- Python 3.10 以上（| 型注釈などを使用）
- 必須パッケージ（最低限）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS）

パッケージ化や開発環境での利用は、pyproject / requirements を別途用意する想定です。

---

## セットアップ

1. リポジトリをクローン／取得し、開発環境を用意する:
   - 仮想環境を作成し有効化（例: python -m venv .venv）
   - 必要パッケージをインストール:
     pip install duckdb defusedxml

   （プロジェクトに requirements ファイルがあればそこからインストールしてください）

2. 環境変数を用意する:
   - プロジェクトルートの `.env` または `.env.local` に設定を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

3. 最低限必須の環境変数（Settings クラス参照）:
   - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID — Slack 送信先チャンネルID（必須）
   - （省略時のデフォルト）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1（で自動ロード無効）
   - データベースパス（省略可）
     - DUCKDB_PATH（例: data/kabusys.duckdb デフォルト）
     - SQLITE_PATH（monitoring 用、デフォルト: data/monitoring.db）

4. 例: `.env`（最低限の例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_api_password_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要 API と例）

以下は Python REPL やスクリプトから呼び出す例です。

- DuckDB スキーマの初期化（最初に一度だけ実行）
  ```py
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)  # DB ファイル作成・スキーマ作成
  ```

- 日次 ETL 実行
  ```py
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")  # 既存 DB に接続
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

  run_daily_etl は内部で:
  - market calendar を先読み
  - 株価（差分）取得・保存
  - 財務データ（差分）取得・保存
  - 品質チェック（オプション）

- ニュース収集ジョブの実行
  ```py
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # sources = {"yahoo": "https://..."} を渡すかデフォルトを使用
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  ```

- カレンダー更新ジョブ（夜間バッチ向け）
  ```py
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved calendar rows:", saved)
  ```

- 監査スキーマの初期化（audit テーブルを追加）
  ```py
  from kabusys.data.audit import init_audit_schema
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  init_audit_schema(conn)
  ```

- J-Quants のトークンを直接取得する
  ```py
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

---

## 実行時ヒント / 運用

- 自動ロードされた .env はプロジェクトルート（.git または pyproject.toml を起点）から読み込まれます。CI やテストで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants のレート制限（120 req/min）に合わせた内部制御が組み込まれています。大量データ取得時は注意してください。
- ETL は部分的失敗しても他ステップを継続する設計です。戻り値 ETLResult の errors や quality_issues を監視・通知して運用判断を行ってください。
- DuckDB はファイルベースで軽量な分析 DB として使えます。初期化時に親ディレクトリがなければ自動作成されます。
- RSS 取得では SSRF / Gzip Bomb / XML 攻撃対策を行っていますが、外部ソースの挙動次第で例外が発生します。ログをよく確認してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数と設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py — RSS からのニュース収集・保存・銘柄紐付け
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - audit.py — 監査ログ（signal/events/order_requests/executions）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - schema.py — DuckDB スキーマ定義と初期化
  - strategy/ — 戦略関連（パッケージ骨格）
  - execution/ — 発注・実行関連（パッケージ骨格）
  - monitoring/ — 監視関連（パッケージ骨格）

---

## ロギング / 環境切替

- KABUSYS_ENV: development / paper_trading / live（settings.env）
  - settings.is_dev / is_paper / is_live で振る舞いを切替可能
- LOG_LEVEL 環境変数でログレベルを指定可能（デフォルト INFO）

---

## テスト / 開発

- 単体テスト・統合テストを行う際は、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境の注入を明示的に行うと再現性が高まります。
- jquants_client のネットワーク呼び出しはモックしやすいように id_token を注入する設計です（テストで get_id_token をモックするなど）。

---

## ライセンス・貢献

この README はコードベースから自動生成された概要ドキュメントに基づき作成しています。実プロジェクトに適用する際は LICENSE、CONTRIBUTING、セキュリティポリシー等を追加してください。

---

必要ならば README に含めるコマンド例（systemd/cron ジョブ、Dockerfile、CI 設定例）や .env.example を作成して追記します。どの形式で追記しますか？