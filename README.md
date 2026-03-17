# KabuSys

日本株向け自動売買基盤（ライブラリ）のリポジトリです。  
このリードミーではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株向けのデータ収集・ETL、データ品質チェック、ニュース収集、監査ログ（発注〜約定のトレーサビリティ）、および売買戦略／発注のための基盤機能を提供する Python ライブラリです。主に以下を目的としています。

- J-Quants API からの市場データ・財務データ・マーケットカレンダー取得
- RSS からのニュース収集と銘柄紐付け
- DuckDB による三層データレイヤ（Raw / Processed / Feature）と実行層のスキーマ定義・初期化
- 日次 ETL（差分取得・バックフィル・品質チェック）パイプライン
- 監査ログ用スキーマ（signal → order_request → executions の連鎖）
- SSRF・XML Bomb・大容量応答などを考慮した堅牢なネットワーク処理

設計上、API レート制限、リトライ、トークン自動更新、冪等性（ON CONFLICT）など現実運用に必要な配慮が組み込まれています。

---

## 主な機能一覧

- 環境設定管理（.env 自動読み込み、必須変数検査）
- J-Quants API クライアント
  - 日足（OHLCV）取得（ページネーション対応）
  - 財務（四半期 BS/PL）取得
  - マーケットカレンダー取得
  - リトライ、レートリミット、トークン自動リフレッシュ対応
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックスの自動作成
  - 監査ログ用スキーマ（audit）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- ニュース収集モジュール
  - RSS フィード収集、前処理（URL除去・空白正規化）
  - 記事IDは正規化URLの SHA-256 先頭32文字（冪等性）
  - SSRF 対策、XML セキュリティ、レスポンスサイズ制限
  - raw_news / news_symbols テーブルへの保存（チャンク、トランザクション、INSERT ... RETURNING）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day、夜間更新ジョブ）

---

## 要件（推奨）

- Python 3.10 以上（PEP 604 の型表記（|）を使用）
- pip 環境
- 主要依存パッケージ（例）:
  - duckdb
  - defusedxml

requirements.txt が用意されている場合はそちらを参照してください。なければ手動でインストールします。

---

## セットアップ手順

1. リポジトリをクローン（適宜置き換えてください）

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール

   例（最小）:

   ```
   pip install duckdb defusedxml
   ```

   実運用ではロギングや HTTP クライアントなど追加が必要になる可能性があります。

4. 環境変数を設定

   プロジェクトルートに `.env` または `.env.local` を作成して以下を設定してください（必須）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション等の API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

   オプション:
   - DUCKDB_PATH: データ保存先（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

   自動読み込みについて:
   - パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動ロードします。
   - テストなどで自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. データベース初期化（DuckDB）

   Python REPL やスクリプトでスキーマを初期化します。例:

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルパスまたは ":memory:"
   ```

   監査ログ専用 DB を別に作る場合:

   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 基本的な使い方

以下は主要機能の呼び出し例です。実行前に環境変数（.env）を正しく設定し、DuckDB スキーマを初期化してください。

- 日次 ETL の実行（株価・財務・カレンダー取得＋品質チェック）

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（既に init 済みなら get_connection だけでよい）
  conn = init_schema("data/kabusys.duckdb")

  # 当日分の ETL 実行（戻り値は ETLResult）
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から日足データを個別取得して保存

  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,31))
  saved = save_daily_quotes(conn, records)
  print("saved:", saved)
  ```

- RSS ニュース収集（raw_news 保存・銘柄紐付け）

  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コード
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- 監査スキーマの初期化（監査用テーブルを追加）

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.audit import init_audit_schema
  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- マーケットカレンダー関連ユーティリティ

  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2024, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

エラーハンドリングやロギングは各関数内で行われますが、実行スクリプト側でも例外キャッチ・ログ出力を適切に行ってください。

---

## よくあるトラブルと対処

- 環境変数不足による ValueError
  - config.Settings の各プロパティは必須変数が未設定の場合 ValueError を投げます。`.env` を作成して値を設定してください。

- DuckDB がない／インストールされていない
  - pip install duckdb を実行してください。

- J-Quants API の認証エラー（401）
  - リフレッシュトークンが無効、または env が正しく渡っていない可能性があります。settings.jquants_refresh_token を確認してください。
  - jquants_client は 401 を受けた際にトークンを自動リフレッシュして再試行します（1 回のみ）。

- RSS 取得でリダイレクトや内部アドレスに弾かれる
  - news_collector は SSRF 対策のためプライベート IP や非 http/https スキームを拒否します。外部公開の RSS を使用してください。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 以下の主要ファイルです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得＋保存）
    - news_collector.py          — RSS ニュース収集と保存
    - schema.py                  — DuckDB スキーマ定義＆初期化
    - pipeline.py                — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py     — マーケットカレンダー管理ユーティリティ
    - audit.py                   — 監査ログ（signal / order_requests / executions）
    - quality.py                 — データ品質チェック
  - strategy/
    - __init__.py                — 戦略層（拡張ポイント）
  - execution/
    - __init__.py                — 発注実行層（拡張ポイント）
  - monitoring/
    - __init__.py                — 監視・メトリクス（拡張ポイント）

上記のモジュールはそれぞれ拡張して実際の売買ロジック、ブローカー連携、モニタリング等を実装していく想定です。

---

## 開発・拡張方針（補足）

- 戦略（strategy）層と発注（execution）層はこのリポジトリの拡張ポイントです。Signal を生成し、signal_queue → order_requests → executions のフローで監査ログに記録することでトレーサビリティを担保できます。
- DB スキーマは冪等（CREATE IF NOT EXISTS / ON CONFLICT）であるため、運用中にスキーマを追加する際は後方互換を意識してください。
- ETL は差分取得＋バックフィル方式で API の後出し修正に耐性を持っています。品質チェックは Fail-Fast ではなく問題の収集を優先するため、検出結果に応じてアラートや手動介入を行う設計です。

---

必要であれば README の英語版、サンプル .env.example、requirements.txt、あるいは CLI スクリプト（管理用 entrypoint）のひな形も作成できます。どれを優先しますか？