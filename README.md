# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（データ取り込み・品質管理・特徴量算出・監査スキーマ等）

このリポジトリは、J-Quants API 等からのデータ収集（株価・財務・カレンダー・ニュース）、DuckDB を用いたデータ永続化、データ品質チェック、特徴量計算（ファクター探索 / 正規化）、および発注/監査に関するスキーマを提供するモジュール群で構成されています。

主な設計方針
- DuckDB を中心に「Raw / Processed / Feature / Execution」層でデータを整理
- J-Quants API のレート制御・リトライ・トークン自動リフレッシュ対応
- ETL は差分更新・バックフィル対応で冪等に保存（ON CONFLICT）
- 品質チェックは Fail-Fast ではなく問題を収集して呼び出し元が判断
- 本番発注（外部 API 呼び出し）を行うモジュールとは明確に分離

---

## 機能一覧

- 環境変数 / .env 自動読み込みと設定ラッパー（kabusys.config）
- DuckDB 用スキーマ初期化（data.schema.init_schema）
- J-Quants API クライアント（data.jquants_client）
  - 株価日足、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レートリミット管理、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ（save_*）
- ETL パイプライン（data.pipeline）
  - 差分取得、保存、品質チェック、日次一括実行（run_daily_etl）
- データ品質チェック（data.quality）
  - 欠損、重複、スパイク、日付不整合など
- ニュース収集（data.news_collector）
  - RSS 取得、前処理、重複排除、銘柄コード抽出、DuckDB への保存
  - SSRF/GzipBomb 等への防御を考慮
- 研究用ファクター計算（research.factor_research / feature_exploration）
  - Momentum / Volatility / Value 等の計算
  - 将来リターン計算、Spearman IC 計算、統計サマリー、ランク付け
- 統計ユーティリティ（data.stats）
  - z-score 正規化
- 監査ログスキーマ（data.audit）
  - signal -> order_request -> execution のトレース可能なテーブル群
- カレンダー管理（data.calendar_management）
  - 営業日判定、次/前営業日取得、夜間カレンダー更新ジョブ

---

## 要件

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - defusedxml
- そのほか標準ライブラリを多用（urllib, datetime, math 等）

依存関係はプロジェクトの packaging / pyproject.toml / requirements.txt に合わせてインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb defusedxml
   - その他ツールやテストフレームワークがあれば適宜インストール
4. DuckDB データベースを初期化
   - Python REPL またはスクリプトから実行（下記「データベース初期化」を参照）
5. 環境変数を設定
   - .env または .env.local をプロジェクトルートに配置（下記を参照）

---

## 環境変数 (.env) 例

以下は主要な環境変数の一覧（必須は明記）。実際は .env.example を参照して作成してください。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須：kabuステーション連携用)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須：通知用)
- SLACK_CHANNEL_ID (必須：通知用)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live) デフォルトは development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) デフォルト INFO

自動で .env を読み込む仕組みがあります（kabusys.config）。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。

---

## 使い方（代表的な操作例）

以下は Python スクリプトまたは REPL から行う基本的な操作例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  # またはメモリ DB
  # conn = schema.init_schema(":memory:")
  ```

- 監査ログ専用 DB 初期化
  ```python
  from kabusys.data import audit
  conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
  ```

- 日次 ETL を実行（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）
  ```python
  from kabusys.data import pipeline, schema
  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn)  # 戻り値は ETLResult インスタンス
  print(result.to_dict())
  ```

- J-Quants から株価を直接取得して保存
  ```python
  import duckdb
  from kabusys.data import jquants_client as jq
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 有効コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 研究用ファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2024, 2, 28)
  mom = calc_momentum(conn, d)
  vol = calc_volatility(conn, d)
  val = calc_value(conn, d)
  fwd = calc_forward_returns(conn, d)
  ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
  summary = factor_summary(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
  ```

- z-score 正規化（クロスセクション）
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m"])
  ```

---

## 注意事項 / 運用上のポイント

- J-Quants のレート制限（120 req/min）を Respect する実装になっています。大量のデータ取得は時間を要します。
- get_id_token はリフレッシュトークンから idToken を取得します。環境変数 JQUANTS_REFRESH_TOKEN を設定してください。
- ETL は差分更新を前提としています。初回は大きなデータ取得が発生します（_MIN_DATA_DATE により制約あり）。
- DuckDB の ON CONFLICT で冪等に保存されるため、再実行は通常安全です。
- news_collector は RSS の XML パースに defusedxml を使用し、SSRF / GzipBomb 等の対策を含みます。
- 本リポジトリのコードは本番発注（実際の証券会社への注文送信）自体を実行するモジュールには直接触れないよう分離設計されています。KABUSYS_ENV を "live" にすると本番向けの挙動である旨のフラグが立ちます。運用時は十分に検証・レビューしてください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      - 環境変数読み込み・Settings
    - execution/                      - 発注関連（未実装ファイル群の格納想定）
    - strategy/                       - 戦略関連（モデル等）
    - monitoring/                     - 監視系
    - data/
      - __init__.py
      - jquants_client.py             - J-Quants API クライアント + 保存
      - news_collector.py             - RSS 取得・前処理・DB 保存
      - schema.py                     - DuckDB スキーマ定義 & init_schema / get_connection
      - pipeline.py                   - ETL パイプライン（run_daily_etl 等）
      - etl.py                        - ETLResult の公開インターフェース
      - features.py                   - 特徴量ユーティリティ公開（zscore）
      - stats.py                      - 統計ユーティリティ（z-score）
      - quality.py                    - データ品質チェック
      - calendar_management.py        - マーケットカレンダー更新・営業日ロジック
      - audit.py                      - 監査ログスキーマの初期化
    - research/
      - __init__.py
      - feature_exploration.py        - 将来リターン・IC・summary・rank
      - factor_research.py            - Momentum/Volatility/Value 等の計算
    - その他モジュール...

---

## 開発 / テストのヒント

- 自動 .env ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト用に独自の環境を用意すると良いです。
- DuckDB を :memory: で初期化すると単体テストが簡単になります。
- news_collector._urlopen や jquants_client のネットワーク部分はモック可能に設計されている箇所があります（テストで置き換えて速度と再現性を確保）。
- 型注釈と明確なエラーハンドリングがコード内に組み込まれているため、静的解析（mypy）や linters（flake8）によるチェックが有効です。

---

もし README に追加してほしい内容（API リファレンス、より詳細な .env.example、デプロイ手順、CI ワークフロー など）があれば教えてください。