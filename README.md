# KabuSys

日本株の自動売買プラットフォーム（ライブラリ群）  
このリポジトリはデータ取得（J-Quants）、ETL、データ品質チェック、特徴量計算、ニュース収集、監査ログなどを備えた日本株向け自動売買基盤のコア実装です。DuckDB をストレージに利用し、発注処理や戦略は拡張可能なモジュール構成になっています。

---

## 概要

KabuSys は以下を目的とした Python パッケージ群です。

- J-Quants API から市場データ（株価・財務・カレンダー）を安全かつ冪等に取得・保存する ETL パイプライン
- DuckDB を用いたデータスキーマ定義と初期化
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース（RSS）収集と記事→銘柄紐付け（SSRF 対策・サイズ制限などを実装）
- 研究用のファクター計算（モメンタム、ボラティリティ、バリュー）と探索ユーティリティ（IC, forward returns, summary）
- 発注／監査ログ用スキーマ（監査用テーブル群）
- 環境変数ベースの設定管理（.env 自動読み込み／オーバーライド対応）

設計上、本ライブラリは本番の発注 API を直接叩く箇所を含まない（データ取得・特徴量計算・スキーマ・監査の基盤提供）部分が中心です。発注ロジックやブローカー接続は execution パッケージ等を拡張して実装します。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API との通信（ページネーション対応、トークン自動リフレッシュ、レートリミット、リトライ）
  - fetch / save の冪等保存（DuckDB への ON CONFLICT 処理）
- data.pipeline
  - 日次 ETL 実行 run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の順で処理
  - 差分取得・バックフィル対応
- data.schema / data.audit
  - DuckDB スキーマの初期化（Raw / Processed / Feature / Execution / Audit テーブル群）
  - 監査テーブル（signal_events, order_requests, executions 等）の初期化
- data.news_collector
  - RSS フィード収集・前処理・記事の冪等保存・銘柄抽出（SSRF と GZIP 対策、トラッキングパラメータ除去）
- data.quality
  - 欠損データ、スパイク、重複、日付不整合のチェックとレポート（QualityIssue）
- data.stats / research
  - zscore_normalize（クロスセクション Z スコア正規化）
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary（リサーチ向け解析）
- config
  - .env 自動読み込み（プロジェクトルート検出）、必須環境変数取得ユーティリティ
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込み無効化可能

---

## セットアップ手順（ローカル）

1. Python 環境（推奨: 3.9+）を用意する

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトがパッケージ化されている場合）pip install -e .

   ※このコードベースは標準ライブラリを多用しています。上記以外に追加依存がある場合は requirements.txt を参照してください。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` または `.env.local` を置くと自動的に読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動読み込みを無効化）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - デフォルト例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - テスト時に自動ロードを無効にする:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベースの初期化
   - DuckDB スキーマを初期化:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB を初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（サンプル）

以下は代表的な利用例です。実運用ではログや例外処理、トークン管理、スケジューラ（cron / Airflow 等）を組み合わせて運用してください。

- 日次 ETL を実行する（簡易）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から株価をフェッチして保存
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  saved = save_daily_quotes(conn, recs)
  print(f"saved: {saved}")
  ```

- ニュース収集ジョブを実行（既知銘柄リストを与えて銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema(":memory:")
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2024, 3, 1))
  # records は [{"date": ..., "code": "...", "mom_1m": ..., ...}, ...]
  ```

- ファクターの正規化と IC 計算例
  ```python
  from kabusys.data.stats import zscore_normalize
  from kabusys.research import calc_forward_returns, calc_ic

  # factor_records: list[dict]（calc_momentum 等の出力）
  # forward_records: list[dict] = calc_forward_returns(conn, target_date)
  normalized = zscore_normalize(factor_records, ["mom_1m", "ma200_dev"])
  ic = calc_ic(normalized, forward_records, factor_col="mom_1m", return_col="fwd_1d")
  ```

---

## 主要ディレクトリ構成

（src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env の自動読み込みと Settings クラス（JQUANTS_REFRESH_TOKEN 等）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レート制御・リトライ・トークン管理・保存関数）
    - news_collector.py
      - RSS 取得・前処理・DB 保存・銘柄抽出（SSRF 対策・サイズ制限）
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py
      - 差分更新 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付整合性）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - features.py / etl.py / audit.py / calendar_management.py
      - 機能別ユーティリティ（再エクスポート、監査ログ初期化、カレンダー更新ロジック）
  - research/
    - __init__.py
    - feature_exploration.py
      - forward returns, IC, factor summary, ranking
    - factor_research.py
      - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - strategy/
    - __init__.py
    - （戦略用ロジックを実装する箇所。現状はパッケージプレースホルダ）
  - execution/
    - __init__.py
    - （発注・ブローカー接続を実装する箇所。プレースホルダ）
  - monitoring/
    - __init__.py
    - （監視 / メトリクス関連の実装用プレースホルダ）

---

## 設定項目（主要）

- 環境（KABUSYS_ENV）
  - development / paper_trading / live
- ログレベル（LOG_LEVEL）
  - DEBUG / INFO / WARNING / ERROR / CRITICAL
- J-Quants 関連
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABUSYS は token を使用して id_token を取得し API 呼び出しを行います
- kabuステーション関連
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- Slack
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DB パス
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視等に使用: default data/monitoring.db）

設定は .env または OS 環境変数で行います。自動読み込みはプロジェクトルートを基準に行われます（.git または pyproject.toml を探索）。

---

## 運用上の注意点 / ベストプラクティス

- J-Quants API のレート制限（120 req/min）を守るよう実装済みですが、大量データ収集時は注意してください。
- save_* 系関数は冪等（ON CONFLICT）を意識して実装されています。ETL は差分取得＋バックフィルのロジックに従って再実行可能です。
- ニュース収集は外部フィードを扱うため、サイズ制限・リダイレクト検査（SSRF 対策）が組み込まれています。外部入力をそのまま信頼しないでください。
- DuckDB のファイルはバックアップと権限管理を行ってください。監査ログは削除しない前提で設計されています。
- production 環境では KABUSYS_ENV=live を使用して安全対策（paper/live の分離）を行ってください。

---

## 貢献 / 拡張案

- execution パッケージにブローカーごとのアダプタを実装して実トレード対応（paper_trading/live 切替）
- strategy パッケージに戦略実装（Signal -> OrderRequest -> 発注）とリスク管理
- monitoring に Prometheus/Grafana 連携や、Slack 通知の実装
- テストカバレッジの強化（ETL の単体/統合テスト、ネットワーク部分のモック）

---

## ライセンス & 注意

この README はコードベースの要点をまとめたものです。実運用で使用する場合は十分なテストと法規制・証券会社の規約確認を行ってください。

--- 

必要であれば README に含める例 .env.example、CI 実行例、詳細な API 使用例や CLI エントリポイント（必要あれば）を追記できます。どの情報を優先的に追加しますか？