KabuSys
======

日本株向けの自動売買 / データ基盤ライブラリ（DuckDB ベース）。  
データ収集（J-Quants）、ETL、データ品質チェック、ファクター計算、ニュース収集、監査ログなどをモジュール化して提供します。

主な特徴
--------
- J-Quants API クライアント（ページネーション / レート制限 / トークン自動リフレッシュ / 冪等保存）
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分更新、バックフィル、品質チェック）
- ニュース収集（RSS → 正規化 → DuckDB 保存、SSRF 対策、トラッキングパラメータ除去）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と研究ユーティリティ（IC, forward returns, z-score）
- データ品質チェック群（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal → order_request → executions のトレースを担保）

必要条件
--------
- Python 3.10+
- 主要依存（例）
  - duckdb
  - defusedxml
- （ネットワーク経由の機能を使う場合）J-Quants API アクセス権（リフレッシュトークン）

セットアップ手順
----------------

1. (推奨) 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （開発用）pip install -e . など（プロジェクトの配布方法に合わせて）

3. 環境変数の設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（config モジュールによる自動ロード）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必要な環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能を使う場合）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知を使う場合）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - DUCKDB_PATH: DuckDB ファイルパス（省略時 data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）パス（省略時 data/monitoring.db）
   - KABUSYS_ENV: 環境 (development | paper_trading | live)（デフォルト development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

   例 .env（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

基本的な使い方（コード例）
------------------------

以下はライブラリの主要ユースケースの簡単な使用例です。実行は Python スクリプトまたは REPL から行ってください。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
  ```

- 日次 ETL 実行（J-Quants から差分取得し DB 保存・品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # init_schema で作成した conn を渡して実行
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集（RSS 取得 → DuckDB 保存 → 銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection

  known_codes = {"7203", "6758", "9432"}  # 既知の銘柄コードセット
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)  # {source_name: 新規保存数}
  ```

- ファクター計算 / 研究ユーティリティ
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary
  from kabusys.data.stats import zscore_normalize

  momentum = calc_momentum(conn, target_date=date(2024,1,31))
  fwd = calc_forward_returns(conn, target_date=date(2024,1,31))
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(momentum, ["mom_1m","ma200_dev"])
  normalized = zscore_normalize(momentum, ["mom_1m","mom_3m"])
  ```

- 監査ログ初期化（audit schema）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # または既存 conn に対して init_audit_schema(conn)
  ```

主要モジュール / 機能一覧
-----------------------
- kabusys.config
  - .env / 環境変数の自動読み込み、必須設定の検査、環境判定（dev/paper/live）
- kabusys.data.jquants_client
  - J-Quants API リクエスト / 保存（fetch_*, save_*）
  - レート制御、リトライ、トークンリフレッシュ
- kabusys.data.schema
  - DuckDB のスキーマ DDL と init_schema(), get_connection()
- kabusys.data.pipeline
  - run_daily_etl() を含む ETL ジョブ（prices / financials / calendar）
- kabusys.data.news_collector
  - RSS 取得・前処理・保存・銘柄抽出
- kabusys.data.quality
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
- kabusys.research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 研究支援（calc_forward_returns / calc_ic / factor_summary / rank）
- kabusys.data.audit
  - 監査ログテーブル定義・初期化（signal / order_requests / executions）

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - pipeline.py
  - features.py
  - stats.py
  - calendar_management.py
  - audit.py
  - etl.py
  - quality.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

運用上の注意 / ベストプラクティス
--------------------------------
- 環境変数（特に API トークン）は安全に管理してください（.env は gitignore に追加推奨）。
- DUCKDB ファイルはバックアップ・バージョン管理（スナップショット）を検討してください。
- ETL のバックフィル日数やスパイク閾値は運用要件に合わせて調整してください（pipeline.run_daily_etl の引数で上書き可）。
- 監査ログ（audit）を有効にするとシグナル〜約定の追跡が可能になります。証券会社からのコールバック等と連携する際に重要です。
- NewsCollector は外部 URL を取得するため、SSRF 対策済みですがプロキシやネットワーク制御を適切に行ってください。

貢献・拡張
----------
- ファクター追加、ETL の改善、外部データソースの追加（例: ニュース API、Twitter、EDGAR 等）を歓迎します。
- テストカバレッジを増やすこと（特にネットワーク依存部分、DB 周りのトランザクション）を推奨します。

ライセンス
---------
リポジトリの付属ライセンスに従ってください（本 README はコードベースの説明用テンプレートです）。

問い合わせ
----------
実装や運用に関する具体的な質問があれば、用途（ETL / 研究 / 運用）と再現手順を添えて質問してください。