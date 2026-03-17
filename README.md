# KabuSys

日本株向けの自動売買データ基盤・ETL・監査ライブラリです。  
J-Quants API や RSS フィードから市場データ・財務データ・ニュースを収集・保存し、品質チェック、特徴量・シグナル・監査ログの基盤を提供します。

主な設計方針：
- レート制限・リトライ・トークン自動リフレッシュを備えた J-Quants クライアント
- DuckDB を用いた冪等なデータ保存（ON CONFLICT）
- RSS の安全な取得（SSRF 対策、gzip 上限、XML 脆弱性対策）
- ETL の差分更新・バックフィル・品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル→発注要求→約定）のトレーサビリティ

---

## 機能一覧

- 環境変数/設定読み込みと管理（kabusys.config.Settings）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可能）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、四半期財務、取引カレンダー取得
  - レートリミット制御、リトライ、トークン自動リフレッシュ
  - DuckDB へ冪等保存関数（raw_prices / raw_financials / market_calendar）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、URL 正規化、記事ID生成（SHA-256先頭32文字）
  - SSRF・XML脆弱性対策、受信サイズ制限、DuckDB へ冪等保存
  - 記事から銘柄コード抽出と news_symbols への紐付け
- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層の DuckDB DDL 定義
  - init_schema(db_path) で初期化（冪等）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新・バックフィル・カレンダー先読み・品質チェックの統合実行
  - run_daily_etl で日次 ETL 実行（結果を ETLResult で返す）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合を検出
  - run_all_checks でまとめて実行
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの初期化関数
  - init_audit_schema(conn) / init_audit_db(path)

---

## 前提・依存関係

推奨 Python バージョン：3.10+（PEP 604 の型記法（|）を利用）  
主な依存ライブラリ（最低限）:
- duckdb
- defusedxml

インストール例（仮想環境を推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# パッケージを開発インストールできる場合:
pip install -e .
```

※ 実プロジェクトでは pyproject.toml / requirements.txt を使って依存を管理してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成 & 依存インストール（上記参照）

3. 環境変数の設定（.env を作成）
   - 自動読み込み: パッケージ起点で `.env` と `.env.local` がプロジェクトルートにあれば読み込まれます。
   - 自動読み込みを無効化する場合：
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     # オプション
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```
   - .env のパース挙動:
     - export KEY=val 形式に対応
     - シングル/ダブルクォート内のエスケープ処理対応
     - inline コメントの扱いは仕様に準拠

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトから:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ファイル DB
   # またはメモリDB:
   # conn = schema.init_schema(":memory:")
   ```
   監査ログ（audit）を別 DB にする場合:
   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主な API）

以下は簡単な利用例です。実運用はエントリポイントスクリプトやジョブ管理（cron, Airflow 等）を推奨します。

- J-Quants の ID トークン取得:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用して取得
  ```

- 日次 ETL を実行（市場カレンダー取得 → 株価・財務 → 品質チェック）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import pipeline, schema

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 単発で株価 ETL／財務 ETL を実行:
  ```python
  from datetime import date
  from kabusys.data import pipeline, schema

  conn = schema.get_connection("data/kabusys.duckdb")  # 既存DB接続
  fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
  ```

- RSS ニュース収集ジョブ:
  ```python
  from kabusys.data import news_collector, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # 既定のソースを使う場合
  results = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
  print(results)  # {source_name: saved_count, ...}
  ```

- データ品質チェック（個別 or 全部）:
  ```python
  from kabusys.data import quality, schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  ```

- 監査テーブルの初期化（既存接続へ追加）:
  ```python
  from kabusys.data import audit, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  audit.init_audit_schema(conn)
  ```

---

## 環境変数一覧（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
  - KABU_API_PASSWORD : kabuステーション API パスワード
  - SLACK_BOT_TOKEN : Slack 通知用 Bot Token
  - SLACK_CHANNEL_ID : Slack チャンネル ID

- 任意 / デフォルトあり
  - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH : SQLite（監視用）パス（デフォルト: data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env 自動ロードを無効化

環境変数は kabusys.config.Settings 経由で取得できます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            -- J-Quants クライアント（fetch/save）
      - news_collector.py            -- RSS ニュース取得・保存
      - schema.py                    -- DuckDB スキーマ定義 / init_schema
      - pipeline.py                  -- ETL パイプライン（差分更新・品質チェック）
      - audit.py                     -- 監査ログ（signal/order/execution）
      - quality.py                   -- データ品質チェック
      - pipeline.py
    - strategy/
      - __init__.py                  -- 戦略層用パッケージプレースホルダ
    - execution/
      - __init__.py                  -- 実行（ブローカ連携）プレースホルダ
    - monitoring/
      - __init__.py                  -- 監視用プレースホルダ

主要なモジュール名（呼び出し例）:
- kabusys.config.settings
- kabusys.data.schema.init_schema / get_connection
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.data.pipeline.run_daily_etl
- kabusys.data.quality.run_all_checks
- kabusys.data.audit.init_audit_schema

---

## 運用上の注意

- J-Quants の API レート制限（120 req/min）に合わせた内部制御がありますが、大量リクエストを行う際は設定確認を行ってください。
- DuckDB のファイルパスはデフォルトで data/ 配下に作成されます。運用時は永続ストレージを確保してください。
- ニュース取得は外部 URL へアクセスします。SSRF 防止や受信上限が組み込まれていますが、運用環境のネットワークリスク管理は別途行ってください。
- 環境変数は機密情報を含むため、適切に管理（Vault, secrets manager 等）することを推奨します。
- ETL 実行はジョブスケジューラやワーカーで管理し、ログ・監査を必ず残してください。

---

## 開発・拡張の指針

- strategy/ と execution/ パッケージはプレースホルダとして用意されています。戦略ロジックやブローカー接続をここに実装してください。
- DB スキーマ変更は schema.py の DDL を更新し、マイグレーションを設計してください（現状は init_schema で冪等にテーブル作成）。
- テストは外部 API 呼び出しを直接行わず、get_id_token や _urlopen 等をモックして実行することを想定しています。
- セキュリティ面: defusedxml の利用、SSRF対策、受信上限など既存対策を活かしつつ、外部ライブラリの脆弱性情報は随時確認してください。

---

必要であれば、この README をベースに以下も作成できます:
- .env.example のテンプレート
- Quickstart スクリプト（init + daily ETL 実行）
- Dockerfile / docker-compose 構成例
- CI / テスト実行手順

どれを追加しますか？