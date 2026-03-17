# KabuSys

日本株向け自動売買基盤のコアライブラリ（KabuSys）。データ収集（J-Quants、RSS）、ETL パイプライン、データ品質チェック、DuckDB スキーマと監査ログ機能を備え、戦略・発注・監視コンポーネントと連携して自動売買システムを構築するための基盤を提供します。

## 主な特徴
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - レートリミット遵守（120 req/min）とリトライ（指数バックオフ、最大 3 回）
  - 401 応答時の自動トークンリフレッシュ（一回のみ）
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を抑止
  - DuckDB への冪等保存（ON CONFLICT 句）
- RSS ニュース収集（NewsCollector）
  - RSS からの記事収集、前処理、記事IDの冪等化（正規化 URL の SHA-256 ハッシュ先頭 32 文字）
  - SSRF 防御、gzip サイズ制限、XML 攻撃対策（defusedxml）
  - raw_news / news_symbols への冪等保存（チャンクバルク挿入、INSERT RETURNING を利用）
  - テキストから銘柄コード抽出（既知コードとの照合）
- DuckDB ベースのデータモデル
  - Raw / Processed / Feature / Execution / Audit 層を含む包括的なスキーマ定義
  - スキーマ初期化用ユーティリティ（init_schema, init_audit_db）
  - 主要クエリ向けのインデックスを作成
- ETL パイプライン
  - 差分更新（最終取得日を確認して未取得分を取得）
  - backfill による後出し修正吸収
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）
- カレンダー管理（営業日判定、前後営業日の取得、夜間カレンダー更新ジョブ）
- 監査ログ（監査用テーブル群）  
  - シグナル → 発注要求 → 約定の UUID 連鎖によるフルトレーサビリティ

---

## 機能一覧（モジュール単位）
- kabusys.config
  - 環境変数の自動ロード（.env / .env.local）と Settings クラス
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_* 関数で DuckDB に冪等保存
- kabusys.data.news_collector
  - RSS 取得・前処理・保存（save_raw_news, save_news_symbols）
  - SSRF / XML / gzip / トラッキングパラメータ除去などの安全対策
- kabusys.data.schema
  - DuckDB スキーマ（DDL）定義・初期化（init_schema）
- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl（ETL 実行）
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.audit
  - 監査テーブル定義・初期化（init_audit_schema / init_audit_db）
- kabusys.data.quality
  - 各種データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）

（strategy、execution、monitoring はパッケージ構成に用意されています）

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.9+）
2. 必要パッケージをインストール
   - 主要依存パッケージ: duckdb, defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - 開発パッケージや追加依存がある場合はプロジェクトの pyproject.toml / requirements.txt を参照してください。

3. リポジトリをチェックアウトし editable install（オプション）
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

4. 環境変数を設定
   - 自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須環境変数（Settings にて必須とされているもの）:
     - JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD - kabuステーション API のパスワード
     - SLACK_BOT_TOKEN - Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID - 通知先チャネル ID
   - オプション / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例の `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本的な API 例）

以下は最小限の使用例（Python スクリプト内で実行）です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema

  conn = schema.init_schema("data/kabusys.duckdb")
  # またはメモリ DB
  # conn = schema.init_schema(":memory:")
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data import audit

  audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
  ```

- 日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import pipeline, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- RSS ニュース収集ジョブ（既知の銘柄コードセットを渡して紐付け）
  ```python
  from kabusys.data import news_collector, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例
  res = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(res)  # {source_name: 新規保存数}
  ```

- J-Quants の生データ取得（直接呼び出し例）
  ```python
  from kabusys.data import jquants_client as jq
  from datetime import date

  records = jq.fetch_daily_quotes(date_from=date(2024, 1, 1), date_to=date(2024, 1, 31))
  ```

注意点:
- jquants_client は内部でレートリミット、リトライ、トークンリフレッシュを行います。
- news_collector は SSRF/ZIP/XML 攻撃対策や受信サイズ制限を実施します。
- ETL は各ステップを個別にハンドリングするため、1 ステップ失敗でも他を継続します。run_daily_etl は ETLResult を返します。

---

## 環境変数まとめ（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) - デフォルト development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) - デフォルト INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

---

## ディレクトリ構成（主要ファイル）
プロジェクトのソースは `src/kabusys` にあります。主要ファイルは以下のとおりです。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数と Settings
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得 + 保存）
    - news_collector.py        — RSS ニュース収集、前処理、DB 保存
    - schema.py                — DuckDB スキーマ定義・初期化 (init_schema)
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — 市場カレンダー管理・営業日判定
    - audit.py                 — 監査ログテーブル初期化（init_audit_db）
    - quality.py               — データ品質チェック
  - strategy/
    - __init__.py
    (戦略関連モジュールを配置する場所)
  - execution/
    - __init__.py
    (発注・約定関連モジュールを配置する場所)
  - monitoring/
    - __init__.py
    (監視・メトリクス関連モジュールを配置する場所)

---

## 設計上の注意・セキュリティ考慮
- J-Quants API 利用はレート制限（120 req/min）を厳守します。内部で固定間隔スロットリングを採用しています。
- トークン管理: 401 を受けた場合に自動でリフレッシュを試みます（1 回のみ）。
- NewsCollector: SSRF、XML Bomb、Gzip Bomb、トラッキングパラメータを考慮した安全設計になっています。
- DuckDB の INSERT は冪等化（ON CONFLICT）を多用し、ETL の再実行に耐える設計です。
- 監査ログは基本的に削除しない前提です。時間は UTC で管理されます。

---

## よくある質問（FAQ）
- Q: .env は自動読み込みされますか？
  - A: はい。プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Q: DuckDB の初期化はどのようにする？
  - A: `kabusys.data.schema.init_schema(db_path)` を呼び出せば、必要なテーブル・インデックスを作成して接続を返します。
- Q: トークンや機密情報はどこに置くべき？
  - A: OS 環境変数かプロジェクトルートの `.env`（`.env.local` はローカル上書き用）に置いてください。`.env` をリポジトリに含めないよう注意してください。

---

この README はコードベースの主要機能と使い方をまとめた概略です。実運用の際は環境変数管理、シークレット管理、監査要件、運用用ログ/監視の設定を組織のポリシーに従って追加してください。必要であれば導入手順や運用手順の詳細ドキュメントを追記できます。