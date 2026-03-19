# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
DuckDB をデータ層に用い、J-Quants API からのデータ取得、ETL、特徴量計算、ニュース収集、監査ログなどを一通り扱える設計になっています。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API からの株価・財務・市場カレンダー取得（レート制御・リトライ・トークン自動更新）
- DuckDB ベースのデータスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース（RSS）収集・前処理・銘柄紐付け（SSRF 対策・トラッキング除去）
- ファクター（モメンタム／バリュー／ボラティリティ）計算と特徴量探索（IC・forward returns 等）
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ
- 小さなユーティリティ（Zスコア正規化、統計集計 等）

設計方針として、外部 API 呼び出しや発注処理はモジュール単位で分離し、DuckDB と標準ライブラリ中心で依存を最小にしています。

---

## 主な機能一覧

- data/jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - save_* 系：DuckDB への冪等保存（ON CONFLICT）・fetched_at 記録
  - レートリミット（120 req/min）、リトライ、401 時のトークン自動更新
- data/schema
  - DuckDB のスキーマ定義（raw_prices, prices_daily, features, orders, executions, audit tables など）
  - init_schema(db_path) で一括初期化
- data/pipeline
  - run_daily_etl(): 市場カレンダー → 株価 → 財務 → 品質チェック の一括処理
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別ジョブ
- data/news_collector
  - RSS フィードの取得（fetch_rss）、記事正規化、記事保存（save_raw_news）および銘柄紐付け（save_news_symbols / run_news_collection）
  - SSRF 対策、gzip サイズ防御、トラッキングパラメータ除去、記事ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）
- data/quality
  - 欠損・重複・スパイク・日付不整合などの品質チェックと QualityIssue の集計
- research
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- audit
  - 監査ログテーブルの初期化（init_audit_schema / init_audit_db）と時刻を UTC に固定するポリシー

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（開発インストール推奨）

   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

2. 必要な追加依存パッケージ（例）
   - duckdb
   - defusedxml

   例（pip）:

   ```
   pip install duckdb defusedxml
   ```

   ※プロジェクトの setup / pyproject によっては自動的にインストールされます。

3. 環境変数の設定
   - .env または環境変数で設定します。パッケージはプロジェクトルート（.git または pyproject.toml を基準）から自動で `.env` / `.env.local` を読み込みます（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須環境変数（主要）:
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード（発注を使う場合）
   - SLACK_BOT_TOKEN       : Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   オプション（デフォルトあり）:
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG/INFO/…（デフォルト: INFO）
   - DUCKDB_PATH           : data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH           : data/monitoring.db（デフォルト）

   例 `.env`:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（代表的なワークフロー）

以下は簡単な使用例（Python スニペット）。適宜ログ設定や例外処理を追加してください。

- DuckDB スキーマ初期化

  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 監査ログ用 DB 初期化（別 DB に分ける場合）

  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- 日次 ETL 実行

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を引数で指定可能
  print(result.to_dict())
  ```

- 個別 ETL（株価のみ）

  ```python
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- ニュース収集ジョブ実行（既知銘柄セットを渡して銘柄紐付けを行う）

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "6501"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 研究用ファクター計算（例: モメンタム）

  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2024, 1, 31)
  momentum = calc_momentum(conn, d)
  volatility = calc_volatility(conn, d)
  value = calc_value(conn, d)

  # Zスコア正規化の使用例
  normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- forward returns / IC 計算（特徴量探索）

  ```python
  from kabusys.research import calc_forward_returns, calc_ic

  fwd = calc_forward_returns(conn, target_date=d, horizons=[1,5,21])
  ic = calc_ic(factor_records=momentum, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

---

## 主要 API 詳細（ざっくり）

- init_schema(db_path) -> DuckDB 接続
  - 全テーブル・インデックスを作成する（冪等）
- get_connection(db_path) -> DuckDB 接続
  - 既存 DB へ接続（スキーマ初期化は行わない）
- run_daily_etl(conn, target_date=None, ...) -> ETLResult
  - ETL の実行結果を ETLResult オブジェクトで返す
- jquants_client.fetch_* / save_* : API 取得と DB 保存（冪等）
- news_collector.fetch_rss / save_raw_news / run_news_collection
- research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- data.stats.zscore_normalize

各関数の詳細はソースコードの docstring を参照してください。

---

## ディレクトリ構成

（リポジトリのルートが src/ を含む Python パッケージ構成を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS 収集・前処理・DB 保存
    - schema.py              — DuckDB スキーマ定義 & init_schema
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - audit.py               — 監査ログスキーマ初期化
    - features.py            — 特徴量関連の公開インターフェース
    - etl.py                 — ETLResult 再エクスポート
    - quality.py             — データ品質チェック
    - ...（他モジュール）
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — forward returns / IC / factor_summary / rank
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須 for kabu API) — kabuステーション API パスワード
- SLACK_BOT_TOKEN (必須 if Slack通知を使う)
- SLACK_CHANNEL_ID (必須 if Slack通知を使う)
- DUCKDB_PATH (任意) — デフォルト `data/kabusys.duckdb`
- SQLITE_PATH (任意) — デフォルト `data/monitoring.db`
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化

config.Settings クラスのプロパティは上記環境変数を参照します。未設定の必須値は ValueError を送出します。

---

## セキュリティ・設計上の注意点

- news_collector は SSRF 対策（リダイレクト検査・プライベート IP ブロック）や XML/ Gzip サイズ保護を実装していますが、運用環境でも外部フィードの取り扱いには注意してください。
- J-Quants の API レート制限やリトライ/バックオフは実装されていますが、実際の運用に合わせたスロットル調整が必要か確認してください。
- DuckDB の外部キーやトランザクションの挙動（バージョン依存）には注意。コメント中に示した制約（ON DELETE CASCADE 不可など）を踏まえて運用してください。

---

## 貢献・ライセンス

- 貢献歓迎です。Pull Request / Issue を作成してください。
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（ここでは明示していません）。

---

問題や不明点があれば、どの箇所（例: ETL 実行、DB 初期化、環境変数の設定、研究関数の使い方）について詳しく知りたいか教えてください。必要に応じてサンプルスクリプトやユニットテスト例も作成します。