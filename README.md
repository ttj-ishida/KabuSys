# KabuSys

日本株自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、DuckDB スキーマ定義、監査ログ等を提供するモジュール群です。  
本リポジトリはライブラリ形式で各コンポーネントを組み合わせて自動売買システムを構築することを想定しています。

---

## プロジェクト概要

KabuSys は日本株自動売買システムの基盤的コンポーネントを提供します。主な役割は以下です。

- J-Quants API を通じた市場データ（株価日足、財務、マーケットカレンダー）の取得（レートリミット・リトライ・トークン自動更新対応）
- DuckDB ベースのデータスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集（正規化・SSRF対策・トラッキングパラメータ除去・銘柄紐付け）
- マーケットカレンダー管理（営業日判定、次/前営業日取得、夜間更新ジョブ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレース）

設計上、冪等性（ON CONFLICT）、トレーサビリティ、セキュリティ（SSRF/ XML 脅威対策）、およびテスト容易性を重視しています。

---

## 主な機能一覧

- config
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得ラッパー（settings）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

- data.jquants_client
  - ID トークン取得（自動リフレッシュ）
  - 株価日足 / 財務データ / マーケットカレンダー取得（ページネーション対応）
  - DuckDB への冪等保存（save_* 関数）
  - レートリミット制御・リトライ・Look-ahead 防止（fetched_at 記録）

- data.news_collector
  - RSS フィードの取得・前処理・記事保存（raw_news）
  - 記事IDは正規化 URL の SHA-256（先頭32文字）
  - SSRF / gzip bomb / XML 攻撃対策
  - 銘柄コード抽出・news_symbols への紐付け

- data.schema
  - DuckDB の全テーブル定義（Raw/Processed/Feature/Execution）
  - init_schema() でスキーマを冪等に作成

- data.pipeline
  - 差分 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 日次 ETL エントリ（run_daily_etl）：カレンダー→株価→財務→品質チェック
  - backfill ロジック、品質チェック統合

- data.calendar_management
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - calendar_update_job による夜間カレンダー更新

- data.quality
  - 欠損・スパイク・重複・日付不整合チェック（run_all_checks）

- data.audit
  - 監査向けテーブル（signal_events / order_requests / executions）と初期化関数

- strategy / execution / monitoring
  - パッケージは存在します（拡張ポイント）。各層の実装はプロジェクトに応じて実装してください。

---

## セットアップ手順

以下は最低限のセットアップ例です。プロジェクト側で追加の依存関係管理（requirements.txt / pyproject.toml）を行ってください。

1. Python 仮想環境を作成・有効化（例: Python 3.9+ 推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 必須（少なくとも）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   プロジェクトがパッケージ化されていれば:
   - pip install -e .

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（Settings で required なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack のチャネル ID
   - 任意 / デフォルト:
     - KABUS_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）

   例（.env の抜粋）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DB スキーマ初期化
   - Python REPL / スクリプトから:
     ```
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログを別 DB で使う場合:
     ```
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（主要な実行例）

- J-Quants の ID トークン取得（手動）
  ```
  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用して取得
  ```

- 日次 ETL を実行（run_daily_etl）
  ```
  from kabusys.data import schema, pipeline
  conn = schema.init_schema("data/kabusys.duckdb")  # 初期化 + 接続
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

  オプションで id_token を注入してテスト可能:
  ```
  result = pipeline.run_daily_etl(conn, id_token=my_token, backfill_days=5)
  ```

- ニュース収集ジョブ
  ```
  from kabusys.data import news_collector as nc, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes は抽出対象の有効な銘柄コードセット
  res = nc.run_news_collection(conn, known_codes={"7203", "6758"})
  print(res)  # {source_name: 保存件数}
  ```

- カレンダー夜間更新ジョブ
  ```
  from kabusys.data import calendar_management as cm, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = cm.calendar_update_job(conn)
  print(f"saved={saved}")
  ```

- 品質チェックの実行
  ```
  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

ログや例外は各モジュールで適切に出力・送出されるため、運用側でログレベルの設定や監視を行ってください。

---

## ディレクトリ構成

リポジトリ（src 配下）の主要ファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント、保存ユーティリティ
      - news_collector.py      # RSS ニュース収集
      - schema.py              # DuckDB スキーマ定義 & 初期化
      - pipeline.py            # ETL パイプライン（差分取得・品質チェック）
      - calendar_management.py # マーケットカレンダー管理
      - audit.py               # 監査ログテーブル初期化
      - quality.py             # データ品質チェック
    - strategy/
      - __init__.py            # 戦略層（拡張ポイント）
    - execution/
      - __init__.py            # 発注/約定層（拡張ポイント）
    - monitoring/
      - __init__.py            # 監視関連（拡張ポイント）

各モジュールは疎結合で設計されており、戦略（strategy）や発注実装（execution）、監視（monitoring）はプロジェクト固有の実装を追加することで統合できます。

---

## 運用上の注意点 / 実装上の留意点

- J-Quants API のレート制限（120 req/min）を内部で守る設計です。ただし、並列プロセスで複数インスタンスを動かす場合は注意してください。
- get_id_token はリフレッシュトークンから idToken を発行します。401 発生時は自動リフレッシュして一回だけリトライする仕組みがあります。
- ニュース収集では SSRF・XML Bomb・大容量レスポンス対策を組み込んでいますが、運用環境のネットワークポリシーも併せて検討してください。
- DuckDB はファイルロック等の挙動に注意が必要です。複数プロセスで同一 DB を同時書きする場合は設計を検討してください（監査 DB を分ける等の戦略）。
- 環境変数は .env/.env.local をプロジェクトルートに置くと自動ロードされます。テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動読み込みを抑止できます。
- 日次 ETL は「バックフィル」ロジックをサポートしており、最終取得日の数日前から再取得して API の後出し修正を吸収します。

---

## 拡張案 / 今後の実装ポイント

- strategy パッケージ内に具体的な売買ロジック（シグナル生成）を実装
- execution パッケージに証券会社 API（kabu-station 等）との送受信、オーダー状態管理の実装
- monitoring に Slack 通知・Prometheus Exporter 等を追加
- テストスイート（ユニット/統合）と CI パイプラインの整備
- 依存ライブラリを pyproject.toml / requirements.txt に明示

---

必要であれば、README にサンプル .env.example、起動スクリプト（systemd / cron / Airflow 例）、およびより詳細な API 使用例（関数ごとの引数説明や戻り値）を追記します。どの情報を優先して追記するか指示ください。