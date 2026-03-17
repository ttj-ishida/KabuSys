# KabuSys

日本株向けの自動売買基盤コンポーネント群です。  
データ取得（J-Quants）、ETLパイプライン、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）などの基盤処理を提供します。

---

## 主な特徴（機能一覧）
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPXマーケットカレンダーの取得
  - APIレート制限（120 req/min）遵守（内部 RateLimiter）
  - リトライ（指数バックオフ、指定ステータスの再試行）、401時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止
  - DuckDB へ冪等（ON CONFLICT DO UPDATE）で保存

- ニュース収集（RSS）
  - RSS 取得、前処理（URL除去・空白正規化）
  - URL正規化＋SHA-256ハッシュで記事ID生成（冪等性）
  - SSRF対策、受信サイズ上限、defusedxml によるXML保護
  - DuckDB へ冪等保存（INSERT ... RETURNING）および銘柄コード紐付け

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義、スキーマ初期化補助

- ETL パイプライン
  - 差分更新（最終取得日からの差分取得、自動バックフィル）
  - カレンダー先読み、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次ETLの統合実行（run_daily_etl）

- マーケットカレンダー管理
  - 営業日判定、前後営業日の探索、範囲内の営業日取得
  - 夜間バッチ更新 job（calendar_update_job）

- 監査ログ（audit）
  - シグナル→発注要求→約定のトレーサビリティ用スキーマ
  - 発注要求の冪等キー、UTCタイムスタンプ設定

- データ品質チェック
  - 欠損、スパイク、重複、日付整合性のチェックセット

---

## 動作要件
- Python 3.10+
  - （モジュール内の型ヒント（|）を使用しているため Python 3.10 以上を推奨）
- 必須パッケージの例
  - duckdb
  - defusedxml
  - （標準ライブラリ：urllib, json, logging 等）

※ プロジェクト配布時には requirements.txt / pyproject.toml を用意してください。

---

## セットアップ手順

1. リポジトリをクローン（ローカルで編集・インストールする場合）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必須パッケージをインストール
   ```
   pip install duckdb defusedxml
   # またはパッケージ化されている場合:
   pip install -e .
   ```

4. 環境変数 (.env) の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` または `.env.local` を置くと、自動で読み込まれます。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   必要な環境変数の一覧は次節を参照してください。

5. DuckDB スキーマ初期化（例: デフォルト path を使用）
   Python セッションで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # 親ディレクトリを自動作成
   conn.close()
   ```

---

## 必要な環境変数（主なもの）
- J-Quants / API / Slack などの認証情報や設定は環境変数から読み込みます。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API パスワード
- SLACK_BOT_TOKEN        : Slack Bot トークン
- SLACK_CHANNEL_ID       : 通知先 Slack チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL      : kabu API のベース URL （デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            : 実行環境 (development | paper_trading | live)、デフォルト development
- LOG_LEVEL              : ログレベル（DEBUG/INFO/...）、デフォルト INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env 読み込みを無効化（値がセットされていれば無効）

注意: Settings クラスは未設定の必須環境変数を参照すると ValueError を送出します。

---

## 使い方（短いコード例）

- DuckDB スキーマの初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（全体）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を省略すると今日
  print(result.to_dict())
  ```

- 個別 ETL（株価・財務・カレンダー）を手動で実行
  ```python
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date(2026,1,1))
  ```

- ニュース収集（RSS）と保存
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # sources を省略するとデフォルトの RSS ソースを使用
  results = run_news_collection(conn, known_codes={"7203","6758"})
  print(results)  # {source_name: saved_count}
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 監査スキーマ初期化（audit テーブル）
  ```python
  from kabusys.data.audit import init_audit_schema, init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- J-Quants の ID トークンを明示的に取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使って取得
  ```

注意点:
- jquants_client は内部でレート制御とリトライロジックを持ちます。大量リクエストを投げる際は設計に沿ってください。
- ETL 関数は id_token を引数で注入できます（テスト用に便利）。

---

## モジュール／主要 API 概観
- kabusys.config
  - settings: 環境変数ラッパー（プロジェクトルートの .env / .env.local を自動ロード）
- kabusys.data
  - jquants_client: API 取得・保存（fetch_* / save_*、get_id_token）
  - news_collector: RSS 取得・記事保存・銘柄紐付け（fetch_rss, save_raw_news, run_news_collection）
  - schema: DuckDB スキーマ定義・初期化（init_schema, get_connection）
  - pipeline: ETL（run_daily_etl, run_prices_etl...）
  - calendar_management: 営業日判定・更新ジョブ
  - quality: データ品質チェック（run_all_checks など）
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - プレースホルダ（戦略・発注・監視の拡張ポイント）

---

## ディレクトリ構成（このリポジトリに含まれる主なファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - execution/ __init__.py
  - strategy/ __init__.py
  - monitoring/ __init__.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - calendar_management.py
    - audit.py
    - quality.py

（上記は実装済みの主要モジュールを示しています。戦略や実行周りは拡張ポイントとして空パッケージになっています。）

---

## 運用上の注意・設計ポリシー（抜粋）
- API レート制限を守る設計（jquants_client の RateLimiter）。大量取得時は間隔に注意。
- 取得データの fetched_at（UTC）を記録し、データがいつ取得されたかを明確化（Look-ahead Bias の防止）。
- DuckDB への保存は冪等（ON CONFLICT）で実装。ETL を何度実行しても上書きで整合性を保ちます。
- ニュース取得は SSRF・XMLExploit・GzipBomb 対策を実装。
- 品質チェックは Fail-Fast ではなく全件収集し、呼び出し元で判断できるよう設計。

---

## 開発にあたって
- ローカルでの開発・テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを止め、テスト用の環境変数注入を行ってください。
- 型ヒント・ドキュメンテーションを参照し、ユニットテストを用意してから運用に移行してください。

---

必要であれば README に含める Usage の詳細（cron ジョブ例、Dockerfile 例、CI 設定のテンプレート、.env.example の雛形など）を追加で作成します。どのドキュメントが必要か教えてください。