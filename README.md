# KabuSys

バージョン: 0.1.0

日本株向けの自動売買プラットフォームの一部を提供する Python ライブラリ群です。データ収集（J-Quants）、DuckDB ベースのスキーマ・ETL、ニュース収集、ファクター計算（リサーチ）、監査ログ整備など、トレーディング・データ基盤と研究ワークフローに必要なコンポーネントを含みます。

---

## 主な特徴

- J-Quants API クライアント（取得・ページネーション・自動トークン更新・レート制御・リトライ）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- RSS ベースのニュース収集（SSRF/サイズ制限/トラッキング除去・銘柄抽出）
- ファクター計算（Momentum, Value, Volatility 等）および特徴量探索（将来リターン計算・IC）
- 統計ツール（Zスコア正規化など）
- 監査ログ（signal → order_request → executions のトレーサビリティ用スキーマ）
- 環境変数からの設定管理と .env 自動ロード機能

---

## 動作要件

- Python 3.10+
- 依存パッケージ（主なもの）
  - duckdb
  - defusedxml

必要に応じて他パッケージ（標準ライブラリで実装されている機能が多く、外部依存は最小化されています）。

---

## セットアップ手順

1. リポジトリを取得 / クローン

2. 仮想環境を作成して有効化（推奨）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール:
   ```bash
   pip install duckdb defusedxml
   ```

4. 環境変数を準備
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   .env ファイルをプロジェクトルートに置くと、自動で読み込まれます（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動ロードを無効化する場合は環境変数を設定します:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

5. DuckDB スキーマ初期化（Python スクリプト内で実行）
   - 通常のデータベースを初期化:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB を初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（簡単な例）

以下は代表的なユースケースのサンプルコードです。各関数はモジュール内の docstring に利用法が記載されています。

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から日足を取得して保存（単体）
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- RSS ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- ファクター計算（リサーチ）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  # 例: mom のカラム "mom_1m" と fwd の "fwd_1d" の IC を計算
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- Zスコア正規化（data.stats.zscore_normalize）
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
  ```

---

## 設定・挙動の注意点

- settings は環境変数を参照して値を取得します。必須項目が未設定の場合は ValueError を投げます。
- .env のパースはシェル風（export 句、クォート、行コメントなど）に対応しています。
- J-Quants API クライアントはレート制限（120 req/min）に合わせて固定間隔のスロットリングとリトライを実装しています。401 応答時はトークンを自動更新して再試行します。
- news_collector は RSS の SSRF 対策、gzip サイズ上限、XML ハードニング（defusedxml）など安全対策を実装しています。
- DuckDB の DDL は冪等（IF NOT EXISTS）になっているため、何度でも安全に init_schema を実行できます。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュールと役割の簡単な一覧です（src/kabusys 以下）:

- __init__.py
  - パッケージのバージョンと公開モジュール定義
- config.py
  - 環境変数管理、.env 自動ロード、Settings クラス
- data/
  - jquants_client.py: J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py: RSS 取得・前処理・DB 保存・銘柄抽出
  - schema.py: DuckDB スキーマ定義と init_schema / get_connection
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - features.py: データ特徴量関連の公開インターフェース
  - calendar_management.py: カレンダー更新・営業日判定ユーティリティ
  - audit.py: 監査ログ（signal / order_request / executions）用スキーマと初期化
  - etl.py: ETLResult の公開インターフェース
  - quality.py: データ品質チェック
- research/
  - feature_exploration.py: 将来リターン計算、IC、factor_summary、rank
  - factor_research.py: momentum / value / volatility ファクター計算
  - __init__.py: 便利関数の再エクスポート（zscore_normalize 等）
- strategy/
  - __init__.py （戦略ロジック用のエントリポイント）
- execution/
  - __init__.py （発注/ブローカ接続のエントリポイント）
- monitoring/
  - __init__.py （監視/メトリクス整備のエントリポイント）

---

## 開発・運用上の留意点

- DuckDB をファイルベースで運用する際はバックアップやロック、同時接続（マルチプロセス）の挙動に注意してください。
- 本コードベースでは「本番（live）」と「ペーパー（paper_trading）」を環境変数で切り替え可能です。発注系コードを組み込む場合は is_live/is_paper フラグを参照して安全に振る舞いを分離してください。
- API トークンなどは必ず安全に保管してください（.env ファイルのアクセス制御、CI/CD でのシークレット管理等）。
- ロギングレベルは環境変数 LOG_LEVEL で調整できます。

---

必要に応じて README を拡張して具体的な CLI、ユニットテスト、CI 設定、運用手順（夜間バッチ、監視アラート、Slack 通知）などを追記できます。追加したい内容があれば教えてください。