# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。データ収集・ETL、品質チェック、マーケットカレンダー管理、ニュース収集、監査ログ（発注→約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、J-Quants や kabuステーション 等の外部APIから取得したデータを DuckDB に保存し、戦略や発注システムが利用するための安定したデータ基盤とユーティリティを提供することを目的とした Python パッケージです。

主な設計方針：
- データ取得は冪等（ON CONFLICT ...）で行い、後出し修正に対応
- API レート制御、リトライ、トークン自動リフレッシュを内包
- データ品質チェックを組み込み、ETL の健全性を検査
- SSRF / XML Bomb / メモリ DoS 等を考慮した堅牢なニュース収集
- 監査ログでシグナルから約定までを UUID でトレース可能

---

## 機能一覧

- jquants_client
  - 株価日足（OHLCV）、財務データ（四半期）、マーケットカレンダーのフェッチ（ページネーション対応）
  - レートリミット（120 req/min）、指数バックオフ、特定ステータスでのリトライ、401 時のトークン自動リフレッシュ
  - DuckDB へ冪等保存（save_daily_quotes / save_financial_statements / save_market_calendar）

- ETL パイプライン（data.pipeline）
  - 差分更新（最終取得日からの自動算出 + バックフィル）
  - 日次一括 ETL 実行（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック

- データスキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution / Audit 層の DuckDB テーブル定義と初期化（init_schema）

- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定、前後の営業日取得、期間内営業日取得、夜間カレンダー更新ジョブ

- ニュース収集（data.news_collector）
  - RSS 取得、URL 正規化、記事ID生成（SHA-256）、前処理、DuckDB への冪等保存、銘柄コード抽出
  - SSRF 対策、gzip 制限、defusedxml 使用による安全な XML パース

- データ品質チェック（data.quality）
  - 欠損、重複、スパイク（前日比閾値）、日付不整合（未来日・非営業日）検出
  - 各チェックは QualityIssue の一覧を返す（Fail-Fast ではなく全件収集）

- 監査ログ（data.audit）
  - signal_events / order_requests / executions といった監査テーブルの初期化・管理
  - 監査用 DB の初期化 helper（init_audit_db）

- 環境設定（config）
  - .env / .env.local の自動ロード（プロジェクトルート検出）、必須環境変数チェック、設定ラッパー (`settings`)

---

## 前提・要件

- Python 3.9+
- 主要依存（抜粋）:
  - duckdb
  - defusedxml

（実際のパッケージ化では setup.cfg / pyproject.toml / requirements.txt を用意してください）

---

## 環境変数

自動的にプロジェクトルートの `.env` および `.env.local`（存在する場合）を読み込みます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（少なくとも下記が必要）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意 / デフォルトあり:

- KABUS_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用途の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (`development`, `paper_trading`, `live`)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）

注意: 設定は `kabusys.config.settings` オブジェクトから参照できます。

例（.env）:
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

---

## インストール（ローカル開発向け例）

1. 仮想環境作成 & 有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb defusedxml

3. パッケージを editable インストール（開発時）
   - pip install -e .

（プロジェクトには pyproject.toml / requirements.txt を用意してください）

---

## セットアップ手順（DB初期化等）

サンプル Python スクリプトや対話で実行できます。

1. DuckDB スキーマ初期化:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

2. 監査ログ用 DB 初期化（別DBに分離する場合）:
   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

3. （オプション）.env をプロジェクトルートに配置して環境変数を設定します（.env.example を参照）。

注意:
- init_schema は冪等的にテーブルを作成します（既存テーブルはスキップ）。
- DuckDB ファイルの親ディレクトリが存在しない場合、自動で作成されます。

---

## 使い方（主要ユースケース）

以下はパッケージ API を使った基本的な例です。

1. 日次 ETL（株価・財務・カレンダーの差分取得＋品質チェック）
   ```python
   from datetime import date
   import kabusys
   from kabusys.data import schema, pipeline

   conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema 済みを想定
   result = pipeline.run_daily_etl(conn)  # 今日を対象に ETL を実行
   print(result.to_dict())
   ```

   オプション:
   - target_date を指定して任意日を処理
   - id_token を直接渡して認証トークン注入（テスト時に便利）
   - run_quality_checks=False にして品質チェックをスキップ可能

2. ニュース収集ジョブ
   ```python
   from kabusys.data import news_collector, schema

   conn = schema.get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
   results = news_collector.run_news_collection(conn, known_codes=known_codes)
   print(results)  # {source_name: 新規保存件数}
   ```

3. マーケットカレンダー夜間更新
   ```python
   from kabusys.data import calendar_management, schema

   conn = schema.get_connection("data/kabusys.duckdb")
   saved = calendar_management.calendar_update_job(conn)
   print("saved", saved)
   ```

4. J-Quants API を直接呼ぶ（トークンを明示的に取得）
   ```python
   from kabusys.data import jquants_client as jq
   token = jq.get_id_token()  # settings からリフレッシュトークンを使用
   prices = jq.fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
   ```

5. 品質チェックのみ実行
   ```python
   from kabusys.data import quality, schema
   conn = schema.get_connection("data/kabusys.duckdb")
   issues = quality.run_all_checks(conn)
   for i in issues:
       print(i)
   ```

ログとエラー：
- 各モジュールは標準 logging を使用します。LOG_LEVEL / logging 設定で出力を制御してください。
- ETL は個別ステップで例外をハンドリングし、可能な限り処理を継続します。ETLResult.errors/quality_issues を参照して状況を判断してください。

---

## 開発・テスト時のヒント

- テスト時は .env の自動ロードを抑止できます:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- jquants_client はレート制限 (120 req/min) とリトライロジックを内包しています。大量実行の際は注意してください。

- news_collector._urlopen をモックすることで RSS フェッチの単体テストが容易です。

---

## ディレクトリ構成

パッケージの主要ファイル / ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント（取得 & 保存）
    - news_collector.py       # RSS ニュース収集・保存・銘柄抽出
    - schema.py               # DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py             # ETL パイプライン（差分更新 / run_daily_etl 等）
    - calendar_management.py  # マーケットカレンダー管理（営業日判定・更新ジョブ）
    - audit.py                # 監査ログ（signal/order/execution）初期化ヘルパ
    - quality.py              # データ品質チェック
  - strategy/
    - __init__.py             # 戦略関連モジュール置き場（拡張ポイント）
  - execution/
    - __init__.py             # 発注・実行関連（拡張ポイント）
  - monitoring/
    - __init__.py             # 監視・アラート関連（拡張ポイント）

その他:
- .env, .env.local, .env.example (プロジェクトルートに配置する想定)
- data/ (デフォルトの DuckDB / SQLite データ保存先)

---

## 追加情報 / 注意点

- すべての日時処理や保存は UTC を基準に扱うことを基本方針としています（監査ログ等で SET TimeZone='UTC' を実行）。
- DuckDB の SQL 実行ではプレースホルダ（?）を使用しており、SQL インジェクションのリスクを低減しています。
- ニュース収集はトラッキングパラメータ除去・URL 正規化・SHA-256 による記事ID生成で冪等性を確保しています。
- schema.init_schema は初期化のみを行います。既存コネクション取得は schema.get_connection を利用してください。
- 実際の運用（本番発注）を行う場合は、paper_trading / live 等の環境設定・十分なテスト・監査が必須です。

---

この README はコードベースの現状（主要モジュール/関数の設計）に基づいて作成しています。CLI やエントリポイント、パッケージ配布用設定（pyproject.toml 等）は別途プロジェクトに追加してください。質問や追加で欲しいチュートリアル（例: CI/CD、Docker 、例データでのサンプル実行）があれば教えてください。