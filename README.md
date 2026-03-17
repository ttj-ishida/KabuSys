# KabuSys

日本株向け自動売買データ基盤 / ETL / 監査ライブラリ

このリポジトリは、J-Quants 等の外部 API から日本株データ（株価、財務、マーケットカレンダー、ニュース等）を取得し、
DuckDB に格納・品質チェック・監査ログ保存までを行うためのモジュール群です。
戦略層 / 実行層は拡張可能な設計になっており、バックテストや自動売買運用の基盤として利用できます。

バージョン: 0.1.0

---

## 主な機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）・再試行（指数バックオフ）・トークン自動リフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し look-ahead bias を回避
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS フィード取得、XML パース（defusedxml）、URL 正規化、トラッキングパラメータ除去
  - SSRF 対策（スキーム検証・ホストのプライベートアドレス判定・リダイレクト検査）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で冪等性を確保
  - DuckDB へのバルク挿入（トランザクション・チャンク分割、INSERT ... RETURNING）

- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution / Audit 層を含む包括的なスキーマ
  - テーブル作成・インデックス作成を行う init_schema 関数

- ETL パイプライン
  - 差分更新（最終取得日からの差分 or 指定範囲）・バックフィル（重複吸収）対応
  - 市場カレンダー先読み（lookahead）機能
  - 品質チェック（欠損・重複・スパイク・日付不整合）を実行・集約

- マーケットカレンダー管理
  - 営業日判定 / 翌営業日・前営業日検索 / 期間内営業日取得
  - カレンダー夜間更新ジョブ（calendar_update_job）

- 監査ログ（Audit）
  - signal → order_request → execution のトレーサビリティを保持する監査テーブル群
  - 発注の冪等キーや各種ステータスを保存

---

## セットアップ手順（開発・実行環境）

以下は基本的なセットアップ手順の例です（OS によりコマンドは適宜置き換えてください）。

1. Python 環境準備（推奨: 3.10+）
   - 仮想環境を作成して有効化する
     - python -m venv .venv
     - Unix/macOS: source .venv/bin/activate
     - Windows: .venv\Scripts\activate

2. 必要パッケージをインストール
   - requirements.txt がない場合、最低限以下が必要になります:
     - duckdb, defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトをパッケージとしてインストールする場合）
   - pip install -e .

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID       — Slack チャンネル ID
   - オプション（デフォルトあり）:
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH       — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH       — デフォルト: data/monitoring.db
     - KABUSYS_ENV       — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL         — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN="your_refresh_token_here"
     KABU_API_PASSWORD="your_kabu_password"
     SLACK_BOT_TOKEN="xoxb-..."
     SLACK_CHANNEL_ID="Cxxxxxxx"
     DUCKDB_PATH="data/kabusys.duckdb"
     KABUSYS_ENV="development"
     ```

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで実行:
     ```py
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログのみ別 DB に分けたい場合:
     ```py
     from kabusys.data.audit import init_audit_db
     conn_audit = init_audit_db("data/audit.duckdb")
     ```
   - 既存接続に監査テーブルを追加する場合:
     ```py
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)  # conn は init_schema の戻り値
     ```

---

## 使い方（主要 API / ワークフロー例）

- 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）
  ```py
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（初回のみ）
  conn = init_schema("data/kabusys.duckdb")

  # 日次 ETL 実行
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 個別データ取得（J-Quants）
  ```py
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

  token = get_id_token()  # settings.jquants_refresh_token を使用
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,3,31))
  ```

- ニュース収集ジョブの実行
  ```py
  from kabusys.data.pipeline import run_news_collection  # 実際の import は news_collector から
  from kabusys.data.news_collector import run_news_collection
  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- マーケットカレンダー関連ユーティリティ
  ```py
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  d = date(2024, 3, 15)
  is_trading = is_trading_day(conn, d)
  next_td = next_trading_day(conn, d)
  ```

- 品質チェック単体実行
  ```py
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意: 上記はライブラリ API を直接呼ぶ方法の例です。運用ではスケジューラ（cron / Airflow 等）から上記スクリプトを呼ぶ想定です。

---

## 自動環境読み込みの挙動

- config.py は、パッケージのルート（.git または pyproject.toml が見つかる親ディレクトリ）を探索し、
  プロジェクトルートにある `.env` と `.env.local` を自動的に読み込みます。
  読み込み順序: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数を設定:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成

リポジトリ内の主な構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント（取得・保存）
    - news_collector.py                 — RSS ニュース収集・保存
    - schema.py                         — DuckDB スキーマ定義・初期化
    - pipeline.py                       — ETL パイプライン（差分更新・日次ETL）
    - calendar_management.py            — 市場カレンダー管理（営業日判定等）
    - quality.py                        — データ品質チェック
    - audit.py                          — 監査ログ（signal / order_request / executions）
  - strategy/
    - __init__.py                        — 戦略層用の拡張ポイント（未実装の初期シグネチャ）
  - execution/
    - __init__.py                        — 発注実行層の拡張ポイント（未実装の初期シグネチャ）
  - monitoring/
    - __init__.py                        — 監視・メトリクス用（骨組み）

上記の各モジュールは用途別に分離されており、戦略や実行部分はプロジェクト固有のロジックに合わせて拡張して使用します。

---

## 注意点 / 設計上のポイント

- API レート制限やリトライロジック、トークンの自動リフレッシュなど、外部サービスとの堅牢な連携を重視しています。
- DuckDB に対する INSERT は冪等性（ON CONFLICT）を前提に設計しているため、ETL を再実行しても重複データ発生を抑えられます。
- ニュース収集では SSRF 対策・XML の安全なパース・レスポンスサイズ制限（Gzip Bomb 対策）等のセキュリティ考慮を行っています。
- 品質チェックは Fail-Fast ではなく問題を全収集して呼び出し側で判断できる設計です。
- 本リポジトリはデータ取得・保存・監査の基盤ライブラリを提供するもので、実際の「発注」部分（ブローカー API 呼び出し等）は別途実装・接続が必要です。

---

## 参考 / 次のステップ

- strategy / execution モジュールに戦略実装やブローカー接続を追加して運用ワークフローを組む
- scheduler（Airflow / cron / Prefect 等）経由で定期 ETL と calendar_update_job を運行する
- Slack や監視ツールと連携して異常時にアラートを上げる

---

ご不明点や README に追記してほしい項目があれば教えてください。